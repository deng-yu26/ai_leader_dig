"""
==============================================================
LiveTalking 3D 数字人服务封装
负责：
1. 将 AI 回答文本发送到 LiveTalking 进行 3D Avatar 口播
2. 支持打断当前播放
3. LiveTalking 不可用时自动降级

LiveTalking API（aiohttp 路由）：
- POST /human         驱动数字人说话
  Body: {"type": "echo", "text": "...", "sessionid": "..."}
- POST /interrupt_talk  打断当前说话
  Body: {"sessionid": "..."}

注意：LiveTalking 默认端口 8010
==============================================================
"""

import sys
import os
import threading
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LIVETALKING_API_URL, LIVETALKING_ENABLED


class LiveTalkingService:
    """LiveTalking 3D 数字人调度服务"""

    def __init__(self):
        self.api_url = LIVETALKING_API_URL.rstrip("/")
        self.enabled = LIVETALKING_ENABLED
        self._session = None
        self._init_session()
        self._available = None
        print(f"[LiveTalking] 服务初始化，地址：{self.api_url}，启用：{self.enabled}")

    def _init_session(self):
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _check_available(self) -> bool:
        if not self.enabled:
            return False
        if self._available is not None:
            return self._available
        try:
            resp = self._session.get(f"{self.api_url}/", timeout=3)
            self._available = resp.status_code < 500
        except Exception:
            self._available = False
            print(f"[LiveTalking] 服务不可达：{self.api_url}")
        return self._available

    def is_available(self) -> bool:
        return self._check_available()

    def speak(self, text: str, sessionid: str = ""):
        """
        发送文本到 LiveTalking 进行 3D 口播（后台线程，不阻塞）

        参数：
            text: 朗读文本
            sessionid: WebRTC 会话 ID（从 /offer 协商获取）
        """
        if not text or not text.strip():
            return
        text = text.strip()
        t = threading.Thread(target=self._do_speak, args=(text, sessionid), daemon=True)
        t.start()

    def _do_speak(self, text: str, sessionid: str):
        if not self._check_available():
            print(f"[LiveTalking] 不可用，降级跳过：{text[:30]}...")
            return
        try:
            url = f"{self.api_url}/human"
            payload = {"type": "echo", "text": text, "sessionid": sessionid or ""}
            resp = self._session.post(url, json=payload, timeout=10)
            if resp.status_code == 200:
                print(f"[LiveTalking] 推送成功：{text[:30]}...")
            else:
                print(f"[LiveTalking] 推送失败 HTTP {resp.status_code}：{resp.text[:100]}")
        except requests.exceptions.Timeout:
            print(f"[LiveTalking] 请求超时")
        except requests.exceptions.ConnectionError:
            print(f"[LiveTalking] 连接失败，服务可能未启动")
            self._available = False
        except Exception as e:
            print(f"[LiveTalking] 发送异常：{e}")

    def interrupt(self, sessionid: str = ""):
        """打断 LiveTalking 当前说话"""
        if not self._check_available():
            return
        try:
            url = f"{self.api_url}/interrupt_talk"
            resp = self._session.post(url, json={"sessionid": sessionid or ""}, timeout=5)
            if resp.status_code == 200:
                print(f"[LiveTalking] 已打断")
        except Exception as e:
            print(f"[LiveTalking] 打断失败：{e}")

    def set_audiotype(self, audiotype: int, sessionid: str = ""):
        """切换数字人动作状态
        audiotype: 0=正常说话 1=静音空闲 2+=自定义动作
        """
        if not self._check_available():
            return
        try:
            url = f"{self.api_url}/set_audiotype"
            resp = self._session.post(
                url,
                json={"audiotype": audiotype, "sessionid": sessionid or ""},
                timeout=5
            )
            if resp.status_code == 200:
                print(f"[LiveTalking] 切换动作 audiotype={audiotype}")
        except Exception as e:
            print(f"[LiveTalking] 切换动作失败：{e}")

    def is_speaking(self, sessionid: str = "") -> bool:
        """查询 LiveTalking 是否正在说话"""
        if not self._check_available():
            return False
        try:
            url = f"{self.api_url}/is_speaking"
            resp = self._session.post(
                url,
                json={"sessionid": sessionid or ""},
                timeout=3
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    return result.get("data", False)
        except Exception as e:
            print(f"[LiveTalking] 查询说话状态失败：{e}")
        return False


# ======================== 全局单例 ========================
_livetalking_service = None


def get_livetalking_service() -> LiveTalkingService:
    global _livetalking_service
    if _livetalking_service is None:
        _livetalking_service = LiveTalkingService()
    return _livetalking_service
