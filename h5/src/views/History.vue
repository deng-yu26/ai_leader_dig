<template>
  <div class="history-page">
    <van-nav-bar title="对话历史" left-arrow @click-left="$router.back()" />

    <van-pull-refresh v-model="refreshing" @refresh="onRefresh">
      <van-list
        v-model:loading="loading"
        :finished="finished"
        finished-text="没有更多了"
        @load="loadMore"
      >
        <div v-for="log in logs" :key="log.id" class="log-card" @click="viewDetail(log)">
          <div class="log-header">
            <span class="log-emotion">{{ emojiMap[log.emotion_label] || '💬' }}</span>
            <span class="log-time">{{ log.question_time }}</span>
          </div>
          <div class="log-question">Q: {{ truncateText(log.question_text, 50) }}</div>
          <div class="log-answer">A: {{ truncateText(log.answer_text, 80) }}</div>
        </div>

        <van-empty v-if="!loading && logs.length === 0" description="暂无对话记录" />
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Dialog } from 'vant'
import { getChatHistory } from '@/utils/api'

const router = useRouter()
const logs = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)

const emojiMap = {
  '平静': '💬',
  '微笑': '😊',
  '热情': '🔥'
}

function truncateText(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}

async function loadMore() {
  loading.value = true
  try {
    const res = await getChatHistory({ page: page.value, per_page: 20 })
    if (res.code === 200) {
      const items = res.data.items || []
      logs.value.push(...items)
      finished.value = items.length < 20
      page.value++
    } else {
      finished.value = true
    }
  } catch (e) {
    finished.value = true
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

function onRefresh() {
  page.value = 1
  logs.value = []
  finished.value = false
  loadMore()
}

function viewDetail(log) {
  Dialog.alert({
    title: '对话详情',
    message: `🗣 问题：${log.question_text}\n\n🤖 回答：${log.answer_text}\n\n🕐 时间：${log.question_time}\n😊 情绪：${log.emotion_label}`,
    confirmButtonText: '关闭'
  })
}
</script>

<style scoped>
.history-page {
  min-height: 100vh;
  background: #f5f7f0;
}

.log-card {
  background: #fff;
  margin: 8px 16px;
  padding: 14px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  cursor: pointer;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.log-emotion {
  font-size: 20px;
}

.log-time {
  font-size: 12px;
  color: #9aab9a;
}

.log-question {
  font-size: 14px;
  color: #2e3d2e;
  font-weight: 500;
  margin-bottom: 6px;
}

.log-answer {
  font-size: 13px;
  color: #6b7c6b;
  line-height: 1.5;
}
</style>