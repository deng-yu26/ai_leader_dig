/**
 * 管理后台API请求工具
 */
import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true
})

// 响应拦截
api.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code === 401) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_info')
      window.location.hash = '#/login'
      ElMessage.error('登录已过期，请重新登录')
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  error => {
    ElMessage.error('网络请求失败：' + (error.message || '未知错误'))
    return Promise.reject(error)
  }
)

// ===== 管理员接口 =====
export const adminLogin = (data) => api.post('/admin/login', data)
export const getAdminInfo = () => api.get('/admin/info')
export const getUsers = (params) => api.get('/admin/users', { params })
export const deleteUser = (id) => api.delete(`/admin/users/${id}`)
export const getAdminDigitalHumans = () => api.get('/admin/digital-humans')
export const createDigitalHuman = (data) => api.post('/admin/digital-humans', data)
export const updateDigitalHuman = (id, data) => api.put(`/admin/digital-humans/${id}`, data)
export const deleteDigitalHuman = (id) => api.delete(`/admin/digital-humans/${id}`)
export const getKnowledgeList = (params) => api.get('/admin/knowledge', { params })
export const createKnowledge = (data) => api.post('/admin/knowledge', data)
export const updateKnowledge = (id, data) => api.put(`/admin/knowledge/${id}`, data)
export const deleteKnowledge = (id) => api.delete(`/admin/knowledge/${id}`)
export const syncKnowledge = () => api.post('/admin/knowledge/sync')
export const uploadKnowledgeFile = (formData) => api.post('/admin/knowledge/upload', formData, {
  headers: { 'Content-Type': 'multipart/form-data' },
  timeout: 60000
})
export const getKnowledgeGraph = () => api.get('/admin/knowledge/graph')
export const getKnowledgeStats = () => api.get('/admin/knowledge/stats')
export const getChatLogs = (params) => api.get('/admin/chat-logs', { params })
export const getDashboardStats = () => api.get('/admin/dashboard/stats')
export const getDashboardPref = () => api.get('/admin/dashboard/pref')
export const getEmotionReport = () => api.get('/admin/emotion/report', {
  timeout: 120000  // 2分钟超时（大模型分析需要较长时间）
})
export const getAiConfig = () => api.get('/admin/ai-config')
export const updateAiConfig = (data) => api.put('/admin/ai-config', data)
export const getAdmins = () => api.get('/admin/admins')
export const createAdmin = (data) => api.post('/admin/admins', data)

export default api