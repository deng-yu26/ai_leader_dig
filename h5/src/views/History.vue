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
        <div v-for="session in sessions" :key="session.session_id" class="session-card">
          <!-- 会话头部 -->
          <div class="session-header" @click="toggleSession(session.session_id)">
            <div class="session-info">
              <span class="session-emoji">{{ emojiMap[session.emotion] || '💬' }}</span>
              <div class="session-meta">
                <div class="session-title">{{ truncateText(session.title, 25) }}</div>
                <div class="session-sub">
                  {{ session.time }} · {{ session.message_count }} 轮对话
                </div>
              </div>
            </div>
            <div class="session-actions">
              <van-icon
                v-if="session.route_data"
                name="guide-o"
                size="18"
                color="#5b8c5a"
                @click.stop="openRoute(session.route_data)"
              />
              <van-icon
                :name="expandedId === session.session_id ? 'arrow-up' : 'arrow-down'"
                size="16"
                color="#999"
              />
            </div>
          </div>

          <!-- 展开的对话消息 -->
          <div class="session-messages" v-if="expandedId === session.session_id">
            <div
              v-for="msg in session.messages"
              :key="msg.id"
              class="msg-item"
            >
              <div class="msg-question">
                <span class="msg-role">🙋</span>
                <span>{{ msg.question_text }}</span>
              </div>
              <div class="msg-answer">
                <span class="msg-role">🤖</span>
                <span>{{ truncateText(msg.answer_text, 200) }}</span>
              </div>
              <div class="msg-footer">
                <span class="msg-time">{{ msg.question_time }}</span>
                <span class="msg-emotion">{{ emojiMap[msg.emotion_label] || '' }} {{ msg.emotion_label }}</span>
              </div>
            </div>
          </div>
        </div>

        <van-empty v-if="!loading && sessions.length === 0" description="暂无对话记录">
          <template #image>
            <span style="font-size:48px">💬</span>
          </template>
        </van-empty>
      </van-list>
    </van-pull-refresh>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { getChatHistory } from '@/utils/api'

const router = useRouter()
const sessions = ref([])
const loading = ref(false)
const finished = ref(false)
const refreshing = ref(false)
const page = ref(1)
const expandedId = ref(null)

const emojiMap = { '平静': '💬', '微笑': '😊', '热情': '🔥' }

function truncateText(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.substring(0, maxLen) + '...' : text
}

function toggleSession(sid) {
  expandedId.value = expandedId.value === sid ? null : sid
}

function openRoute(routeData) {
  if (!routeData?.route_data) return
  const rd = routeData.route_data
  router.push({
    path: '/route-map',
    query: {
      origin: rd.origin || '景区入口',
      destination: rd.destination || '灵山大佛',
      waypoints: (rd.waypoints || []).join(','),
      mode: rd.mode || 'walk',
      summary: rd.summary || ''
    }
  })
}

async function loadMore() {
  loading.value = true
  try {
    const res = await getChatHistory({ page: page.value, per_page: 10 })
    if (res.code === 200 && res.data?.sessions) {
      sessions.value.push(...res.data.sessions)
      finished.value = res.data.sessions.length < 10
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
  sessions.value = []
  expandedId.value = null
  finished.value = false
  loadMore()
}
</script>

<style scoped>
.history-page {
  min-height: 100vh;
  background: #f5f7f0;
}
.session-card {
  background: #fff;
  margin: 8px 16px;
  border-radius: 14px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  overflow: hidden;
}
.session-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  cursor: pointer;
}
.session-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.session-emoji { font-size: 24px; }
.session-title { font-size: 15px; font-weight: 600; color: #2e3d2e; }
.session-sub { font-size: 12px; color: #9aab9a; margin-top: 2px; }
.session-actions { display: flex; align-items: center; gap: 10px; }
.session-messages {
  border-top: 1px solid #f0f4eb;
  padding: 8px 14px 12px;
  max-height: 360px;
  overflow-y: auto;
}
.msg-item {
  padding: 8px 0;
  border-bottom: 1px solid #f5f7f0;
}
.msg-item:last-child { border-bottom: none; }
.msg-question, .msg-answer {
  display: flex; gap: 6px;
  font-size: 13px; line-height: 1.6;
  padding: 3px 0;
}
.msg-role { flex-shrink: 0; }
.msg-question { color: #5b8c5a; }
.msg-answer { color: #4b5b4b; }
.msg-footer {
  display: flex; justify-content: space-between;
  font-size: 11px; color: #b0b8b0;
  margin-top: 4px;
}
</style>
