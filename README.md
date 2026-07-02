# 🪷 灵山胜境AI数字人导游系统

## 项目简介
灵山胜境AI数字人导游系统是一套基于Web的智能导游解决方案，包含：
- **游客移动端H5**：面向游客，提供AI数字人导游交互、语音/文字/图片提问、智能路线规划等功能
- **管理员PC后台**：面向运营人员，提供数字人管理、知识库管理、对话日志、数据大屏、AI参数配置等功能

## 项目目录结构

```
aileader/
├── startup.py                          # 一键启动脚本（后端）
├── knowledge/                          # 知识库原始文档（景区资料）
│   ├── 灵山胜境 景点结构化数据集.docx
│   ├── 灵山胜境：历史、文化、景点特色与个性化游览指南.docx
│   └── 景点景区旅游数据行为分析数据.xlsx
│
├── backend/                            # 后端服务（Python Flask）
│   ├── app.py                          # Flask主应用入口
│   ├── config.py                       # 全局配置文件（API Key等在此配置）
│   ├── models.py                       # 数据库模型（5张核心表）
│   ├── init_db.py                      # 数据库初始化脚本
│   ├── requirements.txt                # Python依赖列表
│   ├── routes/
│   │   ├── admin_routes.py             # 管理员RESTful接口
│   │   └── user_routes.py              # 游客RESTful接口
│   ├── services/
│   │   ├── rag_service.py              # RAG知识库检索（ChromaDB）
│   │   ├── asr_service.py              # 语音识别（Whisper）
│   │   ├── tts_service.py              # 语音合成（Edge-TTS）
│   │   ├── llm_service.py              # 多模态大模型接口
│   │   └── emotion_service.py          # 情绪分析
│   └── websocket/
│       └── chat_ws.py                  # WebSocket长连接处理
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
│       │   ├── Chat.vue                # 聊天页面
│       │   ├── RoutePlan.vue           # 路线规划
│       │   ├── History.vue             # 对话历史
│       │   ├── User.vue                # 个人中心
│       │   └── DigitalHuman.vue        # 切换数字人
│       └── components/
│           └── Live2DViewer.vue        # Live2D数字人渲染组件
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
        ├── views/
        │   ├── Login.vue               # 管理员登录
        │   ├── Layout.vue              # 后台布局（侧边栏+顶部栏）
        │   ├── Dashboard.vue           # 数据大屏（ECharts）
        │   ├── UserManage.vue          # 用户管理
        │   ├── DigitalHumanManage.vue  # 数字人管理
        │   ├── KnowledgeManage.vue     # 知识库管理
        │   ├── ChatLogs.vue            # 对话日志（含Excel导出）
        │   ├── AIConfig.vue            # AI参数配置
        │   └── AdminManage.vue         # 管理员管理
        └── components/
```

## 数据库设计（8张表）

### 核心表（原有）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| admin | 管理员表 | id, 账号, 密码(加密), 创建时间 |
| user | 游客用户表 | id, 用户名, 密码(加密), 手机号, 邮箱, 注册时间 |
| chat_log | 对话日志表 | id, 用户ID, 提问文本, AI回答, 时间, 情绪标签, 语音时长, 数字人ID, 音色, 图片路径 |
| faq_knowledge | FAQ知识库表（兼容） | id, 问题, 答案, 文档来源, 向量同步状态, 创建时间 |
| digital_human | 数字人配置表 | id, 名称, 模型路径, 语速, 语调, 音色, 启用状态, 创建时间 |

### 通用知识库（新增）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| knowledge_category | 知识分类表 | id, 名称, 编码, 描述, 图标, 排序, 状态, 创建时间 |
| knowledge | 通用知识库表 | id, 分类ID, 标题, 内容, 标签, 来源文件, 关键词, 版本, 向量同步, 状态, 排序, 创建/更新时间 |
| knowledge_version | 知识版本历史表 | id, 知识ID, 版本, 标题, 内容, 标签, 关键词, 创建时间 |

### 默认知识分类

| 分类名称 | 编码 | 描述 |
|---------|------|------|
| 常见问答 | faq | 游客常见问题的问答对 |
| 景点讲解词 | scene_intro | 各景点的详细讲解文案 |
| 文史资料 | history | 景区历史文化背景资料 |
| 基本信息 | basic_info | 门票、交通、开放时间等 |
| 游览路线 | route | 推荐游览路线规划 |

## 知识库管理新功能

### 后端 API（新版）

| 接口 | 方法 | 说明 |
|------|------|------|
| `/admin/knowledge/categories` | GET/POST | 获取/创建知识分类 |
| `/admin/knowledge/categories/<id>` | PUT/DELETE | 更新/删除分类 |
| `/admin/knowledge/list` | GET | 获取知识库列表（支持分类/关键词/标签/状态/排序多维度筛选） |
| `/admin/knowledge/item` | POST | 创建知识条目（自动同步向量库） |
| `/admin/knowledge/item/<id>` | PUT/DELETE | 更新（带版本控制）/删除知识条目 |
| `/admin/knowledge/item/<id>/versions` | GET | 获取版本历史 |
| `/admin/knowledge/item/<id>/restore/<vid>` | POST | 恢复到指定版本 |
| `/admin/knowledge/batch/import` | POST | 批量导入（JSON格式） |
| `/admin/knowledge/batch/export` | GET | 批量导出（JSON格式） |
| `/admin/knowledge/batch/delete` | POST | 批量删除 |
| `/admin/knowledge/search` | GET | 多维度搜索 |
| `/admin/knowledge/detect` | POST | 上传文件自动检测知识类型并提取关键词 |

### 前端界面优化

- **筛选栏**：分类筛选、关键词搜索、标签筛选、状态筛选、排序方式
- **批量操作**：批量导入（JSON）、批量导出、批量删除
- **版本历史**：查看知识条目的历史版本，支持恢复到任意版本
- **分类管理**：可视化管理知识分类
- **文件自动检测**：上传文件后自动识别类型（FAQ/讲解词/文史/基本信息/路线），提取关键词

## 快速启动

### 环境要求
- Python 3.9+
- Node.js 18+

### 第一步：启动后端服务

```bash


# 手动启动


source backend/venv/bin/activate
cd backend
# 安装依赖
pip install -r requirements.txt
python3 app.py



# # 初始化数据库
# python3 init_db.py

# # 启动Flask服务器
# python3 app.py
```

后端启动后：
- API服务：http://localhost:5001
- WebSocket服务：ws://localhost:5001/ws/chat
- 健康检查：http://localhost:5001/api/health

### 第二步：启动游客移动端H5

```bash
# 新开终端
cd aileader/h5

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

H5启动后访问：http://localhost:3000

### 第三步：启动管理员PC后台

```bash
# 新开终端
cd aileader/admin

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

管理员后台访问：http://localhost:3001

## 默认账号

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 游客 | 注册获取 | 注册时设置 |

## 关键配置说明

### 1. 大模型API配置（可选）
编辑 `backend/config.py` 或通过管理后台 `/ai-config` 页面配置：

```python
LLM_API_KEY = "your-api-key-here"     # ★ 替换为实际API密钥
LLM_API_BASE = "https://api.openai.com/v1"  # ★ 替换为实际接口地址
LLM_MODEL_NAME = "gpt-3.5-turbo"     # ★ 替换为实际模型名
```

**注意**：未配置API时，系统会使用内置的模拟回复模式，回复内容严格限定为灵山景区相关知识。

### 2. Live2D数字人模型
Live2D模型文件需放置在 `h5/public/live2d_models/` 目录下，每个数字人一个子目录：
```
h5/public/live2d_models/
├── lingyun/       # 灵韵（默认导游）
├── huixin/        # 慧心（禅意导游）
└── mingyuan/      # 明远（文化导游）
```
每个目录需包含 Live2D Cubism SDK 所需的 model.json / model3.json 和 moc3 文件。

### 3. 语音识别（ASR）
默认使用 faster-whisper base 模型，首次启动时会自动下载。如需更换模型大小，修改 `config.py`：
```python
WHISPER_MODEL_SIZE = "base"  # 可选: tiny/base/small/medium/large-v2
```

### 4. 语音合成（TTS）
基于 Edge-TTS，无需额外配置，默认音色为 `zh-CN-XiaoxiaoNeural`（晓晓）。

## 技术栈总览

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | Flask | 3.1+ |
| 数据库 | SQLite (Flask-SQLAlchemy) | 3.x |
| WebSocket | Flask-Sock | 0.8+ |
| ASR语音识别 | faster-whisper | 1.x |
| TTS语音合成 | Edge-TTS | 8.x |
| 向量数据库 | ChromaDB | 0.5+ |
| 大模型接口 | OpenAI兼容API | - |
| H5前端 | Vue3 + Vant4 | 3.x / 4.x |
| 管理后台 | Vue3 + Element Plus | 3.x / 2.x |
| 数据图表 | ECharts | 5.x |
| 状态管理 | Pinia | 2.x |
| 密码加密 | Werkzeug | 3.x |

## 功能清单

### 游客端（H5）
- [x] 游客注册/登录
- [x] 多数字人切换
- [x] Live2D数字人展示（表情联动、口型驱动）
- [x] 文字提问
- [x] 语音提问（麦克风录音+ASR）
- [x] 图片上传提问（多模态）
- [x] WebSocket实时流式推送（文本+音频+情绪）
- [x] 实时打断机制
- [x] 智能路线规划（3套差异化方案）
- [x] 对话历史记录
- [x] 情绪联动表情
- [x] 国风浅青+淡金UI设计

### 管理员端（PC后台）
- [x] 管理员登录/鉴权
- [x] 数据大屏（ECharts图表）
- [x] 用户管理
- [x] 数字人管理（CRUD）
- [x] 知识库管理（CRUD + 向量同步）
- [x] 对话日志管理（搜索/筛选/Excel导出）
- [x] AI参数配置（API Key/地址/模型）
- [x] 管理员账号管理
- [x] 深蓝商务风格UI