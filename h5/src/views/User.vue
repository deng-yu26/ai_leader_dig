<template>
  <div class="user-page">
    <van-nav-bar title="个人中心" left-arrow @click-left="$router.back()" />

    <!-- 用户信息区域 -->
    <div class="user-profile">
      <div class="avatar">👤</div>
      <div class="user-info">
        <div class="username">{{ userStore.userInfo?.username || '游客' }}</div>
        <div class="user-meta">
          <span v-if="userStore.userInfo?.phone">{{ userStore.userInfo.phone }}</span>
          <span v-if="userStore.userInfo?.email"> · {{ userStore.userInfo.email }}</span>
        </div>
      </div>
    </div>

    <!-- 功能列表 -->
    <van-cell-group inset class="menu-group">
      <van-cell title="切换数字人导游" is-link @click="$router.push('/digital-human')">
        <template #icon><span style="margin-right:8px;">🪷</span></template>
      </van-cell>
      <van-cell title="对话历史记录" is-link @click="$router.push('/history')">
        <template #icon><span style="margin-right:8px;">📋</span></template>
      </van-cell>
      <van-cell title="游览路线规划" is-link @click="$router.push('/route-plan')">
        <template #icon><span style="margin-right:8px;">🗺️</span></template>
      </van-cell>
    </van-cell-group>

    <!-- 当前数字人信息 -->
    <div class="dh-section">
      <div class="section-title">当前AI导游</div>
      <div class="dh-card">
        <div class="dh-icon">🪷</div>
        <div class="dh-name">{{ dhStore.currentName }}</div>
        <van-tag type="success" plain>在线</van-tag>
      </div>
    </div>

    <!-- 退出登录 -->
    <van-button
      round
      block
      plain
      class="logout-btn"
      @click="handleLogout"
    >
      退出登录
    </van-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Dialog, showSuccessToast } from 'vant'
import { useUserStore, useDigitalHumanStore } from '@/store'

const router = useRouter()
const userStore = useUserStore()
const dhStore = useDigitalHumanStore()

function handleLogout() {
  Dialog.confirm({
    title: '退出确认',
    message: '确定要退出登录吗？',
    confirmButtonText: '退出'
  }).then(() => {
    userStore.logout()
    showSuccessToast('已退出登录')
    router.push('/login')
  }).catch(() => {})
}
</script>

<style scoped>
.user-page {
  min-height: 100vh;
  background: #f5f7f0;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 32px 20px;
  background: linear-gradient(135deg, #5b8c5a, #7cb342);
  color: #fff;
}

.avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
}

.username {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.user-meta {
  font-size: 13px;
  opacity: 0.8;
}

.menu-group {
  margin: 16px;
}

.dh-section {
  margin: 16px;
}

.section-title {
  font-size: 14px;
  color: #6b7c6b;
  margin-bottom: 10px;
  padding-left: 4px;
}

.dh-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}

.dh-icon {
  font-size: 32px;
}

.dh-name {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
  color: #2e3d2e;
}

.logout-btn {
  margin: 32px 16px;
  color: #e74c3c;
  border-color: #e74c3c;
  width: auto;
}
</style>