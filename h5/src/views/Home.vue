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

    <!-- ========== 模式 A：全屏数字人 ========== -->
    <template v-if="viewMode === 'full'">
      <div class="content-area full-mode">
        <!-- 数字人全身 -->
        <div class="live2d-container live2d-full" @click="onTapCharacter">
          <Live2DViewer
            ref="live2dRef"
            :emotion="chatStore.currentEmotion"
            :is-speaking="chatStore.isSpeaking"
            :dh-id="dhStore.currentId"
          />
          <div class="emotion-badge" v-if="chatStore.currentEmotion !== '平静'">
            {{ chatStore.currentEmotion === '热情' ? '🔥' : '😊' }}
            {{ chatStore.currentEmotion }}
          </div>
          <!-- 通话状态指示 -->
          <div class="call-indicator" v-if="callActive">
            <span class="call-dot"></span> 通话中
          </div>
        </div>
      </div>

      <!-- 底部通话操作栏 -->
      <div class="action-bar">
        <div class="action-btn mute" :class="{ active: audioMuted }" @click="toggleMute">
          <van-icon :name="audioMuted ? 'volume-o' : 'volume-o'" size="22" />
          <span>{{ audioMuted ? '已静音' : '静音' }}</span>
        </div>
        <div class="action-btn call" :class="{ active: callActive }" @click="toggleCall">
          <van-icon name="phone-o" size="32" />
          <span>{{ callActive ? '挂断' : '通话' }}</span>
        </div>
        <div class="action-btn text" @click="openTextChat">
          <van-icon name="chat-o" size="22" />
          <span>文字</span>
        </div>
      </div>
    </template>

    <!-- ========== 模式 B：对话模式 ========== -->
    <template v-if="viewMode === 'chat'">
      <div class="content-area chat-mode">
        <!-- 数字人区（上方 40%，点击切回模式A） -->
        <div class="live2d-container live2d-compact" @click="closeTextChat">
          <Live2DViewer
            ref="live2dRef"
            :emotion="chatStore.currentEmotion"
            :is-speaking="chatStore.isSpeaking"
            :dh-id="dhStore.currentId"
          />
          <div class="emotion-badge" v-if="chatStore.currentEmotion !== '平静'">
            {{ chatStore.currentEmotion === '热情' ? '🔥' : '😊' }}
            {{ chatStore.currentEmotion }}
          </div>
        </div>

        <!-- 对话区（下方 60%） -->
        <div class="chat-bubbles" ref="bubbleRef">
          <div v-if="messages.length === 0" class="chat-empty">
            <div class="empty-icon">💬</div>
            <p class="empty-text">输入你的问题，AI导游为你解答</p>
          </div>

          <div
            v-for="(msg, i) in messages"
            :key="`${msg.id}-${i}`"
            :class="['bubble', msg.role === 'user' ? 'user-bubble' : 'ai-bubble']"
          >
            <div class="bubble-avatar" v-if="msg.role === 'user'">👤</div>
            <div class="bubble-content">
              <!-- AI 思考中 / 已停止 -->
              <div class="bubble-text thinking" v-if="msg.role === 'ai' && !msg.text">
                <template v-if="i === messages.length - 1 && chatStore.isProcessing">
                  <span class="dot-pulse"></span>
                </template>
                <template v-else>
                  <span class="stopped-text">已停止思考</span>
                </template>
              </div>
              <div class="bubble-text" v-else>{{ msg.text }}</div>
              <div class="bubble-meta">
                <span class="bubble-time">{{ msg.time }}</span>
                <span class="bubble-emotion" v-if="msg.emotion && msg.emotion !== '平静'">
                  {{ msg.emotion === '热情' ? '🔥' : '😊' }} {{ msg.emotion }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部输入栏 -->
      <div class="input-bar">
        <div class="input-wrapper">
          <!-- 图片上传（始终显示） -->
          <van-icon name="photo-o" size="22" color="#5b8c5a" @click="showImageUpload = true" />

          <!-- 文字输入模式 -->
          <template v-if="!voiceMode">
            <input
              v-model="inputText"
              class="text-input"
              placeholder="输入问题..."
              @keydown.enter="sendText"
            />
            <!-- 打断按钮（覆盖语音入口） / 语音入口 -->
            <van-icon
              v-if="chatStore.isProcessing || chatStore.isSpeaking"
              name="stop-circle-o"
              color="#e74c3c"
              size="22"
              @click="stopReply"
            />
            <van-icon
              v-else
              name="volume-o"
              color="#5b8c5a"
              size="22"
              @click="enterVoiceMode"
            />
            <!-- 发送按钮（思考中隐藏，防止重复发送） -->
            <van-icon
              v-if="inputText.trim() && !chatStore.isProcessing && !chatStore.isSpeaking"
              name="arrow-up"
              size="20"
              color="#fff"
              class="send-btn"
              @click="sendText"
            />
          </template>

          <!-- 语音模式 -->
          <template v-else>
            <div
              :class="['hold-to-speak', { recording: isRecording }]"
              @mousedown.prevent="startHoldSpeak"
              @mouseup.prevent="stopHoldSpeak"
              @mouseleave.prevent="stopHoldSpeak"
              @touchstart.prevent="startHoldSpeak"
              @touchend.prevent="stopHoldSpeak"
            >
              {{ isRecording ? '🎙️ 正在聆听...' : '🎙️ 请按住说话' }}
            </div>
            <!-- 打断按钮（覆盖编辑入口，录音时都不显示） -->
            <van-icon
              v-if="chatStore.isProcessing || chatStore.isSpeaking"
              name="stop-circle-o"
              color="#e74c3c"
              size="22"
              @click="stopReply"
            />
            <van-icon
              v-else-if="!isRecording"
              name="chat-o"
              color="#5b8c5a"
              size="22"
              @click="exitVoiceMode"
            />
          </template>
        </div>
      </div>
    </template>

    <!-- 模式A文字输入弹窗 -->
    <van-popup v-model:show="showTextPopup" position="bottom" round :style="{ minHeight: '40%' }">
      <div class="text-popup">
        <div class="popup-header">
          <span>文字提问</span>
          <van-icon name="cross" size="18" @click="showTextPopup = false" />
        </div>
        <div class="popup-body">
          <textarea
            ref="popupTextRef"
            v-model="popupText"
            class="popup-textarea"
            placeholder="输入你的问题..."
            rows="4"
          ></textarea>
          <div class="popup-actions">
            <van-icon name="photo-o" size="22" color="#5b8c5a" @click="showImageUpload = true" />
            <van-button round type="primary" class="green-btn" @click="sendPopupText" :disabled="!popupText.trim()">
              发送
            </van-button>
          </div>
        </div>
      </div>
    </van-popup>

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

// ---- 双模式状态 ----
const viewMode = ref('full')        // 'full' | 'chat'
const callActive = ref(false)       // 持续收音开关
const audioMuted = ref(false)       // 静音数字人播报
const showTextPopup = ref(false)    // 模式A文字弹窗
const popupText = ref('')
const popupTextRef = ref(null)

// ---- 原有状态 ----
const inputText = ref('')
const showImageUpload = ref(false)
const isRecording = ref(false)
const voiceMode = ref(false)
const bubbleRef = ref(null)
const live2dRef = ref(null)
let currentAudioSource = null
let isDiscarded = false
let doneTimeoutId = null
let sessionIdTimer = null

// --- 响应式消息列表 ---
const messages = computed(() => chatStore.messages)
const hasLastAiMsg = computed(() => {
  const msgs = chatStore.messages
  return msgs.length > 0 && msgs[msgs.length - 1].role === 'ai'
})

// 思考气泡：isProcessing 且最后一条 AI 消息还没有文字内容
const showThinkingBubble = computed(() => {
  if (!chatStore.isProcessing) return false
  const msgs = chatStore.messages
  if (msgs.length === 0) return true
  const last = msgs[msgs.length - 1]
  return last.role === 'ai' && !last.text
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
      // 如果静音，不连接扬声器，但仍走完播放流程
      if (!audioMuted.value) {
        source.connect(ctx.destination)
      }
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

  ws.on('user_text', (text) => {
    if (text) {
      chatStore.addUserMessage(text, 'voice')
      scrollToBottom()
    }
  })

  ws.on('text_start', () => {
    isDiscarded = false
    if (doneTimeoutId) {
      clearTimeout(doneTimeoutId)
      doneTimeoutId = null
    }
    // 如果前端已经预创建了空 AI 消息（sendText 立即展示），不再重复创建
    const msgs = chatStore.messages
    const lastEmpty = msgs.length > 0 && msgs[msgs.length - 1].role === 'ai' && !msgs[msgs.length - 1].text
    if (!lastEmpty) {
      chatStore.setProcessing(true)
      chatStore.setEmotion('平静')
      audioQueue.value = []
      isPlayingAudio = false
      chatStore.addAiMessage('')
    }
  })

  ws.on('text_chunk', ({ text }) => {
    if (isDiscarded) return
    chatStore.appendAiText(text)
    scrollToBottom()
  })

  ws.on('text_end', () => {
    if (isDiscarded) return
    chatStore.setProcessing(false)
  })

  ws.on('audio_chunk', ({ audio, lt_synced }) => {
    if (isDiscarded) return
    if (lt_synced) {
      chatStore.isSpeaking = true
      return
    }
    if (audio) {
      audioQueue.value.push(audio)
      if (!isPlayingAudio) playNextAudio()
    }
  })

  ws.on('emotion', (emotion) => {
    if (isDiscarded) return
    chatStore.setEmotion(emotion)
  })

  // ---- 状态消息（静默，思考态由气泡动画展示） ----
  ws.on('status', () => {})

  ws.on('error', (error) => {
    showFailToast(error)
    chatStore.setProcessing(false)
  })

  ws.on('done', () => {
    if (isDiscarded) return
    chatStore.setProcessing(false)
    if (audioQueue.value.length === 0) {
      if (doneTimeoutId) clearTimeout(doneTimeoutId)
      doneTimeoutId = setTimeout(() => {
        chatStore.isSpeaking = false
        doneTimeoutId = null
      }, 1000)
    }
  })
}

// ===== 模式切换 =====
function openTextChat() {
  viewMode.value = 'chat'
  showTextPopup.value = false
  popupText.value = ''
  nextTick(() => scrollToBottom())
}

function closeTextChat() {
  viewMode.value = 'full'
}

// ===== 通话控制按钮 =====
function toggleCall() {
  callActive.value = !callActive.value
  if (callActive.value) {
    // TODO: 实现持续收音（Web Speech API / MediaRecorder 循环）
  } else {
    closeToast()
  }
}

function toggleMute() {
  audioMuted.value = !audioMuted.value
  if (live2dRef.value) {
    if (audioMuted.value) {
      live2dRef.value.muteVideo?.()
    } else {
      live2dRef.value.unmuteVideo?.()
    }
  }
}

// ===== 发送文本 =====
function sendText() {
  const text = inputText.value.trim()
  if (!text) return

  // 防止重复发送
  if (chatStore.isProcessing || chatStore.isSpeaking) return

  if (viewMode.value === 'full') openTextChat()

  inputText.value = ''

  // 立即展示用户消息 + AI思考气泡
  chatStore.addUserMessage(text, 'text')
  chatStore.setProcessing(true)
  chatStore.setEmotion('平静')
  isDiscarded = false
  audioQueue.value = []
  isPlayingAudio = false
  chatStore.addAiMessage('')  // 空消息 → 三点动画
  scrollToBottom()

  const ws = getWsClient()
  if (ws && ws.isConnected.value) {
    ws.sendText(text)
  } else {
    fallbackReply()
  }
}

// 模式A弹窗发送
function sendPopupText() {
  const text = popupText.value.trim()
  if (!text) return
  if (chatStore.isProcessing || chatStore.isSpeaking) return

  openTextChat()
  showTextPopup.value = false

  chatStore.addUserMessage(text, 'text')
  chatStore.setProcessing(true)
  chatStore.setEmotion('平静')
  isDiscarded = false
  audioQueue.value = []
  isPlayingAudio = false
  chatStore.addAiMessage('')
  scrollToBottom()

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

// ===== 语音输入 =====
let mediaRecorder = null
let audioChunks = []
let holdStartTime = 0
let silenceDetector = null     // { audioContext, analyser, dataArray, maxVolume, intervalId }

function enterVoiceMode() {
  voiceMode.value = true
  inputText.value = ''  // 清空文字，避免发送按钮遮挡键盘图标
}

function exitVoiceMode() {
  voiceMode.value = false
  if (isRecording.value) stopHoldSpeak()
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
      // ---- 静音检测：AnalyserNode + RMS 标准音量算法 ----
      const detector = { audioCtx: null, intervalId: null, maxRms: 0 }
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)()
        const source = audioCtx.createMediaStreamSource(stream)
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 512
        source.connect(analyser)
        const timeData = new Uint8Array(analyser.fftSize)

        const intervalId = setInterval(() => {
          analyser.getByteTimeDomainData(timeData)
          // 标准 RMS 计算：归一化到 -1..1，平方平均后开方
          let sumSquares = 0
          for (let i = 0; i < timeData.length; i++) {
            const normalized = (timeData[i] - 128) / 128
            sumSquares += normalized * normalized
          }
          const rms = Math.sqrt(sumSquares / timeData.length)
          if (rms > detector.maxRms) detector.maxRms = rms
        }, 100)

        detector.audioCtx = audioCtx
        detector.intervalId = intervalId
        silenceDetector = detector
      } catch (e) {
        console.warn('[Audio] 静音检测初始化失败:', e)
        silenceDetector = null
      }

      // ---- 录音 ----
      mediaRecorder = new MediaRecorder(stream)
      mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data)

      mediaRecorder.onstop = () => {
        // 清理静音检测
        const det = silenceDetector
        if (det) {
          clearInterval(det.intervalId)
          det.audioCtx.close()
        }

        const duration = (Date.now() - holdStartTime) / 1000
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })

        // 标准静音判断：RMS < 0.015 视为静音（典型语音 RMS 0.02~0.2）
        const hasVolume = det
          ? det.maxRms > 0.015
          : audioBlob.size > 8000

        if (duration < 0.4 || !hasVolume) {
          showFailToast('未检测到声音，请重试')
          isRecording.value = false
          silenceDetector = null
          stream.getTracks().forEach(track => track.stop())
          return
        }

        silenceDetector = null

        const reader = new FileReader()
        reader.onload = () => {
          const base64 = reader.result.split(',')[1]
          const ws = getWsClient()
          if (ws && ws.isConnected.value) ws.sendAudio(base64)
        }
        reader.readAsDataURL(audioBlob)
        stream.getTracks().forEach(track => track.stop())
        isRecording.value = false
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

// ===== 打断/关闭 =====
function stopReply() {
  const ws = getWsClient()
  if (ws && ws.isConnected.value) ws.sendInterrupt()

  isDiscarded = true
  if (doneTimeoutId) {
    clearTimeout(doneTimeoutId)
    doneTimeoutId = null
  }

  audioQueue.value = []
  isPlayingAudio = false
  chatStore.setProcessing(false)
  chatStore.isSpeaking = false

  live2dRef.value?.muteVideo?.()
  setTimeout(() => {
    if (!audioMuted.value) {
      live2dRef.value?.unmuteVideo?.()
    }
  }, 2000)

  if (currentAudioSource) {
    try { currentAudioSource.stop() } catch (_) {}
    currentAudioSource = null
  }

  closeToast()
}

// ===== 点击数字人 → 打断 =====
function onTapCharacter() {
  if (chatStore.isProcessing || chatStore.isSpeaking) {
    stopReply()
  }
}

// ===== 图片上传 =====
function onImageRead(file) {
  showImageUpload.value = false
  if (!file?.file) return

  const reader = new FileReader()
  reader.onload = (e) => {
    const base64 = e.target.result.split(',')[1]
    const text = inputText.value.trim() || popupText.value.trim() || '请分析这张图片'

    if (viewMode.value === 'full') openTextChat()

    chatStore.addUserMessage(text, 'image')
    inputText.value = ''
    popupText.value = ''

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

// ===== 路线推荐 =====
function showRoutes() {
  Dialog.confirm({
    title: '选择游览路线',
    message: '请选择您感兴趣的路线类型：',
    confirmButtonText: '自然风光',
    cancelButtonText: '文化朝圣',
    showCancelButton: true
  }).then(() => {
    if (viewMode.value === 'full') openTextChat()
    chatStore.addAiMessage('🌄 自然风光路线（5小时全景游）：南门→佛足坛→九龙灌浴→菩提大道→灵山大佛→曼飞龙塔→灵山精舍→梵宫广场。漫步菩提大道欣赏太湖风光，登顶大佛俯瞰全景，感受人与自然和谐统一。')
    scrollToBottom()
  }).catch(() => {
    if (viewMode.value === 'full') openTextChat()
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

// ===== 热门问题 =====
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

/* ===== 内容区 ===== */
.content-area {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #e8f5e9 0%, #dce8dc 40%, #cfdbcf 100%);
}

/* 模式A：全屏数字人 */
.full-mode {
  position: relative;
}

.live2d-full {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background: transparent;
}

/* 模式B：上下分布 */
.chat-mode {
  display: flex;
  flex-direction: column;
}

.live2d-compact {
  flex: 0 0 40%;
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  background: transparent;
  border-bottom: 1px solid rgba(91,140,90,0.1);
}

/* 通话状态指示 */
.call-indicator {
  position: absolute;
  top: 10px;
  left: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  background: rgba(76, 175, 80, 0.15);
  color: #388e3c;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  z-index: 5;
}
.call-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4caf50;
  animation: pulse-dot 1.2s ease-in-out infinite;
}

/* 情绪+状态 */
.emotion-badge {
  position: absolute;
  top: 10px;
  right: 12px;
  background: rgba(0,0,0,0.45);
  color: #fff;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  z-index: 5;
}

.status-tip {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(0,0,0,0.45);
  color: #fff;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 11px;
  white-space: nowrap;
  z-index: 5;
}

/* ===== 通话操作栏（模式A） ===== */
.action-bar {
  display: flex;
  justify-content: space-evenly;
  align-items: center;
  padding: 14px 24px;
  padding-bottom: calc(14px + env(safe-area-inset-bottom));
  background: rgba(255,255,255,0.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(91,140,90,0.08);
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
  -webkit-user-select: none;
}
.action-btn:active {
  transform: scale(0.93);
}

/* 左右小按钮 */
.action-btn.mute,
.action-btn.text {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #f0f4eb;
  color: #5b8c5a;
  justify-content: center;
  font-size: 11px;
}
.action-btn.mute.active {
  background: #fff0e6;
  color: #e67e22;
}
.action-btn.mute.active :deep(.van-icon) {
  color: #e67e22;
}

/* 中间通话大按钮 */
.action-btn.call {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
  justify-content: center;
  font-size: 12px;
  box-shadow: 0 4px 16px rgba(91,140,90,0.35);
}
.action-btn.call :deep(.van-icon) {
  line-height: 1;
}
.action-btn.call.active {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
  box-shadow: 0 4px 16px rgba(231,76,60,0.35);
  animation: call-pulse 1.8s ease-in-out infinite;
}
@keyframes call-pulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(231,76,60,0.35); }
  50% { box-shadow: 0 4px 28px rgba(231,76,60,0.55); }
}

/* ===== 对话气泡（模式B） ===== */
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
  font-size: 40px;
  margin-bottom: 10px;
  opacity: 0.4;
}

.empty-text {
  font-size: 13px;
  line-height: 1.8;
  text-align: center;
}

.bubble {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
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
  max-width: 80%;
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
  justify-content: center;
  padding: 4px 0;
  min-height: 24px;
}

.stopped-text {
  color: #9aab9a;
  font-size: 13px;
}

/* 循环三点动画 */
.dot-pulse {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #9aab9a;
  animation: dot-typing 1.4s infinite both;
  position: relative;
  margin-left: 12px;
}
.dot-pulse::before,
.dot-pulse::after {
  content: '';
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #9aab9a;
  position: absolute;
  top: 0;
}
.dot-pulse::before {
  left: -16px;
  animation: dot-typing 1.4s 0.2s infinite both;
}
.dot-pulse::after {
  left: 16px;
  animation: dot-typing 1.4s 0.4s infinite both;
}

@keyframes dot-typing {
  0%, 60%, 100% { opacity: 0.2; transform: scale(0.8); }
  30% { opacity: 1; transform: scale(1); }
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

.user-bubble .bubble-text,
.user-bubble .bubble-time {
  text-align: right;
}

.ai-bubble .bubble-meta {
  justify-content: flex-start;
}

.bubble-emotion {
  font-size: 11px;
}

/* ===== 底部输入栏（模式B） ===== */
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
  flex-shrink: 0;
}

/* ===== 文字弹窗（模式A） ===== */
.text-popup {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  font-size: 16px;
  font-weight: 600;
  color: #2e3d2e;
  border-bottom: 1px solid #eee;
}

.popup-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  gap: 16px;
}

.popup-textarea {
  flex: 1;
  border: 1px solid #e0e8dc;
  border-radius: 12px;
  padding: 12px;
  font-size: 15px;
  color: #2e3d2e;
  outline: none;
  resize: none;
  font-family: inherit;
  background: #f8faf5;
}

.popup-textarea::placeholder {
  color: #9aab9a;
}

.popup-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.green-btn {
  background: linear-gradient(135deg, #5b8c5a, #7cb342) !important;
  color: #fff !important;
  border: none !important;
}

/* ===== 图片上传弹窗 ===== */
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
