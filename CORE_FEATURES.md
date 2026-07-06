# 灵山胜境 AI 数字人导游系统 — 核心功能文档

> 最后更新：2026-07-06  
> 项目路径：`ai_leader_dig/` (导游大脑) + `LiveTalking/` (3D渲染引擎)

---

## 一、项目架构

```
┌─────────────────────────────────────────────────────┐
│                    H5 游客端 (Vue3)                  │
│  Home.vue  DigitalHuman.vue  History.vue  RouteMap  │
│  端口:3000                                           │
└────────┬──────────────────────────────┬─────────────┘
         │ WebSocket (chat_ws.py)       │ HTTP API
         ▼                              ▼
┌─────────────────────────────────────────────────────┐
│              ai_leader_dig 后端 (Flask)              │
│  RAG知识库 → LLM智谱GLM → TTS → LiveTalkingService  │
│  端口:5001                                           │
└────────────────────────┬────────────────────────────┘
                         │ HTTP API (/human, /interrupt_talk)
                         ▼
┌─────────────────────────────────────────────────────┐
│            LiveTalking 3D引擎 (aiohttp)              │
│  TTS合成 → 音频特征提取 → AI口型推理 → WebRTC推流    │
│  端口:8010                                           │
└─────────────────────────────────────────────────────┘
```

### 启动命令

```bash
# 1. LiveTalking
cd LiveTalking && python app.py

# 2. 后端
cd ai_leader_dig/backend && python app.py

# 3. H5 前端
cd ai_leader_dig/h5 && npm run dev

# 4. 管理后台
cd ai_leader_dig/admin && npm run dev
```

---

## 二、实时打断系统

### 2.1 深度管线冲洗 (LiveTalking)

**问题**：用户点击打断后，数字人仍继续说话 2-5 秒。

**原因**：打断信号只清了 TTS 消息队列，下游 6 级队列积压未清理。

**修复**：`base_avatar.py` `flush_talk()` 清空所有管线队列：

```
TTS._cancel_event  →  ASR.queue  →  feat_queue  →  output_queue
→  res_frame_queue  →  WebRTC PlayerStreamTrack  →  silence
```

关键文件：`LiveTalking/avatars/base_avatar.py`、`tts/base_tts.py`、`avatars/audio_features/base_asr.py`

### 2.2 前端打断按钮

- 数字人说话时按钮**始终可见**（`v-if="isProcessing || isSpeaking"`）
- `lt_synced` 标志通过 `websocket.js` 正确传递到前端
- 后端两阶段等待：先等说话开始 → 再等说话结束 → 才发 `done`

### 2.3 打断方式

| 方式 | 触发 |
|------|------|
| 点击 ⏹ 按钮 | `stopReply()` → `ws.sendInterrupt()` |
| 打字发送 | `sendText()` 检测 `isSpeaking` → 自动打断 |
| (待实现) 语音打断 | A模式通话，VAD 检测到说话 → 自动打断 |

---

## 三、语音输入（按住说话）

### 3.1 交互设计

```
空闲:   [📷] [___输入问题...___]    [🎤]  [➤]
语音模式: [📷] [  🎙️ 请按住说话  ]    [✕]  [➤]
录音中:  [📷] [  🎙️ 正在聆听...  ]    [✕]  [➤]   ← 红色
```

### 3.2 静音检测

- 录音 < 0.5 秒 → 误触，提示"未检测到声音"
- 音频数据 < 2KB → 无声，不发送
- 正常 → 发 WebSocket 音频 → 自动退出语音模式

### 3.3 关键文件

- `h5/src/views/Home.vue` — `enterVoiceMode()`、`startHoldSpeak()`、`stopHoldSpeak()`
- `h5/src/components/Live2DViewer.vue` — WebRTC 视频渲染 + 绿幕抠像

---

## 四、数字人场景动作

### 4.1 目录结构

```
data/avatars/{avatar_id}/
├── actions.json          ← 动作配置
├── actions/
│   ├── welcome/          ← 欢迎动作帧 + audio.wav
│   ├── thinking/         ← 思考动作帧（循环播放）
│   ├── gesture_1/        ← 自定义手势1
│   └── gesture_2/        ← 自定义手势2
```

### 4.2 actions.json 格式

```json
[
  {"scene": "welcome",  "audiotype": 2, "imgpath": "actions/welcome"},
  {"scene": "thinking", "audiotype": 3, "imgpath": "actions/thinking"},
  {"scene": "gesture_1","audiotype": 4, "imgpath": "actions/gesture_1"}
]
```

### 4.3 触发时机

| 场景 | audiotype | 触发 |
|------|-----------|------|
| 欢迎 | 2 | WebSocket 连接建立时 |
| 思考 | 3 | LLM 开始处理问题时 |
| 正常说话 | 0 | TTS 音频进来时（自动） |
| 待机 | 1 | 无音频时（自动） |

### 4.4 制作动作帧

```bash
# 录制 2-5 秒动作视频，然后抽帧
ffmpeg -i welcome.mp4 -vf fps=25 data/avatars/1/actions/welcome/%05d.jpg
```

关键文件：`LiveTalking/avatars/base_avatar.py` `__loadcustom()`、`set_custom_state()`、`chat_ws.py`

---

## 五、地图路线导航

### 5.1 技术选型

- **Canvas** 画路线预览（无需任何外部依赖）
- **Leaflet + OpenStreetMap** 交互地图（免费，无需 API Key）
- **高德 URI Scheme** 跳转手机地图 App 导航

### 5.2 交互流程

```
用户问"怎么去灵山大佛"
  ↓ LLM 自然语言回答（不含 JSON）
  ↓ 后端 extract_route_info() 检测路线意图
  ↓ 发送 MSG_TYPE_ROUTE 到前端
  ↓ AI 气泡下出现 [🗺️ 查看路线] 按钮
  ↓ 点击 → 直接进入 RouteMap 页面
  ↓
RouteMap 页面：
  ├─ 路线概览卡片（起点→途经→终点）
  ├─ AI 导游建议文字
  ├─ Canvas 路线预览图
  ├─ Leaflet 交互地图（可缩放拖拽）
  ├─ [🧭 跳转地图App导航] 按钮
  └─ [📍 获取我的位置] 按钮
```


问题 2：地图 + 路线规划 + 对话记录的连通

                    ┌──────────────┐
                    │   RouteMap   │  统一的地图展示页
                    │  接收标准参数  │  origin/destination/waypoints/mode
                    └──────┬───────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   Home.vue           RoutePlan.vue        History.vue
  (AI回答→路线按钮)    (预设路线卡片)       (历史对话→路线按钮)
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                    都有"查看路线"按钮
                    统一跳到 RouteMap

各页面入口

┌───────────┬───────────────────────────────────┬────────────────────────────┐
│   页面    │             触发方式              │        路线数据来源        │
├───────────┼───────────────────────────────────┼────────────────────────────┤
│ Home      │ AI 回复检测到路线 → 气泡下显示 🗺️ │ LLM 提取的 route_data ✅   │
│           │  查看路线                         │ 已有                       │
├───────────┼───────────────────────────────────┼────────────────────────────┤
│ RoutePlan │ 预设路线卡片 → 加 🗺️ 查看路线     │ 本地的路线 JSON（已有      │
│           │ 按钮                              │ spots 数组）               │
├───────────┼───────────────────────────────────┼────────────────────────────┤
│ History   │ 历史对话项 → 如果是路线问题，加   │ 从存储的 answer_text       │
│           │ 🗺️ 图标                           │ 提取路线信息               │
└───────────┴───────────────────────────────────┴────────────────────────────┘

具体交互

RoutePlan（路线规划）：
现在: 卡片只展示文字，没有跳转
改为: 每条路线卡片下面加 [🗺️ 在地图上查看]
      → 带上 origin/destination/waypoints → RouteMap

History（对话记录）：
现在: 只展示对话文字
改为: 如果该对话是路线相关（后端存了 route_data 或回答含路线关键词）
      → 列表项右侧显示 🗺️ 图标
      → 点击 → 提取路线信息 → RouteMap
      → 或者在 ChatLog 表里加个 route_data 字段存下来

数据传递方式

统一用 URL query 传给 RouteMap：

/route-map?origin=南门&destination=灵山大佛&waypoints=佛足坛,九龙灌浴&mode=walk&summary=步行游览

### 5.3 三个入口

| 入口 | 触发 | 路线数据来源 |
|------|------|-------------|
| Home 对话 | AI 检测到路线意图 | LLM `extract_route_info()` |
| RoutePlan | 点预设路线卡片 🗺️ | 本地路线 JSON |
| History | 历史会话有路线数据 | ChatLog `route_data` 字段 |

### 5.4 景区坐标

硬编码在 `RouteMap.vue` 的 `SPOT_COORDS` 中，覆盖灵山 14 个主要景点。

### 5.5 关键文件

- `backend/websocket/chat_ws.py` — 路线检测 + route 消息发送
- `backend/services/llm_service.py` — `extract_route_info()`、`_build_route_data()`
- `h5/src/views/RouteMap.vue` — Canvas + Leaflet 双地图
- `h5/src/views/RoutePlan.vue` — 预设路线→RouteMap 跳转
- `h5/src/views/History.vue` — 历史会话→RouteMap 跳转
- `h5/src/views/Home.vue` — AI 气泡路线按钮

---

## 六、多轮对话历史

### 6.1 数据结构

```sql
ChatLog:
  session_id   VARCHAR(64)   -- 同一 WebSocket 连接的会话 ID
  route_data   TEXT          -- 路线 JSON（可选）
  (其他字段: user_id, question_text, answer_text, emotion_label...)
```

### 6.2 前端展示

```
┌─────────────────────────────────┐
│ 💬 灵山大佛怎么去         🗺️  ▼ │  ← 会话卡片
│   07-06 15:30 · 3 轮对话        │
├─────────────────────────────────┤
│ 🙋 灵山大佛怎么走               │  ← 展开的对话
│ 🤖 从南门出发...                │
│ 🕐 07-06 15:30  💬 平静         │
│ ───────────────────             │
│ 🙋 佛足坛要门票吗               │  ← 第2轮
│ 🤖 佛足坛是免费的...            │
│ 🕐 07-06 15:31  😊 微笑         │
└─────────────────────────────────┘
```

一个 WebSocket 连接 = 一个 Session = 一次会话，可包含多轮 QA。

---

## 七、数字人形象管理

### 7.1 管理后台配置

```
数字人管理页面：
  ├─ 名称（如"女导游"）
  ├─ Avatar文件夹（下拉选择 data/avatars/ 下的形象）
  ├─ 语速/语调/音色
  ├─ 启用状态
  └─ [确认保存]
```

### 7.2 H5 切换

```
H5 "切换数字人导游" 页面：
  → 选择数字人 → store 更新
  → Live2DViewer 监听 dhId 变化
  → WebRTC 断开重连（传新 avatar_id）
  → LiveTalking 加载新形象
```

### 7.3 数据流

```
管理后台 → DigitalHuman.model_path (如 "1")
  → API /user/digital-humans → H5 Store
  → Live2DViewer.connectLiveTalking("1", ...)
  → POST /offer { avatar: "1" }
  → LiveTalking 加载 data/avatars/1/
```

---

## 八、绿幕抠像

`Live2DViewer.vue` 支持可选的 Canvas 实时绿幕抠像：

```html
<Live2DViewer :chrome-key="true" key-color="#00FF00" :threshold="0.3" />
```

- `chromeKey`：开关（默认 false）
- `keyColor`：要抠的颜色（默认绿色 #00FF00）
- `threshold`：容差 0-1（默认 0.3）

原理：WebRTC 视频 → 隐藏 `<video>` → Canvas 逐帧读像素 → 匹配颜色设 alpha=0 → 显示透明

---

## 九、项目分支

| 项目 | 分支 | 说明 |
|------|------|------|
| ai_leader_dig | `feature/zdy` | 导游大脑所有功能 |
| LiveTalking | `feature/deep-pipeline-flush` | 深度管线冲洗 + 场景动作 |
