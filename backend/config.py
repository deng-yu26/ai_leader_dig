"""
==============================================================
【灵山胜境AI数字人导游系统】全局配置文件
==============================================================
所有配置项集中管理，预留可修改位置，
用户可通过修改此文件或环境变量覆盖默认配置。
"""

import os

# ======================== 基础路径配置 ========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KOWLEDGE_DIR = os.path.join(os.path.dirname(BASE_DIR), "knowledge")  # 知识库文档存放目录

# ======================== 数据库配置 ========================
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "lingshan.db")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# ======================== 会话密钥 ========================
SECRET_KEY = "lingshan-ai-guide-secret-key-2026"

# ======================== Flask 运行配置 ========================
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5001
FLASK_DEBUG = True

# ======================== 【重要】多模态大模型配置（智谱AI） ========================
# 已配置为智谱AI GLM-5.2 系列模型
LLM_API_KEY = "d5ce3bc638e643649aba50c075afbdfe.9T7jKPhR6ITe11jY"  # 智谱AI API密钥
LLM_API_BASE = "https://open.bigmodel.cn/api/paas/v4"               # 智谱AI API接口地址
LLM_MODEL_NAME = "glm-5.2"                               # 默认文本模型
LLM_VISION_MODEL = "glm-5v"                                          # 视觉模型（支持图片理解）
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.85

# ======================== Whisper ASR 配置 ========================
WHISPER_MODEL_SIZE = "base"      # tiny/base/small/medium/large-v2
WHISPER_DEVICE = "cpu"           # 强制使用CPU
WHISPER_COMPUTE_TYPE = "int8"    # 量化类型，减少CPU负载

# ======================== Edge-TTS 配置 ========================
TTS_VOICE = "zh-CN-XiaoxiaoNeural"    # 默认中文女声音色
TTS_VOICE_LIST = [                     # 可用音色列表
    "zh-CN-XiaoxiaoNeural",   # 晓晓（女声，推荐）
    "zh-CN-YunxiNeural",      # 云希（男声）
    "zh-CN-YunyangNeural",    # 云扬（男声，情感丰富）
    "zh-CN-XiaoyiNeural",     # 晓伊（女声，活泼）
    "zh-CN-XiaohanNeural",    # 晓涵（女声，温柔）
]

# ======================== ChromaDB 向量库配置 ========================
CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")
CHROMA_COLLECTION_NAME = "lingshan_knowledge"
CHROMA_TOP_K = 5  # 检索返回的最相似文档数量

# ======================== WebSocket 配置 ========================
WS_PING_INTERVAL = 30      # ping间隔（秒）
WS_PING_TIMEOUT = 10       # ping超时时间（秒）

# ======================== 分句与流式配置 ========================
SENTENCE_SPLIT_PATTERN = r"[。！？\n！？]+"     # 分句正则
STREAM_CHUNK_SIZE = 50                        # 流式推送每段最小字符数

# ======================== 默认管理员账号 ========================
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# ======================== 文件上传配置 ========================
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB
