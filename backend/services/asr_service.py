"""
==============================================================
语音识别服务模块 (ASR)
基于 faster-whisper 本地离线运行，纯CPU执行
==============================================================
"""

import os
import sys
import tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WHISPER_MODEL_SIZE, WHISPER_DEVICE, WHISPER_COMPUTE_TYPE


class ASRService:
    """
    语音识别服务
    将音频文件/音频数据转换为文字
    基于 faster-whisper，纯CPU本地运行
    """

    def __init__(self):
        self.model = None
        self.model_loaded = False
        print(f"[ASR] 初始化ASR服务，模型大小：{WHISPER_MODEL_SIZE}，设备：{WHISPER_DEVICE}")

    def _load_model(self):
        """延迟加载Whisper模型"""
        if self.model_loaded:
            return

        try:
            from faster_whisper import WhisperModel

            # 使用int8量化，减少CPU负载
            self.model = WhisperModel(
                model_size_or_path=WHISPER_MODEL_SIZE,
                device=WHISPER_DEVICE,
                compute_type=WHISPER_COMPUTE_TYPE,
                download_root=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
            )
            self.model_loaded = True
            print(f"[ASR] Whisper模型加载完成（{WHISPER_MODEL_SIZE}）")
        except ImportError:
            print("[ASR] 警告：faster-whisper未安装，使用模拟模式")
            self.model_loaded = True
        except Exception as e:
            print(f"[ASR] 警告：模型加载失败：{e}，使用模拟模式")
            self.model_loaded = True

    def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """
        将音频数据转换为文字

        参数：
            audio_data: PCM音频二进制数据（16kHz, 16bit, mono）
            sample_rate: 采样率

        返回：
            识别出的文本
        """
        self._load_model()

        if self.model is None:
            # 模拟模式：返回占位文本
            return "用户语音输入内容"

        try:
            # 保存临时音频文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                self._write_wav(tmp_path, audio_data, sample_rate)

            # 执行语音识别
            segments, info = self.model.transcribe(
                tmp_path,
                beam_size=5,
                language="zh",
                vad_filter=True,  # 启用VAD过滤静音
                vad_parameters=dict(min_silence_duration_ms=500)
            )

            # 收集识别结果
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            # 清理临时文件
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            result = "".join(text_parts)
            print(f"[ASR] 识别结果：{result}")
            return result

        except Exception as e:
            print(f"[ASR] 语音识别失败：{e}")
            return ""

    def _write_wav(self, file_path: str, audio_data: bytes, sample_rate: int):
        """将PCM数据写入WAV文件"""
        import struct
        import wave

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)  # 单声道
            wf.setsampwidth(2)  # 16bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

    def transcribe_file(self, file_path: str) -> str:
        """
        直接转录音频文件

        参数：
            file_path: 音频文件路径

        返回：
            识别出的文本
        """
        self._load_model()

        if self.model is None:
            return "用户语音输入内容"

        try:
            segments, info = self.model.transcribe(
                file_path,
                beam_size=5,
                language="zh",
                vad_filter=True
            )

            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            return "".join(text_parts)

        except Exception as e:
            print(f"[ASR] 文件转录失败：{e}")
            return ""


# ======================== VAD静音检测 ========================
class VADDetector:
    """
    简单的VAD（语音活动检测器）
    基于能量阈值检测静音
    """

    def __init__(self, silence_threshold: float = 0.01, silence_duration: float = 3.0, sample_rate: int = 16000):
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.sample_rate = sample_rate
        self.silence_frames = int(sample_rate * silence_duration / 2)  # 每帧约30ms
        self.frame_size = int(sample_rate * 0.03)  # 30ms一帧

    def has_voice_activity(self, audio_chunk: bytes) -> bool:
        """
        检测音频块中是否包含语音活动

        参数：
            audio_chunk: PCM音频数据

        返回：
            True=检测到语音，False=静音
        """
        if len(audio_chunk) < 2:
            return False

        # 将bytes转换为int16数组
        import struct
        samples = struct.unpack(f"<{len(audio_chunk) // 2}h", audio_chunk[:len(audio_chunk) - len(audio_chunk) % 2])

        if not samples:
            return False

        # 计算RMS能量
        rms = np.sqrt(np.mean(np.array(samples, dtype=np.float32) ** 2))
        return rms > self.silence_threshold * 32768


# ======================== 全局单例 ========================
_asr_service = None


def get_asr_service() -> ASRService:
    """获取ASR服务单例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service
