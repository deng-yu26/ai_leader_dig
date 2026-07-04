实时数字人渲染模块：LiveTalking
开源仓库：https://github.com/lipku/LiveTalking
开源协议：Apache 2.0 License
集成说明：本系统原有前端 Live2D 卡通数字人作为轻量化备选；新增本地离线部署 LiveTalking 实现真人 3D 数字人交互，通过独立 HTTP 服务与 Flask 后端解耦通信。团队自主封装 LiveTalkingService 调度层，打通景区 RAG 问答链路与数字人语音、肢体动作驱动，实现游客文字 / 语音提问后数字人同步播报讲解。模型、视频渲染全本地离线推理，无第三方付费 API、无 Token 消耗

数字人表情动作采用双通道驱动方案：
底层 Audio2Face 模型解析 TTS 语音语调，自动生成同步唇形、眨眼、头部微动，保证基础自然度；
自主设计 LLM 语义情感输出链路，大模型根据讲解内容输出情绪标签与肢体动作指令，实时控制数字人切换微笑、庄重等表情，触发抬手、挥手导游专属手势，实现语言语义与虚拟人动作深度匹配，解决传统数字人表情僵硬、动作与内容脱节问题。

端口冲突：LiveTalking 固定 8010，后端 5001，前端 5173，三个端口互不占用；
显卡要求：无 N 卡只能跑 Wav2Lip 轻量模式，画面卡顿，答辩建议带 RTX 显卡笔记本；
跨域：本地开发 iframe 直接访问 127.0.0.1:8010 无限制；打包部署时配置 Nginx 反向代理；
消息不同步：WebSocket 推送回答和 LiveTalking 下发接口存在微小延迟，可在后端加短暂 sleep 同步音画。


---
现在的数据流

Home.vue                       Live2DViewer.vue                LiveTalking
  │                                  │                             │
  │  ──── WebSocket 提问 ────→ 后端  │                             │
  │                                  │                             │
  │  ←── text_chunk + audio ────    │  ←── WebRTC 视频流 ────    │
  │                                  │                             │
  │        ┌─────────────────────────┤                             │
  │        │ <video srcObject=r.stream>                            │
  │        │ 3D 导游口播画面                                          │
  │        │ + 本地 TTS 音频                                          │

---
问题1 有画面但缺少表情口型
原因：接口调用错误，并且应该传入 sessionid。

前端：
  rtc.js          ← /offer 响应里捕获 sessionid
  Live2DViewer    ← 暴露 getSessionId() 给父组件
  Home.vue        ← 定时同步 sessionid → WebSocket
  websocket.js    ← 每条消息带 lt_sessionid

后端：
  chat_ws.py      ← 提取 lt_sessionid → 传给 LiveTalkingService
  livetalking_service.py ← /human + /interrupt_talk + 带 sessionid


---
问题2 切换数字人形象

目前状态

LiveTalking 数据目录:
  data/avatars/
    └── wav2lip256_avatar1/    ← 只有 1 个 demo 形象

你启动时的命令:
  python app.py                  ← 没指定 --avatar_id，默认用上面这个

修改数字人形象有两个层级

层级 1：换一个 3D 形象（生成新 Avatar）

需要一个干净的说话视频（正脸、口齿清晰、背景干净、3-5 分钟），然后：

录制视频 → LiveTalking 自动提取帧 → 检测人脸 → 生成 Avatar 数据包
         → 存入 data/avatars/新名字/
         → 重启时 --avatar_id 新名字

LiveTalking 自带这个功能：打开 http://127.0.0.1:8010/avatar.html，上传视频即可自动生成。也可以命令行跑 genavatar.py。

层级 2：多个形象之间切换

LiveTalking 的 /offer 接口已经支持按会话切换形象：

# app.py line 80
avatar_id = params.get('avatar', opt.avatar_id)  # offer 里带 avatar 就能切换

也就是说，前端 WebRTC 握手时带上 "avatar": "形象名"，LiveTalking 就会加载不同的人。你不需要重启 LiveTalking。

现在的 DigitalHumanManage.vue（管理后台）存的 model_path 字段正好可以用来做这个——把它对应到 LiveTalking 的 avatar_id。

---
实现路径

┌───────────────┬───────────────────────────────────────────────────┬────────────────────┐
│     步骤      │                      做什么                       │       复杂度       │
├───────────────┼───────────────────────────────────────────────────┼────────────────────┤
│ 生成多个形象  │ 录视频 → LiveTalking 处理 → 得到多个 avatar 包    │    需要视频素材    │
├───────────────┼───────────────────────────────────────────────────┼────────────────────┤
│ 前端传 avatar │ RTC 握手时把当前选中的形象名传给 /offer           │ 改 rtc.js 加个参数 │
├───────────────┼───────────────────────────────────────────────────┼────────────────────┤
│ 管理后台对接  │ DigitalHumanManage 的形象管理真正联动 LiveTalking │     阶段 ⑤ 做      │
├───────────────┼───────────────────────────────────────────────────┼────────────────────┤
│ H5 切换形象   │ DigitalHuman.vue 选不同形象 → 重新 WebRTC 握手    │ 已经有页面，补逻辑 │
└───────────────┴───────────────────────────────────────────────────┴────────────────────┘

---
现在你能马上做的

1. 上传你自己的视频生成新形象：打开 http://127.0.0.1:8010/avatar.html，选择一个干净说话视频，生成
2. 生成后 data/avatars/ 下会多一个目录，重启 LiveTalking 时指定 --avatar_id 新名字