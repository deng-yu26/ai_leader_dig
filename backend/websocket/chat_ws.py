"""
==============================================================
WebSocket 长连接处理模块
负责：
1. 实时音频流接收与ASR转写
2. 流式文本推送（分句、边生成边推送）
3. 音频数据推送
4. 情绪标签推送
5. 实时打断机制

使用 flask-sock 原生同步 API（非 asyncio 包装），
确保与 Flask 开发服务器兼容。
==============================================================
"""

import os
import sys
import json
import re
import threading
import time
import base64
import tempfile
from typing import Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import request
from flask_sock import Sock

from config import SENTENCE_SPLIT_PATTERN
from models import db, ChatLog, DigitalHuman
from services.rag_service import get_knowledge_processor
from services.llm_service import get_llm_service
from services.tts_service import get_tts_service
from services.asr_service import get_asr_service
from services.emotion_service import get_emotion_service
from services.livetalking_service import get_livetalking_service

# ======================== WebSocket消息类型定义 ========================
# 客户端 -> 服务器
MSG_TYPE_TEXT = "text"          # 用户发送文本
MSG_TYPE_AUDIO = "audio"        # 用户发送音频数据
MSG_TYPE_IMAGE = "image"        # 用户发送图片
MSG_TYPE_INTERRUPT = "interrupt"  # 用户打断
MSG_TYPE_HEARTBEAT = "heartbeat"  # 心跳

# 服务器 -> 客户端
MSG_TYPE_USER_TEXT = "user_text"        # 用户语音识别结果文本（前端应展示为用户消息）
MSG_TYPE_TEXT_START = "text_start"      # AI开始生成文本
MSG_TYPE_TEXT_CHUNK = "text_chunk"      # AI文本片段
MSG_TYPE_TEXT_END = "text_end"          # AI文本结束
MSG_TYPE_AUDIO_START = "audio_start"    # AI音频开始
MSG_TYPE_AUDIO_CHUNK = "audio_chunk"    # AI音频数据
MSG_TYPE_AUDIO_END = "audio_end"        # AI音频结束
MSG_TYPE_EMOTION = "emotion"            # 情绪标签推送
MSG_TYPE_STATUS = "status"              # 状态消息
MSG_TYPE_ERROR = "error"                # 错误消息
MSG_TYPE_DONE = "done"                  # 整个对话完成


# 全局待处理列表：[(interrupt_flag, ws, full_answer, lt_sessionid, lt), ...]
# 用于在 lt_synced 模式下等待 LiveTalking 说完再发 done
_pending_lt_waits = []

def _send(ws, message: dict):
    """发送JSON消息到客户端（同步）"""
    try:
        ws.send(json.dumps(message, ensure_ascii=False))
    except Exception as e:
        print(f"[WebSocket] 发送消息失败：{e}")


def _receive(ws) -> Optional[dict]:
    """接收客户端JSON消息（同步）"""
    try:
        data = ws.receive()
        if data is None:
            return None
        if isinstance(data, str):
            return json.loads(data)
        return data
    except Exception:
        return None


def handle_chat(ws):
    """
    处理单次WebSocket连接的全双工通信（同步版本）
    由 flask-sock 的 @sock.route 直接调度
    """
    user_id = None
    digital_human_id = 1
    tts_voice = None
    tts_speed = 1.0
    tts_pitch = 1.0
    is_interrupted = False
    current_question = ""
    current_image_path = None
    current_image_data = None
    lt_sessionid = ""  # LiveTalking WebRTC session id

    # 获取服务实例
    rag = get_knowledge_processor()
    llm = get_llm_service()
    tts = get_tts_service()
    asr = get_asr_service()
    emotion = get_emotion_service()
    lt = get_livetalking_service()  # LiveTalking 3D 数字人服务

    def parse_init_message(msg: dict):
        """解析客户端初始化消息"""
        nonlocal user_id, digital_human_id, tts_voice, tts_speed, tts_pitch
        user_id = msg.get("user_id", 0)
        dh_id = msg.get("digital_human_id", 1)
        digital_human_id = dh_id
        try:
            dh = DigitalHuman.query.get(dh_id)
            if dh:
                tts_voice = dh.default_voice
                tts_speed = dh.default_speed
                tts_pitch = dh.default_pitch
        except Exception:
            pass

    def split_sentences(text: str) -> list:
        """将长文本按句子分割"""
        parts = re.split(SENTENCE_SPLIT_PATTERN, text)
        sentences = [p.strip() for p in parts if p.strip()]
        if len(sentences) <= 1:
            return [text]
        merged = []
        for s in sentences:
            if len(s) < 5 and merged:
                merged[-1] += s
            else:
                merged.append(s)
        return merged if merged else [text]

    def process_question():
        """处理用户问题：RAG检索 -> 流式LLM生成 -> 实时分句推送 -> TTS合成 -> 情绪推送"""
        nonlocal is_interrupted, current_question, current_image_path, current_image_data

        if not current_question.strip():
            _send(ws, {"type": MSG_TYPE_ERROR, "data": "问题不能为空"})
            return

        if is_interrupted:
            return

        question = current_question

        # 检测 LiveTalking 是否可用：可用则跳过本地 TTS，只用 WebRTC 音频（音画同步）
        lt_available = lt.is_available()

        # ---- 步骤1：RAG检索 ----
        _send(ws, {"type": MSG_TYPE_STATUS, "data": "正在检索知识库..."})
        context = rag.get_knowledge_context(question)

        # ---- 步骤2：构建Prompt ----
        system_prompt = """你是一个专业的灵山胜境景区AI导游。你的职责是回答关于灵山胜境景区（含拈花湾禅意小镇）的所有问题。

## 回答规则（严格遵守）：
1. 你只能回答与灵山胜境景区、拈花湾禅意小镇相关的内容。
2. 如果用户问的问题与景区无关，请友好地引导用户询问景区相关问题。
3. 回答内容要热情、生动、有感染力，适合导游讲解风格。
4. 基于提供的知识库上下文进行回答，不要编造事实。
5. 如果知识库中没有相关信息，请如实告知用户，并提供其他相关景点的介绍。
6. 推荐游览路线时，可以结合用户的兴趣点和时间安排给出个性化建议。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"知识库参考信息：\n{context}\n\n用户问题：{question}"}
        ]

        # ---- 步骤3：流式LLM生成 + 实时推送 ----
        _send(ws, {"type": MSG_TYPE_STATUS, "data": "AI导游正在思考..."})
        _send(ws, {"type": MSG_TYPE_TEXT_START, "data": ""})

        full_answer = ""
        text_buffer = ""       # 累积流式文本
        sentence_buffer = ""   # 逐句缓存（用于TTS）
        chunk_index = 0
        full_audio = bytearray()
        emotion_label = "平静"

        # 获取LLM流式生成器
        if current_image_data and current_image_path:
            # 图片模式退化为非流式
            full_answer = llm.chat_with_image(question, current_image_data, current_image_path)
            sentences = split_sentences(full_answer)
            for i, sentence in enumerate(sentences):
                if is_interrupted:
                    break
                _send(ws, {"type": MSG_TYPE_TEXT_CHUNK, "data": sentence, "index": i})
                if lt_available:
                    # LiveTalking 在线：跳过本地 TTS，由 WebRTC 流提供音画同步的音频
                    _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": "", "index": i, "text": sentence, "lt_synced": True})
                else:
                    audio = tts.synthesize(sentence, voice=tts_voice, speed=tts_speed, pitch_value=tts_pitch)
                    if audio:
                        full_audio.extend(audio)
                        audio_b64 = base64.b64encode(audio).decode("utf-8")
                        _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": audio_b64, "index": i, "text": sentence})
                # 同步推送到 LiveTalking 3D 数字人口播
                lt.speak(sentence, lt_sessionid)
                chunk_index += 1
        else:
            # 流式模式：逐字/逐段从LLM接收并实时推送到前端
            stream_gen = llm.chat_stream(messages)
            for chunk in stream_gen:
                if is_interrupted:
                    break

                full_answer += chunk
                text_buffer += chunk
                sentence_buffer += chunk

                # 检查句子边界（遇到句号、感叹号、问号、换行等）
                boundary_chars = set("。！？.!?\n")
                if any(c in chunk for c in boundary_chars) and len(sentence_buffer) >= 5:
                    # 提取并推送完整句子
                    sentences_in_buffer = re.split(SENTENCE_SPLIT_PATTERN, sentence_buffer)
                    for s in sentences_in_buffer:
                        s = s.strip()
                        if s and len(s) >= 2:
                            _send(ws, {"type": MSG_TYPE_TEXT_CHUNK, "data": s, "index": chunk_index})
                            if lt_available:
                                # LiveTalking 在线：跳过本地 TTS
                                _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": "", "index": chunk_index, "text": s, "lt_synced": True})
                            else:
                                audio = tts.synthesize(s, voice=tts_voice, speed=tts_speed, pitch_value=tts_pitch)
                                if audio:
                                    full_audio.extend(audio)
                                    audio_b64 = base64.b64encode(audio).decode("utf-8")
                                    _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": audio_b64, "index": chunk_index, "text": s})
                            # 同步推送到 LiveTalking 3D 数字人口播
                            lt.speak(s, lt_sessionid)
                            chunk_index += 1
                    sentence_buffer = ""

                # 实时分析情绪（每收到一段内容都更新）
                emotion_label = emotion.get_emotion_label(full_answer)
                _send(ws, {"type": MSG_TYPE_EMOTION, "data": emotion_label})

            # 推送剩余的句子缓存
            if sentence_buffer.strip() and not is_interrupted:
                remaining = sentence_buffer.strip()
                _send(ws, {"type": MSG_TYPE_TEXT_CHUNK, "data": remaining, "index": chunk_index})
                if lt_available:
                    _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": "", "index": chunk_index, "text": remaining, "lt_synced": True})
                else:
                    audio = tts.synthesize(remaining, voice=tts_voice, speed=tts_speed, pitch_value=tts_pitch)
                    if audio:
                        full_audio.extend(audio)
                        audio_b64 = base64.b64encode(audio).decode("utf-8")
                        _send(ws, {"type": MSG_TYPE_AUDIO_CHUNK, "data": audio_b64, "index": chunk_index, "text": remaining})
                # 同步推送到 LiveTalking 3D 数字人口播
                lt.speak(remaining, lt_sessionid)

        if is_interrupted:
            return

        if not full_answer.strip():
            full_answer = "抱歉，我暂时无法回答这个问题。请咨询灵山胜境景区其他相关事宜。"

        # ---- 最终情绪推送 ----
        emotion_label = emotion.get_emotion_label(full_answer)
        _send(ws, {"type": MSG_TYPE_EMOTION, "data": emotion_label})

        # 文本生成已完成，先发 text_end（关闭前端"思考中"状态）
        _send(ws, {"type": MSG_TYPE_TEXT_END, "data": full_answer})

        if lt_available:
            # LiveTalking 模式：数字人还在朗读，后台等待说完再发 done
            # 这样前端打断按钮会保持可见（isSpeaking=true）
            interrupt_flag = {'interrupted': False}
            _pending_lt_waits.append((interrupt_flag, ws, full_answer, lt_sessionid, lt))

            def _wait_lt_finish():
                waited = 0.0
                while waited < 30.0:  # 最长等 30 秒
                    if interrupt_flag['interrupted']:
                        return
                    time.sleep(0.3)
                    waited += 0.3
                    try:
                        if not lt.is_speaking(lt_sessionid):
                            print(f"[LiveTalking] 说话结束，等待了 {waited:.1f}s")
                            break
                    except Exception:
                        pass
                if not interrupt_flag['interrupted']:
                    try:
                        _send(ws, {"type": MSG_TYPE_AUDIO_END, "data": ""})
                        _send(ws, {"type": MSG_TYPE_DONE, "data": ""})
                    except Exception:
                        pass
                # 清理
                try:
                    _pending_lt_waits.remove(
                        (interrupt_flag, ws, full_answer, lt_sessionid, lt)
                    )
                except ValueError:
                    pass

            t = threading.Thread(target=_wait_lt_finish, daemon=True)
            t.start()
        else:
            # 本地 TTS 模式：立即发送完成信号（原有行为）
            _send(ws, {"type": MSG_TYPE_AUDIO_END, "data": ""})
            _send(ws, {"type": MSG_TYPE_DONE, "data": ""})

        # ---- 步骤7：保存对话日志 ----
        try:
            voice_duration = len(full_audio) / 16000 if full_audio else 0
            log = ChatLog(
                user_id=user_id or 0,
                question_text=question,
                answer_text=full_answer,
                emotion_label=emotion_label,
                voice_duration=voice_duration,
                digital_human_id=digital_human_id,
                tts_voice=tts_voice or "zh-CN-XiaoxiaoNeural",
            )
            db.session.add(log)
            db.session.commit()
        except Exception as e:
            print(f"[WebSocket] 保存对话日志失败：{e}")

    # ==================== 主循环 ====================
    try:
        # 接收客户端初始化消息
        init_msg = _receive(ws)
        if init_msg:
            parse_init_message(init_msg)

        while True:
            message = _receive(ws)
            if message is None:
                break

            msg_type = message.get("type")

            # 更新 LiveTalking sessionid（每条消息都可能携带）
            sid = message.get("lt_sessionid", "")
            if sid:
                lt_sessionid = sid

            # 处理心跳
            if msg_type == MSG_TYPE_HEARTBEAT:
                _send(ws, {"type": MSG_TYPE_HEARTBEAT, "data": "pong"})
                continue

            # 处理打断信号
            if msg_type == MSG_TYPE_INTERRUPT:
                is_interrupted = True
                lt.interrupt(lt_sessionid)  # 同步打断 LiveTalking 3D 数字人
                # 清理所有等待中的 LiveTalking 完成检查
                for flag, wait_ws, _, _, _ in list(_pending_lt_waits):
                    flag['interrupted'] = True
                    try:
                        _send(wait_ws, {"type": MSG_TYPE_DONE, "data": ""})
                    except Exception:
                        pass
                _pending_lt_waits.clear()
                _send(ws, {"type": MSG_TYPE_STATUS, "data": "已打断当前回复"})
                continue

            # 处理文本消息
            if msg_type == MSG_TYPE_TEXT:
                is_interrupted = False
                current_question = message.get("data", "")
                current_image_path = None
                current_image_data = None
                process_question()

            # 处理音频消息
            elif msg_type == MSG_TYPE_AUDIO:
                is_interrupted = False
                audio_b64 = message.get("data")
                if audio_b64:
                    _send(ws, {"type": MSG_TYPE_STATUS, "data": "正在识别语音..."})
                    # 客户端发送的是 base64 编码的 WebM 音频数据
                    raw_bytes = base64.b64decode(audio_b64)
                    tmp_path = None
                    try:
                        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                            f.write(raw_bytes)
                            tmp_path = f.name
                        # 使用 transcribe_file 让 faster-whisper 内部调 ffmpeg 解码
                        text = asr.transcribe_file(tmp_path)
                    except Exception as e2:
                        print(f"[WebSocket] 音频解码失败: {e2}")
                        text = ""
                    finally:
                        if tmp_path:
                            try:
                                os.unlink(tmp_path)
                            except Exception:
                                pass
                    current_question = text
                    current_image_path = None
                    current_image_data = None
                    # 将语音识别结果推送给前端，前端会将其展示为用户消息
                    if text:
                        _send(ws, {"type": MSG_TYPE_USER_TEXT, "data": text})
                    process_question()

            # 处理图片消息
            elif msg_type == MSG_TYPE_IMAGE:
                is_interrupted = False
                image_b64 = message.get("data")
                current_question = message.get("text", "")
                if image_b64:
                    current_image_data = base64.b64decode(image_b64)
                else:
                    current_image_data = None
                current_image_path = message.get("filename", "image.jpg")
                process_question()

    except Exception as e:
        print(f"[WebSocket] 连接处理异常：{e}")
        try:
            _send(ws, {"type": MSG_TYPE_ERROR, "data": f"服务器内部错误：{str(e)}"})
        except Exception:
            pass


# ======================== WebSocket路由注册 ========================
def register_websocket(app, sock: Sock):
    """
    注册WebSocket路由

    参数：
        app: Flask应用
        sock: Sock实例
    """

    @sock.route("/ws/chat")
    def chat_ws(ws):
        """WebSocket聊天接口（同步版本）"""
        handle_chat(ws)