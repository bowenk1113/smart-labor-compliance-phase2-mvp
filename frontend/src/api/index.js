// 引入 axios，用它统一发送前端到后端的 HTTP 请求。
import axios from 'axios'

// 默认租户编码，演示环境使用 demo-sx。
export const DEFAULT_TENANT_CODE = 'demo-sx'

// 创建一个 axios 实例，后续所有 API 都复用这一份配置。
const api = axios.create({
  // baseURL 写成 /api，是为了走 Vite 代理转发到 FastAPI 后端。
  baseURL: '/api',
  // 问答可能需要检索和生成，所以超时时间设置得比普通接口更长。
  timeout: 45000,
  // 默认请求体使用 JSON。
  headers: {
    'Content-Type': 'application/json'
  }
})

// 从浏览器本地存储读取租户编码；没有设置时使用默认演示租户。
export const getTenantCode = () => localStorage.getItem('tenant_code') || DEFAULT_TENANT_CODE

// 保存租户编码，后续请求会自动带上这个租户。
export const setTenantCode = (code) => {
  localStorage.setItem('tenant_code', code || DEFAULT_TENANT_CODE)
}

// 请求拦截器：每次请求发出前统一补充认证、租户等信息。
api.interceptors.request.use(
  config => {
    // 管理后台登录后会把 token 存在 localStorage。
    const token = localStorage.getItem('admin_token')
    // 如果存在 token，就放到 Authorization 头里。
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 文件上传使用 FormData 时，浏览器需要自动生成 multipart boundary。
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    // 后端通过 X-Tenant-Code 判断当前访问哪个租户。
    config.headers['X-Tenant-Code'] = getTenantCode()
    // 返回修改后的请求配置。
    return config
  },
  // 请求配置阶段出错时，直接把错误交给调用方处理。
  error => Promise.reject(error)
)

// 响应拦截器：统一拆包并处理未登录跳转。
api.interceptors.response.use(
  // 后端返回结构通常是 { success, message, data }，这里直接返回 response.data。
  response => response.data,
  error => {
    // 登录接口自身 401 不跳转，避免登录页循环刷新。
    const isLoginRequest = error.config?.url === '/admin/login'
    // 非登录接口遇到 401，说明后台 token 失效。
    if (error.response?.status === 401 && !isLoginRequest) {
      // 清掉本地登录状态。
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_role')
      // 跳转到管理后台登录页。
      window.location.href = '/admin/login'
    }
    // 继续把错误抛给页面，让页面显示错误提示。
    return Promise.reject(error)
  }
)

// 列表接口常见结构有 data.list 或 data，这里做一个兼容提取。
export const unwrapList = (res) => res?.data?.list || res?.data || []
// 普通详情接口直接取 data。
export const unwrapData = (res) => res?.data

// 把后端返回的 Blob 文件保存成浏览器下载。
const downloadBlob = (blob, filename) => {
  // 创建临时 blob URL。
  const url = URL.createObjectURL(blob)
  // 创建一个隐藏 a 标签。
  const link = document.createElement('a')
  // 设置下载地址。
  link.href = url
  // 设置下载文件名。
  link.download = filename
  // 插入 DOM，浏览器才允许触发点击。
  document.body.appendChild(link)
  // 模拟点击开始下载。
  link.click()
  // 下载触发后移除临时节点。
  link.remove()
  // 释放 blob URL，避免内存泄漏。
  URL.revokeObjectURL(url)
}

// 后台 CSV 导入使用的公共上传方法。
const uploadCsv = (url, file, params = {}) => {
  // 创建 multipart/form-data 请求体。
  const formData = new FormData()
  // 后端统一从 file 字段取上传文件。
  formData.append('file', file)
  // params 用于传 query 参数，例如租户或导入模式。
  return api.post(url, formData, { params })
}

// 后台 CSV 导出使用的公共下载方法。
const exportCsv = async (url, params = {}, filename = 'export.csv') => {
  // responseType=blob 表示把响应当成二进制文件。
  const res = await api.get(url, { params, responseType: 'blob' })
  // 调用下载工具函数保存文件。
  downloadBlob(res, filename)
}

// 普通问答接口：前端传 question/scenario_id 等字段，后端走二期 RAG Pipeline。
export const chat = (data, config = {}) => api.post('/chat', data, config)
// 带附件问答接口：使用 FormData，把问题字段和文件一起传给后端。
export const chatWithFile = (data, file, config = {}) => {
  // 创建文件上传表单。
  const formData = new FormData()
  // 遍历 payload，把非空字段都放进表单。
  Object.entries(data).forEach(([key, value]) => {
    // undefined/null 不传，避免后端收到无意义字段。
    if (value !== undefined && value !== null) {
      formData.append(key, value)
    }
  })
  // 附件统一放到 file 字段。
  formData.append('file', file)
  // 发送到带文件问答接口。
  return api.post('/chat-with-file', formData, config)
}
// 停止生成接口，用于用户点击“停止生成”。
export const stopChatGeneration = (data) => api.post('/chat/stop', data)
// 获取问答历史。
export const getHistory = (params) => api.get('/history', { params })
// 导出问答历史 CSV。
export const exportHistory = (params = {}) => exportCsv('/history/export', params, 'history.csv')
// 清空某个用户的问答历史。
export const clearHistory = (userId) => api.delete('/history', { params: { user_id: userId } })
// 提交答案反馈。
export const submitFeedback = (data) => api.post('/feedback', data)
// 获取推荐问题；二期会按 scenario_id 返回对应场景 FAQ。
export const getRecommendedQuestions = (params = {}) => api.get('/recommended-questions', { params })
// 获取二期场景列表，供前端场景选择器展示。
export const getScenarios = () => api.get('/scenarios')
// 获取当前租户公开信息，用于顶部展示。
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
export const importFaqs = (file, params = {}) => uploadCsv('/admin/faqs/import', file, params)
export const exportFaqs = (params = {}) => exportCsv('/admin/faqs/export', params, 'faqs.csv')
export const batchFaqs = (data) => api.post('/admin/faqs/batch', data)

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
export const importSources = (file, params = {}) => uploadCsv('/admin/sources/import', file, params)
export const exportSources = (params = {}) => exportCsv('/admin/sources/export', params, 'sources.csv')
export const batchSources = (data) => api.post('/admin/sources/batch', data)

export const getKnowledgePackages = (params) => api.get('/admin/knowledge-packages', { params })
export const updatePackageStatus = (id, data) => api.put(`/admin/knowledge-packages/${id}/status`, data)
export const importKnowledgePackages = (file, params = {}) => uploadCsv('/admin/knowledge-packages/import', file, params)
export const exportKnowledgePackages = (params = {}) => exportCsv('/admin/knowledge-packages/export', params, 'knowledge-packages.csv')
export const batchKnowledgePackages = (data) => api.post('/admin/knowledge-packages/batch', data)
// 查看 RAG 知识库同步状态：当前向量后端、本地缓存、runtime FAQ 文件和最近一次同步动作。
export const getRagSyncStatus = () => api.get('/admin/rag/sync-status')
// 清空本地 RAG 的 lru_cache 索引缓存，让下一次问答重新读取知识库文件。
export const reloadRagLocalCache = () => api.post('/admin/rag/reload-local-cache')
// 重建 Milvus 向量库；Local MVP 不需要频繁调用，Milvus 演示/验收时使用。
export const rebuildRagMilvus = (data = {}) => api.post('/admin/rag/rebuild-milvus', data)

export const getTestQuestions = (params) => api.get('/admin/test-questions', { params })

export const getRoles = () => api.get('/admin/roles')
export const getAdmins = (params) => api.get('/admin/admins', { params })
export const addAdmin = (data) => api.post('/admin/admins', data)
export const updateAdmin = (id, data) => api.put(`/admin/admins/${id}`, data)
export const deleteAdmin = (id) => api.delete(`/admin/admins/${id}`)

export default api
