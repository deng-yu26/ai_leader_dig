<template>
  <div class="home-page">
    <!-- 顶部导航 -->
    <div class="home-header">
      <div class="header-left">
        <span class="dh-name" @click="goDigitalHuman">
          🪷 {{ dhStore.currentName }}
        </span>
      </div>
      <div class="header-right">
        <van-icon name="guide-o" size="20" @click="$router.push('/route-plan')" />
        <van-icon name="records-o" size="20" @click="$router.push('/history')" style="margin-left:16px;" />
      </div>
    </div>

    <!-- 快捷功能栏 -->
    <div class="quick-bar">
      <van-button size="mini" plain round @click="showRoutes" class="quick-btn">
        🗺️ 路线
      </van-button>
      <van-button size="mini" plain round @click="showHotQuestions" class="quick-btn">
        🔥 热门
      </van-button>
    </div>

    <!-- Live2D 数字人显示区 -->
    <div class="live2d-container" @click="onTapCharacter">
      <Live2DViewer
        ref="live2dRef"
        :emotion="chatStore.currentEmotion"
        :is-speaking="chatStore.isSpeaking"
        :dh-id="dhStore.currentId"
      />
      <!-- 情绪标签 -->
      <div class="emotion-badge" v-if="chatStore.currentEmotion !== '平静'">
        {{ chatStore.currentEmotion === '热情' ? '🔥' : '😊' }}
        {{ chatStore.currentEmotion }}
      </div>
      <!-- 状态提示 -->
      <div class="status-tip" v-if="chatStore.isProcessing">
        <van-loading type="spinner" size="16" color="#5b8c5a" />
        <span>AI导游思考中...</span>
      </div>
    </div>

    <!-- 对话气泡 -->
    <div class="chat-bubbles" ref="bubbleRef">
      <div v-if="messages.length === 0" class="chat-empty">
        <div class="empty-icon">🪷</div>
        <p class="empty-text">点击数字人开始对话<br>或输入您的问题</p>
      </div>

      <div
        v-for="(msg, i) in messages"
        :key="`${msg.id}-${i}`"
        :class="['bubble', msg.role === 'user' ? 'user-bubble' : 'ai-bubble']"
      >
        <div class="bubble-avatar">
          {{ msg.role === 'user' ? '👤' : '🪷' }}
        </div>
        <div class="bubble-content">
          <div class="bubble-text">{{ msg.text }}</div>
          <div class="bubble-meta">
            <span class="bubble-time">{{ msg.time }}</span>
            <span class="bubble-emotion" v-if="msg.emotion && msg.emotion !== '平静'">
              {{ msg.emotion === '热情' ? '🔥' : '😊' }} {{ msg.emotion }}
            </span>
          </div>
        </div>
      </div>

      <!-- AI思考中加载占位 -->
      <div class="bubble ai-bubble" v-if="chatStore.isProcessing && !hasLastAiMsg">
        <div class="bubble-avatar">🪷</div>
        <div class="bubble-content">
          <div class="bubble-text thinking">
            <van-loading type="ball" size="14" color="#5b8c5a" />
            <span>思考中...</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部输入栏 -->
    <div class="input-bar">
      <div class="input-wrapper">
        <!-- 图片上传按钮 -->
        <van-icon name="photo-o" size="22" color="#5b8c5a" @click="showImageUpload = true" />
        <!-- 文本输入 / 语音模式按住说话 -->
        <input
          v-if="!voiceMode"
          v-model="inputText"
          class="text-input"
          placeholder="输入问题..."
          @keydown.enter="sendText"
        />
        <div
          v-else
          :class="['hold-to-speak', { recording: isRecording }]"
          @mousedown.prevent="startHoldSpeak"
          @mouseup.prevent="stopHoldSpeak"
          @mouseleave.prevent="stopHoldSpeak"
          @touchstart.prevent="startHoldSpeak"
          @touchend.prevent="stopHoldSpeak"
        >
          {{ isRecording ? '🎙️ 正在聆听...' : '🎙️ 请按住说话' }}
        </div>
        <!-- 终止/语音按钮 -->
        <van-icon
          v-if="chatStore.isProcessing || chatStore.isSpeaking"
          name="stop-circle-o"
          color="#e74c3c"
          size="22"
          @click="stopReply"
        />
        <van-icon
          v-else-if="voiceMode"
          name="close"
          color="#999"
          size="22"
          @click="exitVoiceMode"
        />
        <van-icon
          v-else
          name="phone-o"
          color="#5b8c5a"
          size="22"
          @click="enterVoiceMode"
        />
        <!-- 发送按钮 -->
        <van-icon
          name="arrow-up"
          size="20"
          color="#fff"
          class="send-btn"
          @click="sendText"
          v-if="inputText.trim()"
        />
      </div>
    </div>

    <!-- 图片上传弹窗 -->
    <van-action-sheet v-model:show="showImageUpload" title="上传图片提问" close-on-click-action>
      <div class="upload-sheet">
        <van-uploader :after-read="onImageRead" accept="image/*" multiple>
          <van-button icon="photo-o" size="small" class="green-btn">选择图片</van-button>
        </van-uploader>
        <p class="upload-tip">支持JPG、PNG格式，可结合文字提问</p>
      </div>
    </van-action-sheet>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast, showLoadingToast, closeToast, Dialog } from 'vant'
import { useChatStore, useDigitalHumanStore, useUserStore } from '@/store'
import { createWsClient, getWsClient, destroyWsClient } from '@/utils/websocket'
import { getWsInfo } from '@/utils/api'
import Live2DViewer from '@/components/Live2DViewer.vue'

const router = useRouter()
const chatStore = useChatStore()
const dhStore = useDigitalHumanStore()
const userStore = useUserStore()

const inputText = ref('')
const showImageUpload = ref(false)
const isRecording = ref(false)
const voiceMode = ref(false)       // 语音输入模式（输入框变成"按住说话"）
const bubbleRef = ref(null)
const live2dRef = ref(null)
let currentAudioSource = null
let isDiscarded = false
let doneTimeoutId = null           // 旧 done 延迟定时器，新回复开始时清除
let sessionIdTimer = null           // 标记本次回复是否已被丢弃（暂停后忽略剩余片段）

// --- 响应式消息列表 ---
const messages = computed(() => chatStore.messages)
const hasLastAiMsg = computed(() => {
  const msgs = chatStore.messages
  return msgs.length > 0 && msgs[msgs.length - 1].role === 'ai'
})

// ===== 生命周期 =====
onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }

  try {
    const res = await getWsInfo()
    if (res.code === 200) {
      const wsUrl = res.data.ws_url
      createWsClient(wsUrl, {
        user_id: userStore.userInfo?.id || 0,
        digital_human_id: dhStore.currentId
      })
      setupWsHandlers()
    }
  } catch (e) {
    console.warn('WebSocket连接失败，降级为模拟模式:', e)
  }

  await fetchDigitalHumans()

  // 定时同步 LiveTalking sessionid → WebSocket 客户端
  sessionIdTimer = setInterval(() => {
    const sid = live2dRef.value?.getSessionId?.()
    if (sid) {
      const ws = getWsClient()
      if (ws) ws.setLtSessionId(sid)
    }
  }, 500)
})

onUnmounted(() => {
  if (sessionIdTimer) clearInterval(sessionIdTimer)
  destroyWsClient()
})

// --- 消息变化自动滚动 ---
watch(
  () => chatStore.messages.length,
  () => nextTick(() => scrollToBottom())
)

// ===== WebSocket处理器 =====
const audioQueue = ref([])
let isPlayingAudio = false
let audioContext = null

function getAudioContext() {
  if (!audioContext) {
    audioContext = new (window.AudioContext || window.webkitAudioContext)()
  }
  return audioContext
}

function playNextAudio() {
  if (isPlayingAudio || audioQueue.value.length === 0) return
  isPlayingAudio = true

  const audioB64 = audioQueue.value.shift()
  try {
    const audioBytes = Uint8Array.from(atob(audioB64), c => c.charCodeAt(0))
    const ctx = getAudioContext()
    ctx.decodeAudioData(audioBytes.buffer, (buffer) => {
      const source = ctx.createBufferSource()
      currentAudioSource = source
      source.buffer = buffer
      source.connect(ctx.destination)
      source.onended = () => {
        if (currentAudioSource === source) currentAudioSource = null
        isPlayingAudio = false
        if (audioQueue.value.length > 0) playNextAudio()
        else chatStore.isSpeaking = false
      }
      chatStore.isSpeaking = true
      source.start(0)
    }, () => {
      isPlayingAudio = false
      playNextAudio()
    })
  } catch (e) {
    console.warn('[Audio] 播放失败:', e)
    isPlayingAudio = false
    playNextAudio()
  }
}

function setupWsHandlers() {
  const ws = getWsClient()
  if (!ws) return

  // ---- 用户语音识别结果：展示为用户消息 ----
  ws.on('user_text', (text) => {
    if (text) {
      chatStore.addUserMessage(text, 'voice')
      scrollToBottom()
    }
  })

  // ---- AI开始生成：清空音频队列，预创建新AI消息 ----
  ws.on('text_start', () => {
    isDiscarded = false
    // 取消旧的 done 定时器，防止旧回复覆盖新回复的 isSpeaking 状态
    if (doneTimeoutId) {
      clearTimeout(doneTimeoutId)
      doneTimeoutId = null
    }
    chatStore.setProcessing(true)
    chatStore.setEmotion('平静')
    audioQueue.value = []
    isPlayingAudio = false
    // 预创建一条空 AI 消息，后续 text_chunk 直接追加到这条新消息上
    chatStore.addAiMessage('')
  })

  // ---- AI文本片段：追加到当前AI消息 ----
  ws.on('text_chunk', ({ text }) => {
    if (isDiscarded) return
    chatStore.appendAiText(text)
    scrollToBottom()
  })

  // ---- AI文本结束：关闭处理状态 ----
  ws.on('text_end', () => {
    if (isDiscarded) return
    chatStore.setProcessing(false)
  })

  // ---- AI音频片段：加入播放队列 ----
  ws.on('audio_chunk', ({ audio, lt_synced }) => {
    if (isDiscarded) return
    // LiveTalking 同步模式：音频由 WebRTC 视频流提供，本地跳过播放
    if (lt_synced) {
      chatStore.isSpeaking = true
      return
    }
    // 本地 TTS 模式：加入播放队列
    if (audio) {
      audioQueue.value.push(audio)
      if (!isPlayingAudio) playNextAudio()
    }
  })

  // ---- 情绪推送 ----
  ws.on('emotion', (emotion) => {
    if (isDiscarded) return
    chatStore.setEmotion(emotion)
  })

  // ---- 状态消息 ----
  ws.on('status', (status) => {
    showLoadingToast({ message: status, duration: 0, forbidClick: true })
    setTimeout(() => closeToast(), 2000)
  })

  // ---- 错误消息 ----
  ws.on('error', (error) => {
    showFailToast(error)
    chatStore.setProcessing(false)
  })

  // ---- 整个对话完成 ----
  ws.on('done', () => {
    if (isDiscarded) return
    chatStore.setProcessing(false)
    if (audioQueue.value.length === 0) {
      // 使用可取消的定时器，防止旧 done 在新回复开始后覆盖 isSpeaking
      if (doneTimeoutId) clearTimeout(doneTimeoutId)
      doneTimeoutId = setTimeout(() => {
        chatStore.isSpeaking = false
        doneTimeoutId = null
      }, 1000)
    }
  })
}

// ===== 发送文本 =====
function sendText() {
  const text = inputText.value.trim()
  if (!text) return

  if (voiceMode.value) exitVoiceMode()

  inputText.value = ''
  chatStore.addUserMessage(text, 'text')
  scrollToBottom()

  // 数字人正在思考 OR 正在朗读 → 打断后发送新问题
  if (chatStore.isProcessing || chatStore.isSpeaking) {
    const ws = getWsClient()
    if (ws && ws.isConnected.value) {
      ws.sendInterrupt()
      // 丢弃旧回复的所有后续消息
      isDiscarded = true
      audioQueue.value = []
      isPlayingAudio = false
      if (currentAudioSource) {
        try { currentAudioSource.stop() } catch (_) {}
        currentAudioSource = null
      }
      chatStore.setProcessing(false)
      chatStore.isSpeaking = false
      closeToast()
      // 稍等打断生效 + LiveTalking 管线清空，再发新问题
      setTimeout(() => {
        const ws2 = getWsClient()
        if (ws2 && ws2.isConnected.value) ws2.sendText(text)
        else fallbackReply()
      }, 300)
    } else {
      fallbackReply()
    }
    return
  }

  const ws = getWsClient()
  if (ws && ws.isConnected.value) ws.sendText(text)
  else fallbackReply()
}

function fallbackReply() {
  setTimeout(() => {
    chatStore.addAiMessage('您好！我是灵山胜境AI导游。请问有什么可以帮您的？')
    scrollToBottom()
  }, 1000)
}

// ===== 语音输入（按住说话模式） =====
let mediaRecorder = null
let audioChunks = []
let holdStartTime = 0

function enterVoiceMode() {
  voiceMode.value = true
}

function exitVoiceMode() {
  voiceMode.value = false
  if (isRecording.value) {
    stopHoldSpeak()
  }
}

function startHoldSpeak() {
  if (!navigator.mediaDevices?.getUserMedia) {
    showFailToast('当前设备不支持语音输入')
    return
  }

  isRecording.value = true
  audioChunks = []
  holdStartTime = Date.now()

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      mediaRecorder = new MediaRecorder(stream)
      mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data)

      mediaRecorder.onstop = () => {
        const duration = (Date.now() - holdStartTime) / 1000
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })

        // 静音检测：时长太短或数据量太小 → 未检测到声音
        if (duration < 0.5 || audioBlob.size < 2000) {
          showFailToast('未检测到声音，请重试')
          isRecording.value = false
          stream.getTracks().forEach(track => track.stop())
          return
        }

        const reader = new FileReader()
        reader.onload = () => {
          const base64 = reader.result.split(',')[1]
          const ws = getWsClient()
          if (ws && ws.isConnected.value) ws.sendAudio(base64)
        }
        reader.readAsDataURL(audioBlob)
        stream.getTracks().forEach(track => track.stop())
        isRecording.value = false
        // 发送完成后退出语音模式，回到文本输入
        voiceMode.value = false
      }

      mediaRecorder.start()
    })
    .catch(() => {
      showFailToast('麦克风访问被拒绝')
      isRecording.value = false
    })
}

function stopHoldSpeak() {
  if (mediaRecorder && mediaRecorder.state === 'recording') {
    mediaRecorder.stop()
  }
}

function stopReply() {
  const ws = getWsClient()
  if (ws && ws.isConnected.value) ws.sendInterrupt()

  // 丢弃当前回复所有后续消息片段
  isDiscarded = true
  // 取消旧 done 定时器，防止其覆盖新回复的 isSpeaking
  if (doneTimeoutId) {
    clearTimeout(doneTimeoutId)
    doneTimeoutId = null
  }

  audioQueue.value = []
  isPlayingAudio = false
  chatStore.setProcessing(false)
  chatStore.isSpeaking = false

  // LiveTalking 3D 模式：立即静音视频（因引擎无法中断当前句）
  live2dRef.value?.muteVideo?.()
  setTimeout(() => {
    live2dRef.value?.unmuteVideo?.()
  }, 2000)

  if (currentAudioSource) {
    try { currentAudioSource.stop() } catch (_) {}
    currentAudioSource = null
  }

  closeToast()
}

// ===== 图片上传 =====
function onImageRead(file) {
  showImageUpload.value = false
  if (!file?.file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const base64 = e.target.result.split(',')[1]
    const text = inputText.value.trim() || '请分析这张图片'

    chatStore.addUserMessage(text, 'image')
    inputText.value = ''

    const ws = getWsClient()
    if (ws && ws.isConnected.value) {
      ws.sendImage(base64, file.file.name, text)
    } else {
      setTimeout(() => {
        chatStore.addAiMessage('已收到您的图片，正在分析...')
        scrollToBottom()
      }, 1500)
    }
  }
  reader.readAsDataURL(file.file)
}

// ===== 路线推荐（从Chat.vue集成） =====
function showRoutes() {
  Dialog.confirm({
    title: '选择游览路线',
    message: '请选择您感兴趣的路线类型：',
    confirmButtonText: '自然风光',
    cancelButtonText: '文化朝圣',
    showCancelButton: true
  }).then(() => {
    chatStore.addAiMessage('🌄 自然风光路线（5小时全景游）：南门→佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔→灵山精舍→梵宫广场。漫步菩提大道欣赏太湖风光，登顶大佛俯瞰全景，感受人与自然和谐统一。')
    scrollToBottom()
  }).catch(() => {
    chatStore.addAiMessage('🙏 文化朝圣路线（3小时精华游）：南门→佛足坛→九龙灌浴→祥符禅寺→灵山大佛→梵宫→五印坛城。深度体验佛教文化，欣赏梵宫艺术殿堂。')
    scrollToBottom()
  })

  setTimeout(() => {
    Dialog.confirm({
      title: '还有亲子路线',
      message: '是否查看适合家庭出游的亲子路线？',
      confirmButtonText: '查看',
      cancelButtonText: '不用了'
    }).then(() => {
      chatStore.addAiMessage('👨‍👩‍👧‍👦 亲子家庭路线（4小时轻松游）：南门→九龙灌浴→佛手广场→百子戏弥勒→梵宫→五印坛城。适合带孩子的家庭，互动性强！')
      scrollToBottom()
    }).catch(() => {})
  }, 500)
}

// ===== 热门问题（从Chat.vue集成） =====
function showHotQuestions() {
  const questions = [
    '灵山胜境门票多少钱？',
    '灵山大佛有多高？',
    '梵宫有什么看点？',
    '景区怎么去？',
    '有什么特色素斋推荐？'
  ]

  Dialog.alert({
    title: '热门问题',
    message: questions.map((q, i) => `${i + 1}. ${q}`).join('\n'),
    confirmButtonText: '知道了'
  })
}

// ===== 点击数字人 =====
function onTapCharacter() {
  if (!chatStore.isProcessing) {
    const greetings = ['你好呀！欢迎来到灵山胜境~', '有什么可以帮助您的吗？', '今天想去哪里玩呢？']
    const msg = greetings[Math.floor(Math.random() * greetings.length)]
    chatStore.addAiMessage(msg)
    scrollToBottom()
  }
}

// ===== 切换数字人 =====
function goDigitalHuman() {
  router.push('/digital-human')
}

// ===== 获取数字人列表 =====
async function fetchDigitalHumans() {
  try {
    const { getDigitalHumans } = await import('@/utils/api')
    const res = await getDigitalHumans()
    if (res.code === 200) dhStore.setHumans(res.data)
  } catch (e) {
    console.warn('获取数字人列表失败:', e)
  }
}

// ===== 滚动到底部 =====
function scrollToBottom() {
  nextTick(() => {
    if (bubbleRef.value) {
      bubbleRef.value.scrollTop = bubbleRef.value.scrollHeight
    }
  })
  setTimeout(() => {
    if (bubbleRef.value) {
      bubbleRef.value.scrollTop = bubbleRef.value.scrollHeight
    }
  }, 50)
}
</script>

<style scoped>
.home-page {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #e8f5e9 0%, #f5f7f0 100%);
  overflow: hidden;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  padding-top: 48px;
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
}

.dh-name {
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
}

.quick-bar {
  display: flex;
  gap: 8px;
  padding: 6px 16px;
  background: rgba(255,255,255,0.7);
  border-bottom: 1px solid rgba(91,140,90,0.08);
}

.quick-btn {
  height: 26px !important;
  font-size: 11px !important;
  padding: 0 10px !important;
}

.live2d-container {
  flex: 0 0 240px;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background: radial-gradient(ellipse at center, rgba(255,255,255,0.8) 0%, transparent 70%);
  overflow: hidden;
}

.emotion-badge {
  position: absolute;
  top: 12px;
  right: 16px;
  background: rgba(255,255,255,0.9);
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  color: #5b8c5a;
  box-shadow: var(--shadow-sm);
}

.status-tip {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,255,255,0.9);
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 12px;
  color: #5b8c5a;
}

.chat-bubbles {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 16px;
  -webkit-overflow-scrolling: touch;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #9aab9a;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  line-height: 1.8;
  text-align: center;
}

.bubble {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  width: 100%;
  animation: fadeInUp 0.3s ease;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.user-bubble {
  flex-direction: row-reverse;
  justify-content: flex-start;
}

.ai-bubble {
  flex-direction: row;
  justify-content: flex-start;
}

.bubble-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.bubble-content {
  max-width: 75%;
}

.user-bubble .bubble-text,
.user-bubble .bubble-time,
.user-bubble .bubble-meta {
  text-align: right;
}

.user-bubble .bubble-content {
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
  border-radius: 16px 4px 16px 16px;
  padding: 10px 14px;
}

.ai-bubble .bubble-content {
  background: rgba(255,255,255,0.95);
  color: #2e3d2e;
  border-radius: 4px 16px 16px 16px;
  padding: 10px 14px;
  box-shadow: var(--shadow-sm);
}

.bubble-text {
  font-size: 14px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-text.thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #9aab9a;
  font-size: 13px;
}

.bubble-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: 11px;
  color: #9aab9a;
}

.user-bubble .bubble-meta {
  justify-content: flex-end;
}

.ai-bubble .bubble-meta {
  justify-content: flex-start;
}

.bubble-emotion {
  font-size: 11px;
}

.input-bar {
  padding: 8px 16px;
  padding-bottom: calc(8px + env(safe-area-inset-bottom));
  background: rgba(255,255,255,0.95);
  border-top: 1px solid rgba(91,140,90,0.1);
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f0f4eb;
  border-radius: 24px;
  padding: 6px 12px;
}

.text-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 15px;
  color: #2e3d2e;
  padding: 6px 0;
  min-height: 24px;
}

.text-input::placeholder {
  color: #9aab9a;
}

.hold-to-speak {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
  border-radius: 20px;
  font-size: 15px;
  font-weight: 500;
  padding: 8px 0;
  user-select: none;
  -webkit-user-select: none;
  cursor: pointer;
  transition: transform 0.1s;
}
.hold-to-speak.recording {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  transform: scale(0.97);
}

.send-btn {
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-sheet {
  padding: 20px;
  text-align: center;
}

.upload-tip {
  color: #9aab9a;
  font-size: 12px;
  margin-top: 12px;
}
</style>