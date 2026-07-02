<template>
  <div class="dashboard-page">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="4" v-for="stat in stats" :key="stat.label">
        <div class="stat-card" :style="{ background: stat.bg }">
          <div class="label">{{ stat.label }}</div>
          <div class="value">{{ stat.value }}</div>
          <div class="icon">{{ stat.icon }}</div>
        </div>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="16" class="chart-row">
      <!-- 每日对话趋势 -->
      <el-col :span="12">
        <el-card>
          <template #header>📊 每日对话趋势（近7天）</template>
          <div ref="dailyChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <!-- 热门问题TOP10 -->
      <el-col :span="12">
        <el-card>
          <template #header>🔥 热门问题TOP10</template>
          <div ref="hotChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="chart-row">
      <!-- 情绪分布 -->
      <el-col :span="12">
        <el-card>
          <template #header>😊 游客情绪分布</template>
          <div ref="emotionChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
      <!-- 游览偏好 -->
      <el-col :span="12">
        <el-card>
          <template #header>🎯 游览偏好分析</template>
          <div ref="preferenceChartRef" style="height: 300px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats } from '@/utils/api'

const dailyChartRef = ref(null)
const hotChartRef = ref(null)
const emotionChartRef = ref(null)
const preferenceChartRef = ref(null)

const stats = ref([
  { label: '总对话数', value: '0', icon: '💬', bg: 'linear-gradient(135deg, #1a3a5c, #2c5f8a)' },
  { label: '总用户数', value: '0', icon: '👤', bg: 'linear-gradient(135deg, #2c5f8a, #409eff)' },
  { label: '今日对话', value: '0', icon: '📝', bg: 'linear-gradient(135deg, #409eff, #79bbff)' },
  { label: '知识库条目', value: '0', icon: '📚', bg: 'linear-gradient(135deg, #67c23a, #95d475)' },
  { label: '数字人数量', value: '0', icon: '🪷', bg: 'linear-gradient(135deg, #e6a23c, #f3d19e)' }
])

let charts = []

onMounted(async () => {
  await loadData()
  nextTick(() => {
    initCharts()
  })
})

onUnmounted(() => {
  charts.forEach(c => c.dispose())
})

async function loadData() {
  try {
    const res = await getDashboardStats()
    if (res.code === 200) {
      const data = res.data
      stats.value = [
        { label: '总对话数', value: data.total_chats || '0', icon: '💬', bg: 'linear-gradient(135deg, #1a3a5c, #2c5f8a)' },
        { label: '总用户数', value: data.total_users || '0', icon: '👤', bg: 'linear-gradient(135deg, #2c5f8a, #409eff)' },
        { label: '今日对话', value: data.today_chats || '0', icon: '📝', bg: 'linear-gradient(135deg, #409eff, #79bbff)' },
        { label: '知识库条目', value: data.total_knowledge || '0', icon: '📚', bg: 'linear-gradient(135deg, #67c23a, #95d475)' },
        { label: '数字人数量', value: data.total_digital_humans || '0', icon: '🪷', bg: 'linear-gradient(135deg, #e6a23c, #f3d19e)' }
      ]
    }
  } catch (e) {
    console.warn('数据加载失败，使用默认数据')
  }
}

function initCharts() {
  // 每日对话趋势
  const dailyChart = echarts.init(dailyChartRef.value)
  dailyChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'], axisLabel: { color: '#909399' } },
    yAxis: { type: 'value', axisLabel: { color: '#909399' } },
    series: [{
      data: [120, 200, 150, 80, 70, 110, 130],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#409eff', width: 3 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.4)' },
          { offset: 1, color: 'rgba(64,158,255,0.05)' }
        ])
      }
    }]
  })
  charts.push(dailyChart)

  // 热门问题
  const hotChart = echarts.init(hotChartRef.value)
  hotChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', axisLabel: { color: '#909399' } },
    yAxis: {
      type: 'category',
      data: ['门票价格', '开放时间', '游览路线', '交通方式', '灵山大佛'],
      axisLabel: { color: '#606266' }
    },
    series: [{
      data: [85, 72, 68, 55, 50],
      type: 'bar',
      barWidth: 20,
      itemStyle: {
        borderRadius: [0, 10, 10, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#409eff' },
          { offset: 1, color: '#79bbff' }
        ])
      }
    }]
  })
  charts.push(hotChart)

  // 情绪分布
  const emotionChart = echarts.init(emotionChartRef.value)
  emotionChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: false,
      label: { show: true, formatter: '{b}: {c}' },
      data: [
        { value: 45, name: '平静', itemStyle: { color: '#909399' } },
        { value: 35, name: '微笑', itemStyle: { color: '#67c23a' } },
        { value: 20, name: '热情', itemStyle: { color: '#e6a23c' } }
      ],
      emphasis: {
        label: { show: true, fontSize: 16, fontWeight: 'bold' }
      }
    }]
  })
  charts.push(emotionChart)

  // 游览偏好
  const preferenceChart = echarts.init(preferenceChartRef.value)
  preferenceChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: '0%' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      label: { show: true, formatter: '{b}: {d}%' },
      data: [
        { value: 40, name: '文化朝圣', itemStyle: { color: '#1a3a5c' } },
        { value: 35, name: '自然风光', itemStyle: { color: '#67c23a' } },
        { value: 25, name: '亲子家庭', itemStyle: { color: '#e6a23c' } }
      ]
    }]
  })
  charts.push(preferenceChart)
}
</script>

<style scoped>
.dashboard-page {
  padding: 0;
}

.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  position: relative;
  padding: 20px;
  border-radius: 8px;
  color: #fff;
  text-align: center;
  overflow: hidden;
}

.stat-card .label {
  font-size: 13px;
  opacity: 0.85;
  margin-bottom: 8px;
}

.stat-card .value {
  font-size: 28px;
  font-weight: 700;
}

.stat-card .icon {
  position: absolute;
  right: 12px;
  bottom: 8px;
  font-size: 48px;
  opacity: 0.15;
}

.chart-row {
  margin-bottom: 16px;
}
</style>