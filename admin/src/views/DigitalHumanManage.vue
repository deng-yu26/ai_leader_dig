<template>
  <div class="dh-manage">
    <h2 class="page-title">🪷 数字人管理</h2>

    <!-- 添加按钮 -->
    <div style="margin-bottom: 16px;">
      <el-button type="primary" @click="showDialog(null)">+ 添加数字人</el-button>
    </div>

    <!-- 数字人列表 -->
    <el-card>
      <el-table :data="humans" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="数字人名称" min-width="150" />
        <el-table-column prop="model_path" label="模型路径" min-width="200" />
        <el-table-column label="默认参数" min-width="200">
          <template #default="{ row }">
            语速: {{ row.default_speed }} | 语调: {{ row.default_pitch }}
          </template>
        </el-table-column>
        <el-table-column prop="default_voice" label="默认音色" min-width="180" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="showDialog(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" size="small" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑数字人' : '添加数字人'" width="500px">
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="数字人名称" prop="name" :rules="[{ required: true, message: '请输入名称' }]">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="模型路径" prop="model_path" :rules="[{ required: true, message: '请输入模型路径' }]">
          <el-input v-model="form.model_path" placeholder="/live2d_models/xxx/" />
        </el-form-item>
        <el-form-item label="默认语速" prop="default_speed">
          <el-slider v-model="form.default_speed" :min="0.5" :max="2.0" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="默认语调" prop="default_pitch">
          <el-slider v-model="form.default_pitch" :min="0.5" :max="2.0" :step="0.1" show-input />
        </el-form-item>
        <el-form-item label="默认音色" prop="default_voice">
          <el-select v-model="form.default_voice" style="width: 100%;">
            <el-option label="晓晓（女声·推荐）" value="zh-CN-XiaoxiaoNeural" />
            <el-option label="云希（男声）" value="zh-CN-YunxiNeural" />
            <el-option label="晓伊（女声·活泼）" value="zh-CN-XiaoyiNeural" />
            <el-option label="晓涵（女声·温柔）" value="zh-CN-XiaohanNeural" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAdminDigitalHumans, createDigitalHuman, updateDigitalHuman, deleteDigitalHuman } from '@/utils/api'

const humans = ref([])
const loading = ref(false)
const saving = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)

const form = ref({
  name: '',
  model_path: '/live2d_models/default/',
  default_speed: 1.0,
  default_pitch: 1.0,
  default_voice: 'zh-CN-XiaoxiaoNeural',
  is_active: true
})

onMounted(() => fetchHumans())

async function fetchHumans() {
  loading.value = true
  try {
    const res = await getAdminDigitalHumans()
    if (res.code === 200) {
      humans.value = res.data || []
    }
  } catch (e) {
    console.error('获取数字人列表失败:', e)
  } finally {
    loading.value = false
  }
}

function showDialog(row) {
  if (row) {
    isEdit.value = true
    editId.value = row.id
    form.value = { ...row }
  } else {
    isEdit.value = false
    editId.value = null
    form.value = {
      name: '',
      model_path: '/live2d_models/default/',
      default_speed: 1.0,
      default_pitch: 1.0,
      default_voice: 'zh-CN-XiaoxiaoNeural',
      is_active: true
    }
  }
  dialogVisible.value = true
}

async function handleSave() {
  saving.value = true
  try {
    let res
    if (isEdit.value) {
      res = await updateDigitalHuman(editId.value, form.value)
    } else {
      res = await createDigitalHuman(form.value)
    }
    if (res.code === 200) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchHumans()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function handleDelete(id) {
  try {
    const res = await deleteDigitalHuman(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      fetchHumans()
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}
</script>