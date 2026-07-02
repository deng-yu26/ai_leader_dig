<template>
  <div class="route-page">
    <van-nav-bar title="游览路线规划" left-arrow @click-left="$router.back()" />

    <div class="route-content">
      <!-- 路线标签切换 -->
      <van-tabs v-model:active="activeTab" color="#5b8c5a" sticky>
        <van-tab title="文化朝圣">
          <div class="route-card" v-if="routes.culture">
            <div class="route-header">
              <span class="route-icon">🙏</span>
              <div>
                <h3 class="route-title">{{ routes.culture.title }}</h3>
                <p class="route-duration">⏱ {{ routes.culture.duration }}</p>
              </div>
            </div>
            <p class="route-desc">{{ routes.culture.description }}</p>
            <div class="spot-list">
              <div v-for="(spot, i) in routes.culture.spots" :key="i" class="spot-item">
                <div class="spot-index">{{ i + 1 }}</div>
                <div>
                  <div class="spot-name">{{ spot.name }}</div>
                  <div class="spot-desc">{{ spot.description }}</div>
                </div>
              </div>
            </div>
            <div class="route-tips">
              <van-icon name="info-o" /> 💡 {{ routes.culture.tips }}
            </div>
          </div>
        </van-tab>

        <van-tab title="自然风光">
          <div class="route-card" v-if="routes.nature">
            <div class="route-header">
              <span class="route-icon">🌄</span>
              <div>
                <h3 class="route-title">{{ routes.nature.title }}</h3>
                <p class="route-duration">⏱ {{ routes.nature.duration }}</p>
              </div>
            </div>
            <p class="route-desc">{{ routes.nature.description }}</p>
            <div class="spot-list">
              <div v-for="(spot, i) in routes.nature.spots" :key="i" class="spot-item">
                <div class="spot-index">{{ i + 1 }}</div>
                <div>
                  <div class="spot-name">{{ spot.name }}</div>
                  <div class="spot-desc">{{ spot.description }}</div>
                </div>
              </div>
            </div>
            <div class="route-tips">
              💡 {{ routes.nature.tips }}
            </div>
          </div>
        </van-tab>

        <van-tab title="亲子家庭">
          <div class="route-card" v-if="routes.family">
            <div class="route-header">
              <span class="route-icon">👨‍👩‍👧‍👦</span>
              <div>
                <h3 class="route-title">{{ routes.family.title }}</h3>
                <p class="route-duration">⏱ {{ routes.family.duration }}</p>
              </div>
            </div>
            <p class="route-desc">{{ routes.family.description }}</p>
            <div class="spot-list">
              <div v-for="(spot, i) in routes.family.spots" :key="i" class="spot-item">
                <div class="spot-index">{{ i + 1 }}</div>
                <div>
                  <div class="spot-name">{{ spot.name }}</div>
                  <div class="spot-desc">{{ spot.description }}</div>
                </div>
              </div>
            </div>
            <div class="route-tips">
              💡 {{ routes.family.tips }}
            </div>
          </div>
        </van-tab>
      </van-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRoutePlan } from '@/utils/api'

const activeTab = ref(0)
const routes = ref({})

onMounted(async () => {
  try {
    const res = await getRoutePlan()
    if (res.code === 200) {
      routes.value = res.data
    }
  } catch (e) {
    // 降级数据
    routes.value = {
      culture: {
        title: '文化朝圣路线（3小时精华游）',
        duration: '约3小时',
        description: '适合时间有限但想深度体验佛教文化的游客',
        spots: [
          { name: '南门→佛足坛→九龙灌浴', description: '观看出生表演' },
          { name: '祥符禅寺→灵山大佛', description: '登顶抱佛脚' },
          { name: '梵宫→五印坛城', description: '欣赏佛教艺术' }
        ],
        tips: '建议上午9点前入园'
      },
      nature: {
        title: '自然风光路线（5小时全景游）',
        duration: '约5小时',
        description: '适合喜欢户外自然风光的游客',
        spots: [
          { name: '菩提大道', description: '欣赏太湖风光' },
          { name: '灵山大佛', description: '俯瞰全景' },
          { name: '曼飞龙塔→灵山精舍', description: '禅意园林' }
        ],
        tips: '带上相机，拍摄太湖日落'
      },
      family: {
        title: '亲子家庭路线（4小时轻松游）',
        duration: '约4小时',
        description: '适合带孩子家庭，互动性强',
        spots: [
          { name: '九龙灌浴', description: '看表演' },
          { name: '百子戏弥勒', description: '亲子互动' },
          { name: '梵宫→五印坛城', description: '文化体验' }
        ],
        tips: '参加抱佛脚亲子活动，品尝素面套餐'
      }
    }
  }
})
</script>

<style scoped>
.route-page {
  min-height: 100vh;
  background: #f5f7f0;
}

.route-content {
  padding: 0 0 24px;
}

.route-card {
  background: #fff;
  border-radius: 12px;
  margin: 12px 16px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

.route-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.route-icon { font-size: 32px; }

.route-title {
  font-size: 16px;
  font-weight: 600;
  color: #2e3d2e;
  margin-bottom: 4px;
}

.route-duration {
  font-size: 13px;
  color: #5b8c5a;
}

.route-desc {
  font-size: 13px;
  color: #6b7c6b;
  line-height: 1.5;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7f0;
  border-radius: 8px;
}

.spot-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.spot-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.spot-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
  flex-shrink: 0;
}

.spot-name {
  font-size: 14px;
  font-weight: 500;
  color: #2e3d2e;
  margin-bottom: 2px;
}

.spot-desc {
  font-size: 12px;
  color: #9aab9a;
}

.route-tips {
  font-size: 13px;
  color: #c8a45c;
  background: #fff8e1;
  padding: 10px 14px;
  border-radius: 8px;
  line-height: 1.5;
}
</style>