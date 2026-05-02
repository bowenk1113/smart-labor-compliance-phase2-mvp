import axios from 'axios'

export const DEFAULT_TENANT_CODE = 'demo-sx'

const api = axios.create({
  baseURL: '/api',
  timeout: 45000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const getTenantCode = () => localStorage.getItem('tenant_code') || DEFAULT_TENANT_CODE

export const setTenantCode = (code) => {
  localStorage.setItem('tenant_code', code || DEFAULT_TENANT_CODE)
}

api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    config.headers['X-Tenant-Code'] = getTenantCode()
    return config
  },
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response.data,
  error => {
    const isLoginRequest = error.config?.url === '/admin/login'
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_role')
      window.location.href = '/admin/login'
    }
    return Promise.reject(error)
  }
)

export const unwrapList = (res) => res?.data?.list || res?.data || []
export const unwrapData = (res) => res?.data

export const chat = (data) => api.post('/chat', data)
export const getHistory = (params) => api.get('/history', { params })
export const clearHistory = (userId) => api.delete('/history', { params: { user_id: userId } })
export const submitFeedback = (data) => api.post('/feedback', data)
export const getRecommendedQuestions = () => api.get('/recommended-questions')
export const getTenantPublic = () => api.get('/tenant-public')

export const adminLogin = (data) => api.post('/admin/login', data)
export const verifyToken = () => api.get('/admin/verify-token')
export const getStatistics = (params) => api.get('/admin/statistics', { params })
export const getServiceStatus = () => api.get('/admin/service-status')

export const getTenants = (params) => api.get('/admin/tenants', { params })
export const addTenant = (data) => api.post('/admin/tenants', data)
export const updateTenant = (id, data) => api.put(`/admin/tenants/${id}`, data)

export const getLogs = (params) => api.get('/admin/logs', { params })
export const getLogDetail = (id) => api.get(`/admin/logs/${id}`)

export const getFeedbacks = (params) => api.get('/admin/feedbacks', { params })
export const updateFeedbackStatus = (id, data) => api.put(`/admin/feedbacks/${id}`, data)

export const getFaqs = (params) => api.get('/admin/faqs', { params })
export const addFaq = (data, params = {}) => api.post('/admin/faqs', data, { params })
export const updateFaq = (id, data) => api.put(`/admin/faqs/${id}`, data)
export const deleteFaq = (id) => api.delete(`/admin/faqs/${id}`)

export const getSources = (params) => api.get('/admin/sources', { params })
export const addSource = (data, params = {}) => api.post('/admin/sources', data, { params })
export const updateSource = (id, data) => api.put(`/admin/sources/${id}`, data)
export const reviewSource = (id, reviewStatus) => api.put(`/admin/sources/${id}`, { review_status: reviewStatus })
export const uploadSourceFile = (file, params = {}) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/admin/sources/upload', formData, { params })
}
export const deleteSource = (id) => api.delete(`/admin/sources/${id}`)

export const getKnowledgePackages = (params) => api.get('/admin/knowledge-packages', { params })
export const updatePackageStatus = (id, data) => api.put(`/admin/knowledge-packages/${id}/status`, data)

export const getTestQuestions = (params) => api.get('/admin/test-questions', { params })

export const getRoles = () => api.get('/admin/roles')
export const getAdmins = (params) => api.get('/admin/admins', { params })
export const addAdmin = (data) => api.post('/admin/admins', data)
export const updateAdmin = (id, data) => api.put(`/admin/admins/${id}`, data)
export const deleteAdmin = (id) => api.delete(`/admin/admins/${id}`)

export default api
