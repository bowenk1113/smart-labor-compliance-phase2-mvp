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
        <h1>问答日志</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 搜索栏 -->
        <div class="card">
          <div class="search-bar">
            <input 
              v-model="searchKeyword" 
              type="text" 
              class="input" 
              placeholder="搜索问题内容..."
              style="width: 300px;"
            />
            <select v-model="statusFilter" class="input" style="width: 150px;">
              <option value="">全部状态</option>
              <option value="success">成功</option>
              <option value="failed">失败</option>
            </select>
            <button class="btn btn-primary" @click="searchLogs">搜索</button>
          </div>
        </div>

        <!-- 日志列表 -->
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户问题</th>
                <th>回答摘要</th>
                <th>响应时间</th>
                <th>状态</th>
                <th>时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in logsList" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="question-cell">{{ item.question }}</td>
                <td class="answer-cell">{{ truncateText(item.answer) }}</td>
                <td>{{ item.response_time }}ms</td>
                <td>
                  <span :class="['tag', item.status === 'success' ? 'tag-success' : 'tag-danger']">
                    {{ item.status === 'success' ? '成功' : '失败' }}
                  </span>
                </td>
                <td>{{ formatTime(item.created_at) }}</td>
                <td>
                  <button class="btn-link" @click="viewDetail(item)">查看</button>
                </td>
              </tr>
              <tr v-if="logsList.length === 0">
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
        <h3>问答详情</h3>
        <div class="detail-item">
          <label>问题：</label>
          <p>{{ currentDetail.question }}</p>
        </div>
        <div class="detail-item">
          <label>回答：</label>
          <p>{{ currentDetail.answer }}</p>
        </div>
        <div class="detail-item">
          <label>来源：</label>
          <p>{{ currentDetail.sources ? currentDetail.sources.join(', ') : '无' }}</p>
        </div>
        <div class="detail-item">
          <label>响应时间：</label>
          <p>{{ currentDetail.response_time }}ms</p>
        </div>
        <div class="detail-item">
          <label>状态：</label>
          <p>{{ currentDetail.status }}</p>
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
import { getLogs } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const logsList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const statusFilter = ref('')
const showDetail = ref(false)
const currentDetail = ref({})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

// 获取日志列表
const fetchLogs = async () => {
  try {
    const res = await getLogs({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value,
      status: statusFilter.value
    })
    
    if (res.success) {
      logsList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取日志失败:', error)
  }
}

// 搜索
const searchLogs = () => {
  page.value = 1
  fetchLogs()
}

// 翻页
const changePage = (delta) => {
  const newPage = page.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchLogs()
  }
}

// 查看详情
const viewDetail = (item) => {
  currentDetail.value = item
  showDetail.value = true
}

// 截断文本
const truncateText = (text) => {
  if (!text) return ''
  return text.length > 50 ? text.substring(0, 50) + '...' : text
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

// 退出登录
const logout = () => {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_id')
  localStorage.removeItem('admin_username')
  router.push('/admin/login')
}

onMounted(() => {
  fetchLogs()
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

.answer-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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