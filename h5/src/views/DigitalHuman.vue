<template>
  <div class="dh-select-page">
    <van-nav-bar title="切换数字人导游" left-arrow @click-left="$router.back()" />

    <div class="dh-list">
      <div
        v-for="dh in dhStore.humans"
        :key="dh.id"
        :class="['dh-item', { active: dh.id === dhStore.currentId }]"
        @click="switchDh(dh)"
      >
        <div class="dh-model">
          <div class="dh-preview">
            {{ dh.id === 1 ? '🪷' : dh.id === 2 ? '🌸' : '📿' }}
          </div>
        </div>
        <div class="dh-info">
          <div class="dh-name">{{ dh.name }}</div>
          <div class="dh-params">
            <span>语速: {{ dh.default_speed }}</span>
            <span>语调: {{ dh.default_pitch }}</span>
          </div>
          <div class="dh-voice">音色: {{ voiceNameMap[dh.default_voice] || dh.default_voice }}</div>
        </div>
        <div class="dh-check">
          <van-icon v-if="dh.id === dhStore.currentId" name="success" color="#5b8c5a" size="20" />
        </div>
      </div>
    </div>

    <div class="dh-tip">
      <p>💡 不同的数字人导游拥有独特的语速、语调和音色</p>
      <p>灵韵 —— 温和亲切，适合日常讲解</p>
      <p>慧心 —— 轻柔舒缓，适合禅意体验</p>
      <p>明远 —— 沉稳大气，适合文化讲解</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { showSuccessToast } from 'vant'
import { useDigitalHumanStore } from '@/store'
import { getDigitalHumans } from '@/utils/api'

const router = useRouter()
const dhStore = useDigitalHumanStore()

const voiceNameMap = {
  'zh-CN-XiaoxiaoNeural': '晓晓（女声·推荐）',
  'zh-CN-YunxiNeural': '云希（男声）',
  'zh-CN-XiaoyiNeural': '晓伊（女声·活泼）',
  'zh-CN-XiaohanNeural': '晓涵（女声·温柔）'
}

onMounted(async () => {
  try {
    const res = await getDigitalHumans()
    if (res.code === 200 && res.data.length > 0) {
      dhStore.setHumans(res.data)
    }
  } catch (e) {
    dhStore.setHumans([
      { id: 1, name: '灵韵（默认导游）', default_speed: 1.0, default_pitch: 1.0, default_voice: 'zh-CN-XiaoxiaoNeural' },
      { id: 2, name: '慧心（禅意导游）', default_speed: 0.9, default_pitch: 1.1, default_voice: 'zh-CN-XiaoyiNeural' },
      { id: 3, name: '明远（文化导游）', default_speed: 1.1, default_pitch: 0.9, default_voice: 'zh-CN-YunxiNeural' }
    ])
  }
})

function switchDh(dh) {
  if (dh.id !== dhStore.currentId) {
    dhStore.switchDigitalHuman(dh)
    showSuccessToast(`已切换至 ${dh.name}`)
    setTimeout(() => router.back(), 500)
  }
}
</script>

<style scoped>
.dh-select-page {
  min-height: 100vh;
  background: #f5f7f0;
}
.dh-list { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.dh-item {
  display: flex; align-items: center; gap: 16px; background: #fff;
  border-radius: 16px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  border: 2px solid transparent; transition: all 0.3s ease; cursor: pointer;
}
.dh-item.active {
  border-color: #5b8c5a; box-shadow: 0 4px 16px rgba(91, 140, 90, 0.15);
}
.dh-preview {
  width: 72px; height: 72px; border-radius: 50%;
  background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
  display: flex; align-items: center; justify-content: center; font-size: 36px;
}
.dh-info { flex: 1; }
.dh-name { font-size: 16px; font-weight: 600; color: #2e3d2e; margin-bottom: 6px; }
.dh-params { display: flex; gap: 16px; font-size: 12px; color: #9aab9a; margin-bottom: 4px; }
.dh-voice { font-size: 12px; color: #6b7c6b; }
.dh-check { width: 24px; display: flex; justify-content: center; }
.dh-tip { margin: 24px 16px; padding: 16px; background: rgba(255,255,255,0.8); border-radius: 12px; font-size: 13px; color: #6b7c6b; line-height: 2; }
</style>