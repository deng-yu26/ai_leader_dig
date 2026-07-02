<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="sidebar.isCollapsed ? '64px' : '220px'" class="aside">
      <div class="aside-header">
        <span v-if="!sidebar.isCollapsed" class="logo-text">🪷 灵山胜境后台</span>
        <span v-else class="logo-text-mini">🪷</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="sidebar.isCollapsed"
        :router="true"
        background-color="#1a3a5c"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>数据大屏</template>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        <el-menu-item index="/digital-humans">
          <el-icon><MagicStick /></el-icon>
          <template #title>数字人管理</template>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Notebook /></el-icon>
          <template #title>知识库管理</template>
        </el-menu-item>
        <el-menu-item index="/chat-logs">
          <el-icon><ChatDotSquare /></el-icon>
          <template #title>对话日志</template>
        </el-menu-item>
        <el-menu-item index="/ai-config">
          <el-icon><Setting /></el-icon>
          <template #title>AI参数配置</template>
        </el-menu-item>
        <el-menu-item index="/admins">
          <el-icon><UserFilled /></el-icon>
          <template #title>管理员管理</template>
        </el-menu-item>
        <el-menu-item index="/emotion-report">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>游客感受度报告</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主体区域 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button text @click="sidebar.toggle()">
            <el-icon :size="20"><Fold v-if="!sidebar.isCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <span class="page-name">{{ route.meta.title }}</span>
        </div>
        <div class="header-right">
          <span class="admin-name">👤 {{ adminStore.adminInfo?.username || '管理员' }}</span>
          <el-button text @click="handleLogout">退出</el-button>
        </div>
      </el-header>

      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAdminStore, useSidebarStore } from '@/store'

const route = useRoute()
const router = useRouter()
const adminStore = useAdminStore()
const sidebar = useSidebarStore()

const activeMenu = computed(() => route.path)

function handleLogout() {
  ElMessageBox.confirm('确定要退出登录吗？', '提示').then(() => {
    adminStore.logout()
    router.push('/login')
  }).catch(() => {})
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background: #1a3a5c;
  transition: width 0.3s;
  overflow: hidden;
}

.aside-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-text-mini {
  font-size: 24px;
}

.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a3a5c;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.admin-name {
  font-size: 14px;
  color: #606266;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>