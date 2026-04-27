<template>
  <div class="history-page">
    <!-- 头部导航 -->
    <header class="header">
      <div class="header-content">
        <h1 class="logo">企业用工与社保合规智能平台</h1>
        <nav class="nav">
          <router-link to="/">问答首页</router-link>
          <router-link to="/history">历史记录</router-link>
          <router-link to="/admin">管理后台</router-link>
        </nav>
      </div>
    </header>

    <div class="container">
      <div class="card">
        <div class="history-header">
          <h2 class="title">历史记录</h2>
          <button class="btn btn-danger" @click="clearAllHistory" :disabled="historyList.length === 0">
            清空历史记录
          </button>
        </div>

        <div v-if="loading" class="loading">加载中...</div>
        
        <div v-else-if="historyList.length === 0" class="empty">
          暂无历史记录
        </div>

        <div v-else class="history-list">
          <div 
            v-for="item in historyList" 
            :key="item.id" 
            class="history-item"
            @click="viewDetail(item)"
          >
            <div class="history-question">
              <span class="question-label">问：</span>
              {{ item.question }}
            </div>
            <div class="history-answer">
              <span class="answer-label">答：</span>
              {{ truncateAnswer(item.answer) }}
            </div>
            <div class="history-meta">
              <span class="time">{{ formatTime(item.created_at) }}</span>
              <span v-if="item.is_feedback" class="feedback-tag">已反馈</span>
            </div>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="total > pageSize" class="pagination">
          <button @click="changePage(-1)" :disabled="page === 1">上一页</button>
          <span>{{ page }} / {{ totalPages }}</span>
          <button @click="changePage(1)" :disabled="page >= totalPages">下一页</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getHistory, clearHistory } from '@/api'

const historyList = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

// 获取历史记录
const fetchHistory = async () => {
  loading.value = true
  try {
    const userId = localStorage.getItem('user_id') || 'anonymous'
    const res = await getHistory({
      user_id: userId,
      page: page.value,
      page_size: pageSize.value
    })
    
    if (res.success) {
      historyList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取历史记录失败:', error)
  } finally {
    loading.value = false
  }
}

// 翻页
const changePage = (delta) => {
  const newPage = page.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchHistory()
  }
}

// 清空历史记录
const clearAllHistory = async () => {
  if (!confirm('确定要清空所有历史记录吗？')) return
  
  try {
    const userId = localStorage.getItem('user_id') || 'anonymous'
    await clearHistory(userId)
    historyList.value = []
    total.value = 0
    alert('历史记录已清空')
  } catch (error) {
    console.error('清空历史记录失败:', error)
    alert('清空失败，请重试')
  }
}

// 查看详情
const viewDetail = (item) => {
  // 可以跳转到详情页或弹出详情
  alert(`问题：${item.question}\n\n回答：${item.answer}`)
}

// 截断回答
const truncateAnswer = (text) => {
  if (!text) return ''
  return text.length > 100 ? text.substring(0, 100) + '...' : text
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.history-page {
  min-height: 100vh;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 15px 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 20px;
  color: #1890ff;
  margin: 0;
}

.nav a {
  margin-left: 20px;
  color: #666;
  text-decoration: none;
}

.nav a:hover,
.nav a.router-link-active {
  color: #1890ff;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.history-header .title {
  margin: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.history-item {
  padding: 15px;
  background: #fafafa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.history-item:hover {
  background: #f0f5ff;
  box-shadow: 0 2px 8px rgba(24, 144, 255, 0.15);
}

.history-question {
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.question-label {
  color: #1890ff;
}

.history-answer {
  color: #666;
  font-size: 13px;
  margin-bottom: 8px;
}

.answer-label {
  color: #52c41a;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.feedback-tag {
  padding: 2px 8px;
  background: #f6ffed;
  color: #52c41a;
  border-radius: 4px;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 10px;
  }
}</style>