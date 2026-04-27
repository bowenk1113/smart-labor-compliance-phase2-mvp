import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

// ============ 用户端 API ============

// 问答接口
export const chat = (data) => api.post('/chat', data)

// 获取历史记录
export const getHistory = (params) => api.get('/history', { params })

// 清空历史记录
export const clearHistory = (userId) => api.delete('/history', { params: { user_id: userId } })

// 提交反馈
export const submitFeedback = (data) => api.post('/feedback', data)

// 获取推荐问题
export const getRecommendedQuestions = () => api.get('/recommended-questions')

// ============ 管理端 API ============

// 管理员登录
export const adminLogin = (data) => api.post('/admin/login', data)

// 验证令牌
export const verifyToken = () => api.get('/admin/verify-token')

// 获取统计概览
export const getStatistics = () => api.get('/admin/statistics')

// 获取问答日志
export const getLogs = (params) => api.get('/admin/logs', { params })

// 获取问答详情
export const getLogDetail = (id) => api.get(`/admin/logs/${id}`)

// 获取反馈列表
export const getFeedbacks = (params) => api.get('/admin/feedbacks', { params })

// 更新反馈状态
export const updateFeedbackStatus = (id, data) => api.put(`/admin/feedbacks/${id}`, data)

// 获取 FAQ 列表
export const getFaqs = (params) => api.get('/admin/faqs', { params })

// 添加 FAQ
export const addFaq = (data) => api.post('/admin/faqs', data)

// 更新 FAQ
export const updateFaq = (id, data) => api.put(`/admin/faqs/${id}`, data)

// 删除 FAQ
export const deleteFaq = (id) => api.delete(`/admin/faqs/${id}`)

// 获取来源列表
export const getSources = (params) => api.get('/admin/sources', { params })

// 添加来源
export const addSource = (data) => api.post('/admin/sources', data)

// 更新来源
export const updateSource = (id, data) => api.put(`/admin/sources/${id}`, data)

// 删除来源
export const deleteSource = (id) => api.delete(`/admin/sources/${id}`)

// 获取知识包列表
export const getKnowledgePackages = () => api.get('/admin/knowledge-packages')

// 更新知识包状态
export const updatePackageStatus = (id, data) => api.put(`/admin/knowledge-packages/${id}/status`, data)

export default api