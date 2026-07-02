<template>
  <div class="admin-manage">
    <h2 class="page-title">👑 管理员管理</h2>

    <div style="margin-bottom: 16px;">
      <el-button type="primary" @click="showDialog = true">+ 添加管理员</el-button>
    </div>

    <el-card>
      <el-table :data="admins" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="账号" min-width="150" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
      </el-table>
    </el-card>

    <!-- 添加管理员对话框 -->
    <el-dialog v-model="showDialog" title="添加管理员" width="400px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="管理员账号" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdmins, createAdmin } from '@/utils/api'

const admins = ref([])
const loading = ref(false)
const saving = ref(false)
const showDialog = ref(false)
const formRef = ref(null)

const form = ref({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

onMounted(() => fetchAdmins())

async function fetchAdmins() {
  loading.value = true
  try {
    const res = await getAdmins()
    if (res.code === 200) {
      admins.value = res.data || []
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const res = await createAdmin(form.value)
    if (res.code === 200) {
      ElMessage.success('添加成功')
      showDialog.value = false
      form.value = { username: '', password: '' }
      fetchAdmins()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('添加失败')
  } finally {
    saving.value = false
  }
}
</script>