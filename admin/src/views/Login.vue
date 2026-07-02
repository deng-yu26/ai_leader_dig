<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1 class="title">🪷 灵山胜境</h1>
        <p class="subtitle">AI数字人导游系统 · 管理后台</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        size="large"
        @submit.prevent="doLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="管理员账号"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="管理员密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%;">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <span>默认账号：admin / admin123</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { adminLogin } from '@/utils/api'
import { useAdminStore } from '@/store'

const router = useRouter()
const adminStore = useAdminStore()

const formRef = ref(null)
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})
const rules = {
  username: [{ required: true, message: '请输入管理员账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function doLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await adminLogin({
      username: form.username,
      password: form.password
    })
    if (res.code === 200) {
      adminStore.login(res.data)
      ElMessage.success('登录成功')
      router.push('/dashboard')
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (e) {
    ElMessage.error('网络错误，请稍后重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1a3a5c 0%, #2c5f8a 50%, #1a3a5c 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.title {
  font-size: 24px;
  color: #1a3a5c;
  margin-bottom: 8px;
}

.subtitle {
  font-size: 14px;
  color: #909399;
}

.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #c0c4cc;
}
</style>