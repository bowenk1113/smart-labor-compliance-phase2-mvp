<template>
  <div class="admin-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h2>管理后台</h2>
      </div>
      <nav class="sidebar-nav">
        <router-link to="/admin">概览</router-link>
        <router-link to="/admin/logs">问答日志</router-link>
        <router-link to="/admin/feedbacks">反馈管理</router-link>
        <router-link to="/admin/faqs">FAQ管理</router-link>
        <router-link to="/admin/sources">来源管理</router-link>
        <router-link to="/admin/packages">知识包管理</router-link>
        <a href="#" @click.prevent="logout">退出登录</a>
      </nav>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <div class="content-header">
        <h1>反馈管理</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 筛选栏 -->
        <div class="card">
          <div class="search-bar">
            <select v-model="filterType" class="input" style="width: 150px;">
              <option value="">全部反馈</option>
              <option value="true">有帮助</option>
              <option value="false">无帮助</option>
            </select>
            <button class="btn btn-primary" @click="searchFeedbacks">筛选</button>
          </div>
        </div>

        <!-- 反馈列表 -->
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>问题</th>
                <th>反馈类型</th>
                <th>备注</th>
                <th>状态</th>
                <th>时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in feedbacksList" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="question-cell">{{ item.question }}</td>
                <td>
                  <span :class="['tag', item.is_helpful ? 'tag-success' : 'tag-danger']">
                    {{ item.is_helpful ? '有帮助' : '无帮助' }}
                  </span>
                </td>
                <td class="remark-cell">{{ truncateText(item.remark) }}</td>
                <td>
                  <select 
                    v-model="item.status" 
                    @change="updateStatus(item)"
                    class="status-select"
                  >
                    <option value="pending">待处理</option>
                    <option value="processed">处理中</option>
                    <option value="resolved">已解决</option>
                  </select>
                </td>
                <td>{{ formatTime(item.created_at) }}</td>
                <td>
                  <button class="btn-link" @click="viewDetail(item)">查看</button>
                </td>
              </tr>
              <tr v-if="feedbacksList.length === 0">
                <td colspan="7" class="empty">暂无数据</td>
              </tr>
            </tbody>
          </table>

          <!-- 分页 -->
          <div v-if="total > pageSize" class="pagination">
            <button @click="changePage(-1)" :disabled="page === 1">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button @click="changePage(1)" :disabled="page >= totalPages">下一页</button>
          </div>
        </div>
      </div>
    </main>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal" @click.self="showDetail = false">
      <div class="modal-content">
        <h3>反馈详情</h3>
        <div class="detail-item">
          <label>问题：</label>
          <p>{{ currentDetail.question }}</p>
        </div>
        <div class="detail-item">
          <label>反馈类型：</label>
          <p>{{ currentDetail.is_helpful ? '有帮助' : '无帮助' }}</p>
        </div>
        <div class="detail-item">
          <label>备注：</label>
          <p>{{ currentDetail.remark || '无' }}</p>
        </div>
        <div class="detail-item">
          <label>状态：</label>
          <p>{{ getStatusText(currentDetail.status) }}</p>
        </div>
        <div class="detail-item">
          <label>时间：</label>
          <p>{{ formatTime(currentDetail.created_at) }}</p>
        </div>
        <button class="btn btn-primary" @click="showDetail = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getFeedbacks, updateFeedbackStatus } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const feedbacksList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const filterType = ref('')
const showDetail = ref(false)
const currentDetail = ref({})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

// 获取反馈列表
const fetchFeedbacks = async () => {
  try {
    const res = await getFeedbacks({
      page: page.value,
      page_size: pageSize.value,
      is_helpful: filterType.value
    })
    
    if (res.success) {
      feedbacksList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取反馈失败:', error)
  }
}

// 筛选
const searchFeedbacks = () => {
  page.value = 1
  fetchFeedbacks()
}

// 翻页
const changePage = (delta) => {
  const newPage = page.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchFeedbacks()
  }
}

// 更新状态
const updateStatus = async (item) => {
  try {
    await updateFeedbackStatus(item.id, { status: item.status })
    alert('状态更新成功')
  } catch (error) {
    console.error('更新状态失败:', error)
    alert('更新失败，请重试')
  }
}

// 查看详情
const viewDetail = (item) => {
  currentDetail.value = item
  showDetail.value = true
}

// 截断文本
const truncateText = (text) => {
  if (!text) return '无'
  return text.length > 30 ? text.substring(0, 30) + '...' : text
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    pending: '待处理',
    processed: '处理中',
    resolved: '已解决'
  }
  return map[status] || status
}

// 退出登录
const logout = () => {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_id')
  localStorage.removeItem('admin_username')
  router.push('/admin/login')
}

onMounted(() => {
  fetchFeedbacks()
})
</script>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: #001529;
  color: #fff;
  position: fixed;
  height: 100vh;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #ffffff1f;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
}

.sidebar-nav {
  padding: 10px 0;
}

.sidebar-nav a {
  display: block;
  padding: 12px 20px;
  color: #ffffff99;
  text-decoration: none;
  transition: all 0.3s;
}

.sidebar-nav a:hover,
.sidebar-nav a.router-link-active {
  background: #1890ff;
  color: #fff;
}

.main-content {
  flex: 1;
  margin-left: 220px;
  background: #f0f2f5;
  min-height: 100vh;
}

.content-header {
  background: #fff;
  padding: 15px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.content-header h1 {
  margin: 0;
  font-size: 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.question-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remark-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-select {
  padding: 4px 8px;
  border: 1px solid #d9d9d9;
  border-radius: 4px;
}

.btn-link {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
}

.btn-link:hover {
  text-decoration: underline;
}

/* 弹窗样式 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: #fff;
  padding: 30px;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 20px;
}

.detail-item {
  margin-bottom: 15px;
}

.detail-item label {
  font-weight: 600;
  color: #333;
}

.detail-item p {
  margin: 5px 0 0;
  color: #666;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
  
  .main-content {
    margin-left: 0;
  }
}</style>