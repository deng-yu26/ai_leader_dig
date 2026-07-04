# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

**灵山胜境 AI 数字人导游系统** — 参加第十五届中国软件杯大赛 A5 赛题。为景区提供 AI 驱动的 3D 数字人导游，支持语音/文字/图片问答、路线推荐、知识库管理和数据大屏。

### 核心架构：双项目 API 协作

```
ai_leader_dig（导游大脑）           LiveTalking（3D 脸）
┌──────────────────────┐   HTTP    ┌──────────────────┐
│ RAG → 智谱GLM → 回答  │ ────────→ │ TTS → 3D Avatar  │
│ 知识库 · 路线 · 后台   │          │ WebRTC 视频流     │
│ H5移动端 + Admin后台   │ ← 嵌入 ← │ GPU 实时渲染      │
└──────────────────────┘          └──────────────────┘
```

- **ai_leader_dig**（本仓库）：导游业务逻辑 + 双端前端。负责 ASR、RAG 检索、智谱 GLM 对话、知识库管理、数据看板。
- **LiveTalking**（`D:\codeProject\livetalking\LiveTalking`）：3D 数字人渲染引擎。负责 TTS 语音合成、3D Avatar 口播渲染、WebRTC 视频推流。

两个项目**独立运行、独立仓库、不互相侵入**，仅通过 `POST /api/human` HTTP 接口通信。

### 当前状态

| 模块 | 状态 | 说明 |
|------|:--:|------|
| 后端 API | ✅ | Flask 3.1，Flask-Sock WebSocket，SQLite |
| LLM | ✅ | 智谱AI GLM-5.2（流式 + 图片识别） |
| ASR | ✅ | faster-whisper base 模型 |
| TTS | ✅ | Edge-TTS（5 种中文声音），后端本地合成 |
| RAG | ✅ | ChromaDB + 自定义 SimpleEmbedding（384 维） |
| 情绪检测 | ✅ | 关键词规则匹配 |
| H5 前端 | ✅ | Vue3 + Vant4，聊天/路线/历史/用户 |
| Admin 后台 | ✅ | Vue3 + Element Plus + ECharts，数据大屏/知识库/AI配置 |
| Live2D | ⚠️ STUB | Live2DViewer.vue 为占位组件，无实际渲染 |
| LiveTalking 集成 | ❌ 未实现 | digital.md 有规划，无代码 |

## 赛题关键要求

| 要求 | 说明 | 对应 |
|------|------|------|
| 多模态交互 | 语音 + 文本 + 表情 | 语音/文字已有，表情待 LiveTalking 对接 |
| 口型同步 | 语音与口型匹配 | LiveTalking 3D 引擎保障 |
| 知识库准确率 | 基于官方资料包，≥ 90% | RAG 调优 |
| 交互延迟 | < 5 秒 | WebSocket 流式推送 |
| 多模态大模型 | ≥ 1 个 | 智谱 GLM-5V 图片识别 |
| 管理后台 | 形象配置 + 感受度报告 + 数据大屏 | Admin 已有基础 |

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend framework | Flask 3.1 |
| ORM | Flask-SQLAlchemy (SQLite) |
| Real-time | Flask-Sock (同步 WebSocket) |
| Auth | Flask session（服务端 cookie） |
| LLM | 智谱AI GLM-5.2 (文本) + GLM-5V (视觉) |
| Embedding | 自定义 SimpleEmbedding（384 维哈希特征，无需 ML 模型） |
| Vector DB | ChromaDB 1.5.9 (持久化) |
| TTS | Edge-TTS（后端本地合成） |
| STT | faster-whisper 1.2 (`base` 模型, CPU int8) |
| 3D Digital Human | LiveTalking（MuseTalk 模型，WebRTC 推流）— 待集成 |
| H5 Frontend | Vue 3 + Vite + Pinia + Vant 4（纯 JS） |
| Admin Frontend | Vue 3 + Vite + Pinia + Element Plus + ECharts（纯 JS） |

## Directory structure

```
ai_leader_dig/
├── startup.py              # 一键启动脚本
├── README.md               # 项目说明
├── CLAUDE.md               # 本文件
├── digital.md              # LiveTalking 3D 数字人集成规划
├── zhipu.md                # 智谱AI API 参考文档
├── GIT_WORKFLOW.md         # Git 工作流规范
│
├── knowledge/              # 景区知识源文件（docx/xlsx）
│   ├── 灵山胜境 景点结构化数据集.docx
│   ├── 灵山胜境：历史、文化、景点特色与个性化游览指南.docx
│   └── 景点景区旅游数据行为分析数据.xlsx
│
├── backend/                # Flask 后端 (port 5001)
│   ├── app.py              # 入口：create_app() 工厂
│   ├── config.py           # 全局配置（API key、模型、路径）
│   ├── models.py           # 8 个数据模型
│   ├── init_db.py          # 初始化数据库 + 种子数据
│   ├── requirements.txt    # Python 依赖
│   ├── routes/
│   │   ├── admin_routes.py # 管理端 REST API (/api/admin/*)
│   │   └── user_routes.py  # 用户端 REST API (/api/user/*)
│   ├── services/
│   │   ├── rag_service.py    # RAG 检索（ChromaDB + SimpleEmbedding）
│   │   ├── llm_service.py    # 智谱AI GLM 接口封装
│   │   ├── tts_service.py    # Edge-TTS 语音合成
│   │   ├── asr_service.py    # faster-whisper 语音识别
│   │   └── emotion_service.py # 情绪检测
│   └── websocket/
│       └── chat_ws.py       # WebSocket 实时聊天处理
│
├── h5/                     # 游客移动端 (port 3000)
│   └── src/
│       ├── views/           # Login, Register, Home, RoutePlan, History, User, DigitalHuman
│       ├── components/      # Live2DViewer.vue（占位组件）
│       ├── store/           # Pinia: user, digitalHuman, chat
│       └── utils/           # api.js, websocket.js
│
└── admin/                  # 管理后台 (port 3001)
    └── src/
        └── views/           # Dashboard, UserManage, DigitalHumanManage, KnowledgeManage,
                             # ChatLogs, AIConfig, AdminManage, EmotionReport
```

## Commands

### 一键启动

```bash
python startup.py
```

### 分别启动

```bash
# 1. 后端 (port 5001)
cd backend
pip install -r requirements.txt
python init_db.py          # 建库 + 种子数据 + 向量库
python app.py

# 2. H5 移动端 (port 3000)
cd h5
npm install
npm run dev

# 3. Admin 后台 (port 3001)
cd admin
npm install
npm run dev
```

### LiveTalking（3D 数字人引擎 — 待集成）

```bash
cd D:\codeProject\livetalking\LiveTalking
pip install -r requirements.txt
python app.py              # 默认 port 8000
```

## Architecture notes

### 启动流程 (`app.py`)

`create_app()` 在 `backend/app.py` 中：
1. 加载 `config.py` 配置
2. 初始化 Flask + CORS + SQLAlchemy + Flask-Sock
3. 注册 `/api/admin/` 和 `/api/user/` 两个蓝图
4. 注册 WebSocket 路由 `/ws/chat`
5. 自动建表（`db.create_all()`）
6. 首次请求时延迟初始化 ASR 模型

### RAG 流水线

1. **文档解析**：`KnowledgeProcessor` 解析 docx/xlsx/txt → 分块（200 字，50 重叠）
2. **向量化**：`SimpleEmbedding`（384 维哈希特征，无需 ML 模型，轻量快速）
3. **检索**：ChromaDB 查询 top-3 文档
4. **生成**：拼接 RAG 上下文 → 智谱 GLM-5.2 生成回答
5. **后处理**：情绪检测 → TTS 合成 → WebSocket 推送

### WebSocket 实时流水线 (`chat_ws.py`)

```
客户端消息 → 解析类型(text/audio/image)
  → ASR 转写（如果是音频）
  → RAG 检索相关知识
  → GLM 流式生成
  → 逐句拆分（按标点符号）
  → 每句 Edge-TTS 合成 MP3
  → base64 编码 + WebSocket 推送
  → 情绪检测 + 通知推送
  → 保存对话日志到 SQLite
```

支持实时打断（`is_interrupted` 标志）。

### 数据模型（8 个表）

| 模型 | 说明 |
|------|------|
| Admin | 管理员账户 |
| User | 游客账户 |
| ChatLog | 问答日志（含情绪、语音时长、图片路径） |
| FaqKnowledge | 旧版 FAQ 表 |
| KnowledgeCategory | 知识分类（5 个默认分类） |
| Knowledge | 新版知识条目（支持版本控制） |
| KnowledgeVersion | 知识版本历史 |
| DigitalHuman | 数字人配置（名称、声音、语速） |

### API 响应格式

所有接口返回 `{ code: 200, message: "...", data: ... }`。
成功 `code=200`，错误 `code=400/401/500`。

### 认证方式

- **后台**：Flask session（cookie），管理员登录后服务端维护会话
- **游客端**：`/api/user/login` 后维护 session，游客 ID 存储在 session 中

### LiveTalking 集成方案（待实现）

见 `digital.md` 详细规划。核心改动点：

1. **后端新增 `LiveTalkingService`**：封装 `POST /api/human` 调用
2. **H5 `Live2DViewer.vue` → WebRTC `<video>`**：用 LiveTalking 的 WebRTC 视频流替代 Live2D 占位
3. **TTS 可保留在 backend 或迁移到 LiveTalking**：当前 backend TTS 已工作，可逐步迁移

### Cross-cutting concerns

- **降级策略**：LiveTalking 不可用时，H5 回退到纯文字+语音回答（当前已支持），不影响核心问答
- **API key 硬编码**：`config.py` 中智谱 API key 为开发便利硬编码，生产环境应通过环境变量覆盖
- **Embedding 无模型依赖**：`SimpleEmbedding` 是哈希特征向量，不依赖 PyTorch/sentence-transformers，启动快
- **ASR 懒加载**：faster-whisper 模型在首次语音请求时才加载到内存
- **数据库**：SQLite 单文件 `lingshan.db`，无迁移框架（`db.create_all()` 自动建表）

### 前端注意事项

- **纯 JavaScript**（非 TypeScript），编辑 `.js`/`.vue` 文件即可
- **两个独立 Vite 项目**（h5/ 和 admin/），需分别 `npm install` 和 `npm run dev`
- **Vant 4 组件**在 h5 中按需引入，Element Plus 在 admin 中全局注册
- **WebSocket 客户端**（`h5/src/utils/websocket.js`）支持自动重连（3s）、心跳（25s）、音频队列播放
