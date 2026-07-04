# 景区导览AI数字人导游系统 — 开发任务清单

> 更新日期：2026-07-03
> 架构方案：ai_leader_dig（导游大脑）+ LiveTalking（3D 脸），HTTP API 协作，独立部署
> 赛题：第十五届中国软件杯大赛 A5 — 景区导览服务AI数字人
> 当前状态：后端/H5/Admin 基础功能已就绪，LiveTalking 3D 数字人待集成

---

## 开发阶段总览

| 阶段 | 内容 | 对应赛题分值 | 状态 |
|------|------|:--:|:--:|
| ① 打通链路 | 后端接入 LiveTalking API，回答文本 → 3D 导游说话 | 功能完整 40 | ❌ |
| ② 前端改造 | Live2DViewer 占位 → WebRTC 视频 + 交互优化 | 体验 20 | ❌ |
| ③ RAG 准确率 | 基于官方资料包调优，做到 90%+ | 技术 15 | ⚠️ 基础可用 |
| ④ 多模态 | 景点图片识别（GLM-5V 已对接，补前端交互） | 技术 15 | ⚠️ 后端已有 |
| ⑤ 管理后台 | 形象配置 UI + 数据大屏完善 + 感受度报告 | 功能完整 40 | ⚠️ 基础可用 |
| ⑥ 文档+视频 | 设计文档、PPT、演示视频 | 文档 10 | ❌ |

---

## 一、阶段 ①：打通 API 链路 🔴

### 1.1 后端新增 LiveTalkingService

- **当前状态**：`digital.md` 有规划，无任何实现代码。TTS 在后端本地完成（Edge-TTS），回答文本没有发送给 LiveTalking。
- **需求**：LLM 生成回答后，同时发送给 LiveTalking 进行 TTS + 3D Avatar 口播。
- **下一步**：
  1. 在 `config.py` 增加 `LIVETALKING_API_URL` 配置（默认 `http://127.0.0.1:8000`）
  2. 新建 `backend/services/livetalking_service.py`：封装 `send_text()`、`interrupt()` 方法
  3. 在 `chat_ws.py` 的 WebSocket 流式流水线中，每生成一句就调用 `LiveTalkingService.send_text(sentence)`
  4. LiveTalking 不可用时不影响现有文字+语音回答（try/except + 日志）
  5. 保留现有 TTS 降级路径（LiveTalking 挂了，本地 TTS 继续用）
- **相关文件**：
  - `backend/config.py` — 增加配置项
  - `backend/services/livetalking_service.py` — **新建**
  - `backend/websocket/chat_ws.py` — 增加调用
- **预估时间**：0.5 天

### 1.2 TTS 策略决策

- **当前状态**：Edge-TTS 在 backend 本地合成，WebSocket 推送 base64 音频。
- **选择**：
  - **A. 保留本地 TTS**：LiveTalking 只用 `/api/human` 的 `type: "echo"` 模式（传入文本），LiveTalking 内部 TTS 合成。两套 TTS 并行（本地给 H5 降级，LiveTalking 给 3D 画面）
  - **B. 迁移到 LiveTalking**：本地 TTS 逐步废弃，全部由 LiveTalking 负责 TTS + 口播
- **建议**：先选 A（改动最小），后续看效果决定是否迁移
- **预估时间**：此项为决策，不占开发时间

---

## 二、阶段 ②：前端改造 🔴

### 2.1 Live2DViewer.vue 重构为 WebRTC 视频组件

- **当前状态**：`h5/src/components/Live2DViewer.vue` 是 235 行 STUB 占位组件。所有 Live2D SDK 方法都是 `console.log()`，实际只显示荷花 emoji + 浮动动画。
- **需求**：替换为 LiveTalking 的 WebRTC `<video>` 元素，展示 3D 导游实时画面。
- **下一步**：
  1. 重写 `Live2DViewer.vue` 模板：Canvas 占位 → `<video>` 元素
  2. 新建 `h5/src/utils/rtc.js`：封装 WebRTC 连接逻辑
     - 创建 RTCPeerConnection
     - 生成 SDP offer → POST 到 LiveTalking `/offer`
     - 接收 answer → setRemoteDescription
     - 监听 track 事件 → 设置 video.srcObject
  3. 增加连接状态指示（加载中 / 已连接 / 断开 / 重连中）
  4. 增加 `VITE_LIVETALKING_URL` 环境变量
  5. LiveTalking 不可用时显示降级 UI（荷花 + "3D 导游离线" 提示 → 回退纯语音模式）
- **相关文件**：
  - `h5/src/components/Live2DViewer.vue` — 重写
  - `h5/src/utils/rtc.js` — **新建**
  - `h5/src/store/index.js` — 增加 RTC 状态
  - `h5/vite.config.js` — 增加环境变量
- **预估时间**：1 天

### 2.2 游客交互页面优化

- **当前状态**：`Home.vue` 有聊天列表 + 输入栏 + 快捷操作，基本可用。
- **需求**：3D 视频作为背景 + 交互 UI 叠加（参考视频通话布局）。
- **下一步**：
  1. 3D 视频全屏背景 + 底部半透明交互区
  2. 文字/语音/图片按钮悬浮在视频下方
  3. 回答文字以字幕形式悬浮显示
  4. 移动端适配（安全区、横竖屏）
- **相关文件**：
  - `h5/src/views/Home.vue` — 布局改造
  - `h5/src/components/Live2DViewer.vue` — 尺寸/位置适配
- **预估时间**：1 天

---

## 三、阶段 ③：RAG 准确率优化 🔴

### 3.1 基于官方资料包验证知识库

- **当前状态**：`knowledge/` 目录有 3 份景区文档，`KnowledgeProcessor` 可解析 docx/xlsx。已有 20 条 hot FAQ + SQLite 知识条目。ChromaDB 使用自定义 SimpleEmbedding。
- **问题**：SimpleEmbedding 是哈希特征（非语义向量），检索精度可能不足；未做过系统性准确率测试。
- **下一步**：
  1. 确认 `knowledge/` 中文档是否就是官方资料包（与 `示范景区公开资料包/` 对比）
  2. 验证文档解析覆盖率：确保所有景点、文史、FAQ 都被正确分块入库
  3. 如 SimpleEmbedding 检索精度不够，评估切换为 `BAAI/bge-small-zh-v1.5`（需要 sentence-transformers）
  4. 更新 `init_db.py` 的知识导入脚本
- **相关文件**：
  - `backend/services/rag_service.py` — 评估 embedding 方案
  - `backend/init_db.py` — 更新种子数据
  - `knowledge/` — 确认资料完整性
- **预估时间**：0.5 天（验证）/ 1 天（如需换 embedding）

### 3.2 准确率测试与调优

- **当前状态**：无系统性准确率测试。
- **需求**：事实性问答准确率 ≥ 90%。
- **下一步**：
  1. 准备 50-100 条测试问题集（景点信息、历史文化、路线、服务设施、边界问题）
  2. 编写 `backend/test_accuracy.py`：批量调用问答接口，自动评分
  3. 统计准确率，定位错误类型（检索失败 vs LLM 幻觉 vs 边界误判）
  4. 针对性调优：chunk 大小、top-k、prompt 模板、关键词过滤
  5. 迭代直到 ≥ 90%
- **相关文件**：
  - `backend/test_accuracy.py` — **新建**
  - `backend/services/rag_service.py` — prompt 调优
  - `backend/services/llm_service.py` — 参数调优
- **预估时间**：1 天

---

## 四、阶段 ④：多模态集成 🟡

### 4.1 景点图片识别 — 前端交互完善

- **当前状态**：`chat_ws.py` 已支持 `image` 类型消息，`llm_service.py` 已有 `chat_with_image()` 方法（GLM-5V）。但 H5 前端 `Home.vue` 的图片上传交互需确认。
- **需求**：游客拍照上传景点 → GLM-5V 识别 → 结合知识库生成讲解 → 3D 导游播报。
- **下一步**：
  1. 确认 `Home.vue` 图片按钮的交互流程（拍照/相册 → 预览 → 发送）
  2. 确保 WebSocket `image` 消息正确传递 base64 图片
  3. 后端 `chat_ws.py` 图片流程验证：图片 → GLM-5V 识别 → 拼接 RAG → 生成讲解
  4. 如有缺失则补全
- **相关文件**：
  - `h5/src/views/Home.vue` — 图片交互
  - `backend/websocket/chat_ws.py` — 图片处理
  - `backend/services/llm_service.py` — GLM-5V 调用
- **预估时间**：0.5 天

---

## 五、阶段 ⑤：管理后台完善 🟡

### 5.1 数据大屏完善

- **当前状态**：`Dashboard.vue` 已有统计卡片 + 趋势图 + 热门问题 + 情绪饼图 + 偏好分析。
- **待补齐**：
  - [ ] 问题解决率卡片（需后端计算并返回）
  - [ ] 游客关注点分析（热门类别排行，已有部分）
  - [ ] 满意度趋势（已有情绪饼图，可增加趋势线）
- **预估时间**：0.5 天

### 5.2 数字人形象配置 UI

- **当前状态**：`DigitalHumanManage.vue` 支持数字人的 CRUD（名称、模型路径、声音、语速、音调、状态）。`AIConfig.vue` 管理 LLM 参数。但无 LiveTalking 相关配置。
- **需求**：管理员可配置 TTS 声音、语速、音量，可试听预览；可配置 LiveTalking 连接地址。
- **下一步**：
  1. `AIConfig.vue` 增加 LiveTalking 地址配置项
  2. `DigitalHumanManage.vue` 增加声音试听按钮
  3. 配置项同步到后端 `config.py`（或存入 SystemConfig 表）
- **预估时间**：0.5 天

### 5.3 游客感受度报告

- **当前状态**：`EmotionReport.vue` 已有基础页面，后端通过 LLM 生成情感分析洞察。
- **需求**：完善报告内容——游客画像、关注热点、情感趋势、服务建议。
- **预估时间**：0.5 天

---

## 六、阶段 ⑥：文档与演示 🟢

### 6.1 设计文档 + PPT

- **提交要求**：产品总体设计文档 + 方案介绍 PPT
- **内容**：需求分析、方案设计（双项目架构图）、核心技术（RAG + 3D 数字人 + 智谱多模态）、创新要点（LLM 语义驱动表情动作）、产品展示截图、测试数据（准确率 90%+）
- **预估时间**：1 天

### 6.2 演示视频

- **提交要求**：≤7 分钟 .mp4，含创意说明和重点功能展示
- **内容规划**：开场（30s）→ 文字提问（1min）→ 语音提问（1min）→ 拍照识别（1min）→ 路线推荐（30s）→ 管理后台（1.5min）→ 数据大屏（1min）→ 结尾
- **预估时间**：1 天

---

## 七、低优先级 🟢

### 7.1 边界准确率测试

- 系统性测试景区相关性判断和敏感词过滤
- 准备边界测试用例 → 统计误拦截率/漏过率
- **预估时间**：0.5 天

### 7.2 代码质量

- 后端 flake8 检查 + 前端关键组件注释补全
- **预估时间**：0.5 天

### 7.3 移动端适配

- iPhone SE (320px) 到 iPad 全覆盖测试
- 录音按钮、输入框触控区域 ≥ 44px
- **预估时间**：0.5 天

### 7.4 部署支持

- Docker Compose（含 LiveTalking 可选启动）
- Nginx 反向代理配置
- **预估时间**：1 天

---

## 汇总表

| 阶段 | 编号 | 任务 | 预估 | 依赖 |
|------|------|------|------|------|
| ① | 1.1 | 后端新增 LiveTalkingService | 0.5d | LiveTalking 运行 |
| ② | 2.1 | Live2DViewer 重构 WebRTC | 1d | 1.1 |
| ② | 2.2 | 游客交互页面优化 | 1d | 2.1 |
| ③ | 3.1 | 知识库验证与优化 | 0.5-1d | 官方资料包 |
| ③ | 3.2 | 准确率测试调优 | 1d | 3.1 |
| ④ | 4.1 | 图片识别前端交互 | 0.5d | 无 |
| ⑤ | 5.1 | 数据大屏完善 | 0.5d | 无 |
| ⑤ | 5.2 | 形象配置 UI | 0.5d | 无 |
| ⑤ | 5.3 | 游客感受度报告 | 0.5d | 无 |
| ⑥ | 6.1 | 设计文档 + PPT | 1d | 全部完成 |
| ⑥ | 6.2 | 演示视频 | 1d | 全部完成 |
| 🟢 | 7.1-7.4 | 低优先级 | 2.5d | 无 |

**核心链路预估：约 6 天（阶段 ①-⑤）**
**含文档视频：约 8 天**
