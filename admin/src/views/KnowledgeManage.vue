<template>
  <div class="knowledge-manage">
    <h2 class="page-title">知识库管理</h2>

    <!-- 统计概览 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.vector_doc_count }}</div>
          <div class="stat-label">向量文档块</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.faq_count }}</div>
          <div class="stat-label">FAQ条目</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.vector_sync_count }}</div>
          <div class="stat-label">已同步条目</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-label">知识库状态</div>
          <el-tag :type="stats.vector_doc_count > 0 ? 'success' : 'warning'" size="small">
            {{ stats.vector_doc_count > 0 ? '已就绪' : '未构建' }}
          </el-tag>
        </el-card>
      </el-col>
    </el-row>

    <!-- 操作栏 -->
    <el-row :gutter="16" class="action-row">
      <el-col :span="6">
        <el-button type="success" @click="showUploadDialog" style="width:100%">
          上传知识文件
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button type="primary" @click="showDialog(null)" style="width:100%">
          添加知识条目
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button type="warning" @click="handleSync" :loading="syncing" style="width:100%">
          同步向量库
        </el-button>
      </el-col>
      <el-col :span="6">
        <el-button type="info" @click="showGraphDialog" style="width:100%">
          知识图谱
        </el-button>
      </el-col>
    </el-row>

    <!-- 搜索栏 -->
    <div class="search-form">
      <el-input
        v-model="keyword"
        placeholder="搜索问题..."
        clearable
        style="width: 300px;"
        @keyup.enter="search"
        @clear="fetchKnowledge"
      />
      <el-button type="primary" @click="search">搜索</el-button>
    </div>

    <!-- 知识库列表 -->
    <el-card>
      <el-table :data="knowledgeList" stripe v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="answer" label="答案" min-width="300" show-overflow-tooltip />
        <el-table-column prop="doc_source" label="来源" width="150" show-overflow-tooltip />
        <el-table-column label="向量同步" width="100">
          <template #default="{ row }">
            <el-tag :type="row.vector_sync ? 'success' : 'warning'" size="small">
              {{ row.vector_sync ? '已同步' : '待同步' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170" />
        <el-table-column label="操作" width="150" fixed="right">
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

      <div class="pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="perPage"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="fetchKnowledge"
          @size-change="fetchKnowledge"
        />
      </div>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑知识条目' : '添加知识条目'"
      width="600px"
    >
      <el-form ref="formRef" :model="form" label-width="80px">
        <el-form-item label="问题" prop="question" :rules="[{ required: true, message: '请输入问题' }]">
          <el-input v-model="form.question" type="textarea" :rows="2" placeholder="请输入问题内容" />
        </el-form-item>
        <el-form-item label="答案" prop="answer" :rules="[{ required: true, message: '请输入答案' }]">
          <el-input v-model="form.answer" type="textarea" :rows="4" placeholder="请输入答案内容" />
        </el-form-item>
        <el-form-item label="文档来源">
          <el-input v-model="form.doc_source" placeholder="手动录入" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文件上传对话框 -->
    <el-dialog
      v-model="uploadVisible"
      title="上传知识文件"
      width="520px"
    >
      <div class="upload-tip">
        <p>支持的文件格式：docx、xlsx、txt、pdf</p>
        <p>上传后系统将自动提取内容并加入向量知识库</p>
      </div>
      <el-upload
        ref="uploadRef"
        class="upload-area"
        drag
        :auto-upload="false"
        :on-change="handleFileSelect"
        :before-upload="beforeUpload"
        :file-list="fileList"
        :limit="1"
        accept=".docx,.xlsx,.txt,.pdf"
      >
        <div class="upload-content">
          <el-icon class="upload-icon"><UploadFilled /></el-icon>
          <p>点击或将文件拖拽到此区域</p>
          <p class="upload-hint">支持 docx / xlsx / txt / pdf 文件</p>
        </div>
      </el-upload>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          确认上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 知识图谱对话框 -->
    <el-dialog
      v-model="graphVisible"
      title="知识库图谱"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="graph-container" v-loading="graphLoading">
        <div ref="graphCanvasRef" class="graph-canvas"></div>
      </div>
      <template #footer>
        <el-button @click="graphVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getKnowledgeList,
  createKnowledge,
  updateKnowledge,
  deleteKnowledge,
  syncKnowledge,
  uploadKnowledgeFile,
  getKnowledgeGraph,
  getKnowledgeStats
} from '@/utils/api'

const knowledgeList = ref([])
const loading = ref(false)
const saving = ref(false)
const syncing = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const keyword = ref('')
const page = ref(1)
const perPage = ref(20)
const total = ref(0)
const formRef = ref(null)
const form = ref({ question: '', answer: '', doc_source: '' })

// 统计信息
const stats = ref({
  vector_doc_count: 0,
  faq_count: 0,
  vector_sync_count: 0
})

// 文件上传
const uploadVisible = ref(false)
const uploading = ref(false)
const uploadRef = ref(null)
const fileList = ref([])
const selectedFile = ref(null)

// 知识图谱
const graphVisible = ref(false)
const graphLoading = ref(false)
const graphCanvasRef = ref(null)
let graphChart = null

onMounted(() => {
  fetchKnowledge()
  fetchStats()
})

onBeforeUnmount(() => {
  if (graphChart) {
    graphChart.dispose()
    graphChart = null
  }
})

async function fetchKnowledge() {
  loading.value = true
  try {
    const res = await getKnowledgeList({ page: page.value, per_page: perPage.value, keyword: keyword.value })
    if (res.code === 200) {
      knowledgeList.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await getKnowledgeStats()
    if (res.code === 200) {
      stats.value = res.data
    }
  } catch (e) {
    console.error(e)
  }
}

function search() {
  page.value = 1
  fetchKnowledge()
}

function showDialog(row) {
  isEdit.value = !!row
  editId.value = row?.id || null
  form.value = row
    ? { question: row.question, answer: row.answer, doc_source: row.doc_source || '' }
    : { question: '', answer: '', doc_source: '' }
  dialogVisible.value = true
}

async function handleSave() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  saving.value = true
  try {
    let res
    if (isEdit.value) {
      res = await updateKnowledge(editId.value, form.value)
    } else {
      res = await createKnowledge(form.value)
    }
    if (res.code === 200) {
      ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
      dialogVisible.value = false
      fetchKnowledge()
      fetchStats()
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
    const res = await deleteKnowledge(id)
    if (res.code === 200) {
      ElMessage.success('删除成功')
      fetchKnowledge()
      fetchStats()
    }
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

async function handleSync() {
  syncing.value = true
  try {
    const res = await syncKnowledge()
    if (res.code === 200) {
      ElMessage.success(res.message || '同步完成')
      fetchKnowledge()
      fetchStats()
    }
  } catch (e) {
    ElMessage.error('同步失败')
  } finally {
    syncing.value = false
  }
}

// ===== 文件上传 =====
function showUploadDialog() {
  uploadVisible.value = true
  fileList.value = []
  selectedFile.value = null
}

function handleFileSelect(file) {
  selectedFile.value = file.raw
}

function beforeUpload() {
  return false
}

async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const res = await uploadKnowledgeFile(formData)
    if (res.code === 200) {
      ElMessage.success(res.message || '上传成功')
      uploadVisible.value = false
      fetchKnowledge()
      fetchStats()
    } else {
      ElMessage.error(res.message)
    }
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// ===== 知识图谱 =====
function showGraphDialog() {
  graphVisible.value = true
  graphLoading.value = true
  fetchGraphData()
}

async function fetchGraphData() {
  try {
    const res = await getKnowledgeGraph()
    if (res.code === 200) {
      renderGraph(res.data)
    }
  } catch (e) {
    console.error(e)
  } finally {
    graphLoading.value = false
  }
}

function renderGraph(data) {
  if (!graphCanvasRef.value) return

  // 确保节点和边使用相同的label
  const nodeMap = {}
  data.nodes.forEach(n => {
    if (!nodeMap[n.label]) {
      nodeMap[n.label] = { id: n.label, name: n.label, category: n.category }
    }
  })

  const chartNodes = Object.values(nodeMap)
  const chartEdges = []
  const categoryColors = {
    '景点': '#409eff',
    '服务': '#67c23a',
    '路线': '#e6a23c',
    'knowledge': '#909399',
    'faq': '#f56c6c'
  }

  // 构建图边
  data.edges.forEach(e => {
    const sourceNode = chartNodes.find(n => n.id === e.source)
    const targetNode = chartNodes.find(n => n.id === e.target)
    if (sourceNode && targetNode) {
      chartEdges.push({
        source: e.source,
        target: e.target,
        lineStyle: { color: categoryColors[e.category] || '#c0c4cc' }
      })
    }
  })

  const option = {
    title: {
      text: '灵山胜境知识库图谱',
      left: 'center',
      textStyle: { fontSize: 18 }
    },
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const nodeData = data.nodes.find(n => n.label === params.name)
        if (nodeData) {
          return `<div style="max-width:300px">
            <strong>${params.name}</strong><br/>
            <span style="color:#999">${params.data.category || ''}</span><br/>
            <div style="margin-top:4px;color:#666;font-size:12px">${nodeData.text || ''}</div>
          </div>`
        }
        return params.name
      }
    },
    legend: {
      data: ['景点', '服务', '路线', '知识', 'FAQ'],
      bottom: 0,
      left: 'center'
    },
    series: [{
      type: 'graph',
      layout: 'force',
      data: chartNodes.map(n => ({
        id: n.id,
        name: n.name,
        symbolSize: 50,
        category: getCategoryIndex(n.category),
        itemStyle: {
          color: categoryColors[n.category] || '#909399'
        },
        label: {
          show: true,
          fontSize: 12
        }
      })),
      categories: [
        { name: '景点', itemStyle: { color: '#409eff' } },
        { name: '服务', itemStyle: { color: '#67c23a' } },
        { name: '路线', itemStyle: { color: '#e6a23c' } },
        { name: '知识', itemStyle: { color: '#909399' } },
        { name: 'FAQ', itemStyle: { color: '#f56c6c' } }
      ],
      edges: chartEdges,
      force: {
        repulsion: 200,
        edgeLength: 80,
        gravity: 0.1
      },
      roam: true,
      draggable: true,
      lineStyle: {
        color: '#c0c4cc',
        width: 1,
        curveness: 0.2
      },
      label: {
        show: true,
        position: 'right',
        fontSize: 12
      }
    }]
  }

  function getCategoryIndex(category) {
    const map = { '景点': 0, '服务': 1, '路线': 2, 'knowledge': 3, 'faq': 4 }
    return map[category] ?? 3
  }

  if (graphChart) {
    graphChart.dispose()
  }
  graphChart = echarts.init(graphCanvasRef.value)
  graphChart.setOption(option)

  graphChart.on('click', (params) => {
    if (params.dataType === 'node') {
      const nodeData = data.nodes.find(n => n.label === params.name)
      if (nodeData) {
        ElMessage.info(`知识节点：${params.name} - ${nodeData.text || ''}`)
      }
    }
  })
}
</script>

<style scoped>
.page-title {
  font-size: 22px;
  margin: 0 0 20px;
  color: #303133;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 12px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: #909399;
}

/* 操作栏 */
.action-row {
  margin-bottom: 16px;
}

/* 搜索栏 */
.search-form {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 分页 */
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

/* 文件上传 */
.upload-tip {
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 16px;
}

.upload-tip p {
  margin: 4px 0;
  font-size: 13px;
  color: #606266;
}

.upload-area {
  display: flex;
  justify-content: center;
}

.upload-content {
  text-align: center;
  padding: 20px;
}

.upload-icon {
  font-size: 48px;
  color: #409eff;
}

.upload-hint {
  font-size: 12px;
  color: #909399;
}

/* 知识图谱 */
.graph-container {
  width: 100%;
  height: 500px;
}

.graph-canvas {
  width: 100%;
  height: 100%;
}
</style>