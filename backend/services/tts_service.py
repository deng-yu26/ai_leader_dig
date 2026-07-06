"""
==============================================================
语音合成服务模块 (TTS)
基于 Edge-TTS，支持自定义音色、语速、语调参数
异步生成音频数据，支持分句合成
==============================================================
"""

import os
import sys
import asyncio
import tempfile
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TTS_VOICE, TTS_VOICE_LIST


class TTSService:
    """
    文本转语音服务
    基于Edge-TTS，本地离线运行，支持中文多种音色
    """

    def __init__(self):
        self.voice = TTS_VOICE
        self.rate = "+0%"      # 语速调整，如 "+20%", "-10%"
        self.volume = "+0%"    # 音量调整
        self.pitch = "+0Hz"    # 语调调整
        print(f"[TTS] 初始化TTS服务，默认音色：{self.voice}")

    async def _synthesize_async(self, text: str, voice: str, rate: str, pitch: str) -> Optional[bytes]:
        """
        异步调用Edge-TTS合成语音

        参数：
            text: 待合成的文本
            voice: 音色名称
            rate: 语速（如 "+20%", "-10%"）
            pitch: 语调（如 "+0Hz", "+50Hz"）

        返回：
            MP3音频二进制数据，失败返回None
        """
        try:
            import edge_tts
            import asyncio

            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            audio_data = bytearray()

            # 带超时的流式读取：国内连微软服务器可能很慢，5秒超时兜底
            async def collect():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])

            await asyncio.wait_for(collect(), timeout=5.0)
            return bytes(audio_data) if audio_data else None

        except asyncio.TimeoutError:
            print(f"[TTS] 语音合成超时（5s），跳过音频: {text[:20]}...")
            return None
        except ImportError:
            print("[TTS] 警告：edge-tts未安装")
            return None
        except Exception as e:
            print(f"[TTS] 语音合成失败：{e}")
            return None

    def synthesize(self, text: str, voice: Optional[str] = None,
                   speed: float = 1.0, pitch_value: float = 1.0) -> Optional[bytes]:
        """
        同步接口：合成语音

        参数：
            text: 待合成文本
            voice: 音色名称，None则使用默认
            speed: 语速倍率（0.5-2.0），1.0为正常
            pitch_value: 语调倍率（0.5-2.0），1.0为正常

        返回：
            MP3音频数据
        """
        if not text or not text.strip():
            return None

        # 设置参数
        tts_voice = voice or self.voice
        # 将语速倍率转换为edge-tts格式（百分比）
        rate_str = f"{int((speed - 1.0) * 100):+d}%"
        # 将语调倍率转换为Hz变化
        pitch_hz = int((pitch_value - 1.0) * 100)
        pitch_str = f"{pitch_hz:+d}Hz" if pitch_hz != 0 else "+0Hz"

        # 执行异步合成
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio = loop.run_until_complete(
                self._synthesize_async(text, tts_voice, rate_str, pitch_str)
            )
            return audio
        except Exception as e:
            print(f"[TTS] 合成失败：{e}")
            # 重试一次
            try:
                if loop:
                    audio = loop.run_until_complete(
                        self._synthesize_async(text, tts_voice, rate_str, pitch_str)
                    )
                    return audio
            except Exception as e2:
                print(f"[TTS] 重试失败：{e2}")
            return None
        finally:
            if loop:
                loop.close()

    def synthesize_to_file(self, text: str, output_path: str, voice: Optional[str] = None,
                           speed: float = 1.0, pitch_value: float = 1.0) -> bool:
        """
        合成语音并保存到文件

        参数：
            text: 待合成文本
            output_path: 输出文件路径
            voice: 音色
            speed: 语速
            pitch_value: 语调

        返回：
            是否成功
        """
        audio = self.synthesize(text, voice, speed, pitch_value)
        if audio:
            try:
                with open(output_path, "wb") as f:
                    f.write(audio)
                return True
            except Exception as e:
                print(f"[TTS] 保存文件失败：{e}")
        return False

    def get_available_voices(self) -> list:
        """获取可用音色列表"""
        return TTS_VOICE_LIST


# ======================== 全局单例 ========================
_tts_service = None


def get_tts_service() -> TTSService:
    """获取TTS服务单例"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service
