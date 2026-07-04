/**
 * Pinia 全局状态管理
 * 管理用户登录态、数字人选择、对话状态
 */
import { defineStore } from 'pinia'

// ===== 用户状态 =====
export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('user_token') || '',
    userInfo: JSON.parse(localStorage.getItem('user_info') || 'null'),
    isLoggedIn: !!localStorage.getItem('user_token')
  }),

  actions: {
    // 登录成功设置用户信息
    setUserInfo(info) {
      this.userInfo = info
      this.token = info.id?.toString() || ''
      this.isLoggedIn = true
      localStorage.setItem('user_token', this.token)
      localStorage.setItem('user_info', JSON.stringify(info))
    },

    // 退出登录
    logout() {
      this.token = ''
      this.userInfo = null
      this.isLoggedIn = false
      localStorage.removeItem('user_token')
      localStorage.removeItem('user_info')
    }
  }
})

// ===== 数字人状态 =====
export const useDigitalHumanStore = defineStore('digitalHuman', {
  state: () => ({
    currentId: parseInt(localStorage.getItem('dh_id') || '1'),
    currentName: localStorage.getItem('dh_name') || '灵韵（默认导游）',
    humans: [],
    voiceList: [
      'zh-CN-XiaoxiaoNeural',
      'zh-CN-YunxiNeural',
      'zh-CN-XiaoyiNeural',
      'zh-CN-XiaohanNeural'
    ]
  }),

  actions: {
    // 设置数字人列表
    setHumans(list) {
      this.humans = list
    },

    // 切换当前数字人
    switchDigitalHuman(dh) {
      this.currentId = dh.id
      this.currentName = dh.name
      localStorage.setItem('dh_id', dh.id.toString())
      localStorage.setItem('dh_name', dh.name)
    },

    // 获取当前数字人完整信息
    getCurrentHuman() {
      return this.humans.find(h => h.id === this.currentId) || null
    }
  }
})

// ===== 对话状态 =====
export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],       // 对话消息列表
    isProcessing: false, // AI是否正在回复
    currentEmotion: '平静', // 当前情绪标签
    isSpeaking: false,   // 是否正在语音播报
    currentDhId: parseInt(localStorage.getItem('dh_id') || '1'),
    rtcState: 'disconnected'  // LiveTalking WebRTC 连接状态
  }),

  actions: {
    // 添加用户消息
    addUserMessage(text, type = 'text', imageUrl = null) {
      this.messages.push({
        id: Date.now(),
        role: 'user',
        type,
        text,
        imageUrl,
        time: new Date().toLocaleTimeString()
      })
    },

    // 添加AI消息
    addAiMessage(text) {
      this.messages.push({
        id: Date.now(),
        role: 'ai',
        text,
        time: new Date().toLocaleTimeString(),
        emotion: this.currentEmotion
      })
    },

    // 更新最后一条AI消息（流式追加）
    appendAiText(text) {
      const lastMsg = this.messages[this.messages.length - 1]
      if (lastMsg && lastMsg.role === 'ai') {
        lastMsg.text += text
      } else {
        this.addAiMessage(text)
      }
    },

    // 设置处理状态
    setProcessing(val) {
      this.isProcessing = val
    },

    // 设置情绪
    setEmotion(emotion) {
      this.currentEmotion = emotion
    },

    // 清空对话
    clearMessages() {
      this.messages = []
    },

    // 设置 LiveTalking RTC 连接状态
    setRtcState(state) {
      this.rtcState = state
    }
  }
})