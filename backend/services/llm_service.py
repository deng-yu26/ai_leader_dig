"""
==============================================================
多模态大模型接口封装模块（智谱AI GLM系列）
支持：
- 文本对话（流式/非流式）
- 图片理解（GLM-5V系列）
- 连接池管理（requests.Session）
- 自动重试（指数退避）
- 流式逐字文本推送

API文档参考：https://open.bigmodel.cn/dev/api/normal-model/glm-5
==============================================================
"""

import os
import sys
import json
import base64
import time
import random
import requests
from typing import Optional, List, Dict, Any, Generator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    LLM_API_KEY, LLM_API_BASE, LLM_MODEL_NAME,
    LLM_VISION_MODEL, LLM_MAX_TOKENS, LLM_TEMPERATURE
)


class LLMService:
    """
    智谱AI大模型服务
    封装智谱AI GLM系列模型的文本/图片问答功能
    支持流式输出、连接池复用、自动重试
    """

    def __init__(self):
        self.api_key = LLM_API_KEY
        self.api_base = LLM_API_BASE.rstrip("/")
        self.model_name = LLM_MODEL_NAME
        self.vision_model = LLM_VISION_MODEL
        self.max_tokens = LLM_MAX_TOKENS
        self.temperature = LLM_TEMPERATURE

        # 连接池：复用TCP连接，减少握手开销
        self._session = None
        self._init_session()
        print(f"[LLM] 智谱AI服务初始化完成，接口：{self.api_base}，模型：{self.model_name}")

    def _init_session(self):
        """初始化HTTP连接池"""
        self._session = requests.Session()
        # 连接池大小：最多保持10个连接
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0  # 我们自己控制重试
        )
        self._session.mount("https://", adapter)
        self._session.mount("http://", adapter)
        self._session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _should_retry(self, status_code: int) -> bool:
        """判断是否应该重试"""
        return status_code in (429, 500, 502, 503, 504)

    def _do_request(self, payload: dict, stream: bool = False, max_retries: int = 3) -> Optional[requests.Response]:
        """
        执行API请求（含指数退避重试）

        参数：
            payload: 请求体
            stream: 是否流式
            max_retries: 最大重试次数

        返回：
            Response对象或None
        """
        url = f"{self.api_base}/chat/completions"
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self._session.post(
                    url,
                    json=payload,
                    stream=stream,
                    timeout=(10, 120)  # (连接超时, 读取超时)
                )

                if response.status_code == 200:
                    return response

                if self._should_retry(response.status_code) and attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[LLM] 请求返回{response.status_code}，{wait:.1f}s后重试（第{attempt+1}次）")
                    time.sleep(wait)
                    continue

                print(f"[LLM] API请求失败：HTTP {response.status_code}，{response.text[:200]}")
                return None

            except requests.exceptions.Timeout as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[LLM] 请求超时，{wait:.1f}s后重试")
                    time.sleep(wait)
                else:
                    print(f"[LLM] 请求超时，已达最大重试次数")
            except requests.exceptions.ConnectionError as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    print(f"[LLM] 连接失败，{wait:.1f}s后重试")
                    time.sleep(wait)
                else:
                    print(f"[LLM] 连接失败，已达最大重试次数")
            except Exception as e:
                last_error = e
                print(f"[LLM] 请求异常：{e}")
                break

        print(f"[LLM] 请求最终失败：{last_error}")
        return None

    def update_config(self, api_key: str = None, api_base: str = None,
                      model_name: str = None, vision_model: str = None):
        """运行时更新配置"""
        changed = False
        if api_key:
            self.api_key = api_key
            changed = True
        if api_base:
            self.api_base = api_base.rstrip("/")
            changed = True
        if model_name:
            self.model_name = model_name
            changed = True
        if vision_model:
            self.vision_model = vision_model
            changed = True
        if changed:
            # 重建session（因为API key变了）
            self._init_session()
            print(f"[LLM] 配置已更新：API={self.api_base}，模型={self.model_name}")

    def get_config(self) -> dict:
        return {
            "api_key": self.api_key,
            "api_base": self.api_base,
            "model_name": self.model_name,
            "vision_model": self.vision_model
        }

    def is_configured(self) -> bool:
        """检查API密钥是否有效配置"""
        return bool(self.api_key) and "your-api-key" not in self.api_key

    def chat(self, messages: List[Dict[str, str]], stream: bool = False) -> str:
        """
        文本对话接口（非流式）

        参数：
            messages: 消息列表
            stream: 是否流式输出（仅当False时返回完整文本）

        返回：
            AI回复文本
        """
        if not self.is_configured():
            return self._mock_chat(messages)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False
        }

        response = self._do_request(payload, stream=False)
        if not response:
            return self._mock_chat(messages)

        try:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, json.JSONDecodeError) as e:
            print(f"[LLM] 解析响应失败：{e}")
            return self._mock_chat(messages)

    def chat_stream(self, messages: List[Dict[str, str]]) -> Generator[str, None, None]:
        """
        流式文本对话

        参数：
            messages: 消息列表

        生成器：
            yield 逐字/逐段文本片段
        """
        if not self.is_configured():
            yield self._mock_chat(messages)
            return

        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True
        }

        response = self._do_request(payload, stream=True)
        if not response:
            yield self._mock_chat(messages)
            return

        try:
            for line in response.iter_lines():
                if not line:
                    continue
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            print(f"[LLM] 流式读取失败：{e}")

    def chat_with_image(self, text: str, image_data: bytes,
                        image_name: str = "image.jpg", stream: bool = False) -> str:
        """
        图文对话接口（使用GLM-5V视觉模型）

        参数：
            text: 用户文本提问
            image_data: 图片二进制数据
            image_name: 图片文件名
            stream: 是否流式

        返回：
            AI回复文本
        """
        if not self.is_configured():
            return self._mock_chat([{"role": "user", "content": text + "(含图片)"}])

        try:
            image_base64 = base64.b64encode(image_data).decode("utf-8")
            ext = os.path.splitext(image_name)[1].lower()
            mime_types = {
                ".png": "image/png", ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg", ".gif": "image/gif",
                ".webp": "image/webp"
            }
            mime_type = mime_types.get(ext, "image/jpeg")

            payload = {
                "model": self.vision_model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": text},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "stream": stream
            }

            response = self._do_request(payload, stream=stream)
            if not response:
                return self._mock_chat([{"role": "user", "content": text + "(含图片)"}])

            if stream:
                parts = []
                for line in response.iter_lines():
                    if not line:
                        continue
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        ds = line[6:].strip()
                        if ds == "[DONE]":
                            break
                        try:
                            d = json.loads(ds)
                            c = d["choices"][0].get("delta", {}).get("content", "")
                            if c:
                                parts.append(c)
                        except (json.JSONDecodeError, KeyError):
                            continue
                return "".join(parts)
            else:
                data = response.json()
                return data["choices"][0]["message"]["content"]

        except Exception as e:
            print(f"[LLM] 图文调用失败：{e}")
            return self._mock_chat([{"role": "user", "content": text + "(含图片)"}])

    def _mock_chat(self, messages: List[Dict[str, str]]) -> str:
        """模拟回复（智谱AI不可用时的降级方案）"""
        user_msg = " ".join(
            msg.get("content", "") for msg in messages if msg["role"] == "user"
        )

        replies = {
            "门票": "灵山胜境景区成人门票价格为210元/人，拈花湾小镇门票为120元/人。景区开放时间：8:00-17:00。建议提前在官方小程序或携程等平台预约购票，可享优惠。",
            "大佛": "灵山大佛高达88米，是世界上最高的青铜释迦牟尼佛像之一。大佛位于灵山之巅，面向太湖，气势恢宏。登顶大佛可以俯瞰整个太湖风光，还可以体验'抱佛脚'祈福习俗。",
            "梵宫": "灵山梵宫是灵山胜境的核心建筑之一，建筑风格融合了佛教文化与现代艺术。内部有精美的壁画、雕塑、穹顶天象图等艺术作品，还有《吉祥颂》大型演出。",
            "九龙灌浴": "九龙灌浴是灵山胜境每日定时上演的经典水景表演，通过音乐、喷泉、水幕等现代科技手段，生动展现释迦牟尼诞生时'九龙吐水'的佛教传说故事。",
            "路线": "灵山胜境为您推荐三条特色游览路线：\n1. 文化朝圣路线（3小时精华游）：南门→佛足坛→九龙灌浴→祥符禅寺→灵山大佛→梵宫→五印坛城\n2. 自然风光路线（5小时全景游）：南门→佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔→灵山精舍→梵宫广场\n3. 亲子家庭路线（4小时轻松游）：南门→九龙灌浴→佛手广场→百子戏弥勒→梵宫→五印坛城",
            "交通": "灵山胜境位于无锡市滨湖区马山镇，可乘坐无锡地铁至梅园开原寺站，转乘公交88路或89路直达。自驾可通过沪宁高速、锡宜高速到达，景区设有大型停车场。",
            "住宿": "景区内推荐灵山精舍（禅意酒店，含素斋与早课体验），周边马山镇有多家酒店民宿可选，价格从几百元到上千元不等。",
            "素斋": "灵山梵宫提供素斋自助餐（50元/位），景区内还有素面套餐（35元/位），清淡雅致，适合体验佛门饮食文化。",
            "表演": "九龙灌浴每日4-5场表演，《吉祥颂》演出时间为10:35、11:30、14:00、16:00（以景区公告为准），时长约20分钟。",
            "拈花湾": "拈花湾禅意小镇以'禅意生活'为主题，有香月花街、妙音台、梵天花海等景点，适合休闲漫步、体验禅意文化。",
        }
        for keyword, reply in replies.items():
            if keyword in user_msg:
                return reply
        return "您好！我是灵山胜境AI数字人导游。我可以为您介绍灵山胜境的景点信息、门票价格、游览路线、交通方式、餐饮住宿等。请告诉我您想了解什么？"


# ======================== 全局单例 ========================
_llm_service = None


def get_llm_service() -> LLMService:
    """获取大模型服务单例"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service