# 🪷 灵山胜境AI数字人导游系统

> 第十五届中国软件杯大赛 A5 赛题作品

## 项目简介

灵山胜境AI数字人导游系统是一套基于 **3D 数字人引擎 + RAG 智能问答** 的景区 AI 导游解决方案，包含：
- **游客移动端H5**：面向游客，提供 3D AI 数字人导游交互、语音/文字/图片提问、智能路线规划等功能
- **管理员PC后台**：面向运营人员，提供数字人管理、知识库管理、对话日志、数据大屏、AI参数配置等功能

### 核心架构

```
┌──────────────────────────┐       HTTP        ┌──────────────────┐
│  ai_leader_dig（导游大脑）  │ ────────────────→ │ LiveTalking（3D脸）│
│                          │  POST /api/human   │                  │
│  RAG → 智谱GLM → 回答文本  │ ←─ WebRTC 视频流 ─ │ TTS → 3D Avatar  │
│  知识库 · 路线 · 后台      │                   │ GPU 实时渲染      │
└──────────────────────────┘                   └──────────────────┘
```

- **ai_leader_dig**（本仓库）：导游业务逻辑 + 双端前端。负责 ASR 语音识别、RAG 知识检索、智谱 GLM 对话、知识库管理、数据看板
- **LiveTalking**（`D:\codeProject\livetalking\LiveTalking`，独立项目）：3D 数字人渲染引擎，负责 TTS 语音合成和 Avatar 口播视频流

两个项目独立运行、独立仓库，仅通过 HTTP API 通信。LiveTalking 不可用时自动降级为纯语音模式。

## 项目目录结构

```
ai_leader_dig/
├── startup.py                          # 一键启动脚本（后端）
├── knowledge/                          # 知识库原始文档（景区资料）
│   ├── 灵山胜境 景点结构化数据集.docx
│   ├── 灵山胜境：历史、文化、景点特色与个性化游览指南.docx
│   └── 景点景区旅游数据行为分析数据.xlsx
│
├── backend/                            # 后端服务（Python Flask）
│   ├── app.py                          # Flask主应用入口
│   ├── config.py                       # 全局配置文件（API Key等在此配置）
│   ├── models.py                       # 数据库模型（8张表）
│   ├── init_db.py                      # 数据库初始化脚本
│   ├── requirements.txt                # Python依赖列表
│   ├── routes/
│   │   ├── admin_routes.py             # 管理员RESTful接口
│   │   └── user_routes.py              # 游客RESTful接口
│   ├── services/
│   │   ├── rag_service.py              # RAG知识库检索（ChromaDB）
│   │   ├── asr_service.py              # 语音识别（faster-whisper）
│   │   ├── tts_service.py              # 语音合成（Edge-TTS）
│   │   ├── llm_service.py              # 多模态大模型接口（智谱AI GLM）
│   │   └── emotion_service.py          # 情绪分析
│   └── websocket/
│       └── chat_ws.py                  # WebSocket长连接处理（Flask-Sock）
│
├── h5/                                 # 游客移动端H5（Vue3 + Vant4）
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js                     # 入口
│       ├── App.vue                     # 根组件
│       ├── router/index.js             # 路由配置
│       ├── store/index.js              # Pinia状态管理
│       ├── utils/
│       │   ├── api.js                  # API请求工具
│       │   └── websocket.js            # WebSocket客户端
│       ├── views/                      # 页面组件
│       │   ├── Login.vue               # 游客登录
│       │   ├── Register.vue            # 游客注册
│       │   ├── Home.vue                # 首页（数字人+聊天）
│       │   ├── RoutePlan.vue           # 路线规划
│       │   ├── History.vue             # 对话历史
│       │   ├── User.vue                # 个人中心
│       │   └── DigitalHuman.vue        # 切换数字人
│       └── components/
│           └── Live2DViewer.vue        # 数字人渲染组件（待改造为 WebRTC）
│
└── admin/                              # 管理员PC后台（Vue3 + Element Plus）
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.js                     # 入口
        ├── App.vue                     # 根组件
        ├── router/index.js             # 路由配置
        ├── store/index.js              # Pinia状态管理
        ├── utils/api.js                # API请求工具
        ├── styles/global.css           # 全局样式
        └── views/
            ├── Login.vue               # 管理员登录
            ├── Layout.vue              # 后台布局（侧边栏+顶部栏）
            ├── Dashboard.vue           # 数据大屏（ECharts）
            ├── UserManage.vue          # 用户管理
            ├── DigitalHumanManage.vue  # 数字人管理
            ├── KnowledgeManage.vue     # 知识库管理
            ├── ChatLogs.vue            # 对话日志
            ├── AIConfig.vue            # AI参数配置
            ├── AdminManage.vue         # 管理员管理
            └── EmotionReport.vue       # 游客感受度报告
```

## 数据库设计（8张表）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| admin | 管理员表 | id, 账号, 密码(加密), 创建时间 |
| user | 游客用户表 | id, 用户名, 密码(加密), 手机号, 邮箱, 注册时间 |
| chat_log | 对话日志表 | id, 用户ID, 提问文本, AI回答, 时间, 情绪标签, 语音时长, 数字人ID, 音色, 图片路径 |
| faq_knowledge | FAQ知识库表（兼容） | id, 问题, 答案, 文档来源, 向量同步状态, 创建时间 |
| knowledge_category | 知识分类表 | id, 名称, 编码, 描述, 图标, 排序, 状态, 创建时间 |
| knowledge | 通用知识库表 | id, 分类ID, 标题, 内容, 标签, 来源文件, 关键词, 版本, 向量同步, 状态, 排序, 创建/更新时间 |
| knowledge_version | 知识版本历史表 | id, 知识ID, 版本, 标题, 内容, 标签, 关键词, 创建时间 |
| digital_human | 数字人配置表 | id, 名称, 模型路径, 语速, 语调, 音色, 启用状态, 创建时间 |

### 默认知识分类

| 分类名称 | 编码 | 描述 |
|---------|------|------|
| 常见问答 | faq | 游客常见问题的问答对 |
| 景点讲解词 | scene_intro | 各景点的详细讲解文案 |
| 文史资料 | history | 景区历史文化背景资料 |
| 基本信息 | basic_info | 门票、交通、开放时间等 |
| 游览路线 | route | 推荐游览路线规划 |

## 快速启动

### 0. 启动 LiveTalking（3D 数字人引擎 — 可选）

```bash
cd D:\codeProject\livetalking\LiveTalking
pip install -r requirements.txt
python app.py
# 默认地址: http://127.0.0.1:8000
```

> 注意：LiveTalking 需要 NVIDIA GPU。未启动时，系统自动降级为纯语音模式，不影响核心问答功能。

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python init_db.py          # 建库 + 种子数据 + 构建向量库
python app.py
```

后端启动后：
- API服务：http://localhost:5001
- WebSocket服务：ws://localhost:5001/ws/chat

### 2. 启动游客移动端H5

```bash
cd h5
npm install
npm run dev
```

H5启动后访问：http://localhost:3000

### 3. 启动管理员PC后台

```bash
cd admin
npm install
npm run dev
```

管理员后台访问：http://localhost:3001

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 游客 | 自行注册 | 注册时设置 |

## 关键配置说明

### 1. 大模型 API 配置

编辑 `backend/config.py` 或通过管理后台 `/ai-config` 页面配置：

```python
LLM_API_KEY = "your-api-key"           # 智谱AI API密钥
LLM_API_BASE = "https://open.bigmodel.cn/api/paas/v4"
LLM_MODEL_NAME = "glm-5.2"            # 文本模型
LLM_VISION_MODEL = "glm-5v"           # 视觉模型（图片识别）
```

未配置时系统使用内置模拟回复模式（限灵山景区相关知识）。

### 2. 数字人模型

- **3D 模式**（推荐）：启动 LiveTalking 服务，H5 通过 WebRTC 获取实时视频流。详见 `digital.md`
- **降级模式**：LiveTalking 不可用时，H5 显示静态形象 + 本地 TTS 语音回答

### 3. 语音识别（ASR）

默认 faster-whisper `base` 模型，首次启动自动下载。配置：

```python
WHISPER_MODEL_SIZE = "base"  # tiny / base / small / medium
```

### 4. 语音合成（TTS）

默认 Edge-TTS，音色 `zh-CN-XiaoxiaoNeural`（晓晓）。可选音色：晓晓、云希、云扬、晓伊、晓涵。

## 技术栈总览

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask | 3.1+ |
| 数据库 | SQLite (Flask-SQLAlchemy) | 3.x |
| WebSocket | Flask-Sock | 0.8+ |
| ASR语音识别 | faster-whisper | 1.x |
| TTS语音合成 | Edge-TTS | 8.x |
| LLM大模型 | 智谱AI GLM-5.2 + GLM-5V | OpenAI兼容 |
| 向量数据库 | ChromaDB | 1.5+ |
| Embedding | 自定义 SimpleEmbedding（384维哈希） | — |
| 3D数字人 | LiveTalking（MuseTalk，WebRTC推流） | 独立部署 |
| H5前端 | Vue3 + Vant4 | 3.x / 4.x |
| 管理后台 | Vue3 + Element Plus + ECharts | 3.x / 2.x / 5.x |
| 状态管理 | Pinia | 2.x |

## 功能清单

### 游客端（H5）
- [x] 游客注册/登录
- [x] 多数字人切换
- [ ] 3D 数字人实时渲染（WebRTC 接入 LiveTalking — **开发中**）
- [x] 文字提问 + WebSocket 流式推送
- [x] 语音提问（录音 + ASR 转写）
- [x] 图片上传提问（GLM-5V 多模态识别）
- [x] 实时打断机制
- [x] 智能路线规划（3套方案）
- [x] 对话历史记录
- [x] 情绪联动
- [x] 国风浅青+淡金UI设计

### 管理员端（PC后台）
- [x] 管理员登录/鉴权
- [x] 数据大屏（ECharts图表：趋势/热门问题/情绪分布/偏好分析）
- [x] 用户管理
- [x] 数字人管理（CRUD）
- [x] 知识库管理（多维度筛选 + 版本控制 + 批量导入导出 + 文件检测）
- [x] 知识分类管理
- [x] 对话日志管理（搜索/筛选/Excel导出）
- [x] AI参数配置（API Key/地址/模型）
- [x] 管理员账号管理
- [x] 游客感受度报告（LLM 情感分析洞察）
- [ ] LiveTalking 连接配置 — **待开发**
- [ ] 数字人声音试听 — **待开发**

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | — | 智谱AI API Key |
| `LIVETALKING_API_URL` | `http://127.0.0.1:8000` | LiveTalking 地址 |
| `VITE_LIVETALKING_URL` | `http://127.0.0.1:8000` | LiveTalking WebRTC 地址 |
