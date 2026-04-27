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
        <h1>平台概览</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_questions }}</div>
            <div class="stat-label">问答总量</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.today_questions }}</div>
            <div class="stat-label">今日问答</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_feedbacks }}</div>
            <div class="stat-label">反馈总量</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ stats.helpful_rate }}%</div>
            <div class="stat-label">有帮助率</div>
          </div>
        </div>

        <!-- 高频问题 -->
        <div class="card">
          <h2 class="subtitle">高频问题排行</h2>
          <table class="table">
            <thead>
              <tr>
                <th>排名</th>
                <th>问题</th>
                <th>提问次数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in stats.top_questions" :key="index">
                <td>{{ index + 1 }}</td>
                <td>{{ item.question }}</td>
                <td>{{ item.count }}</td>
              </tr>
              <tr v-if="!stats.top_questions || stats.top_questions.length === 0">
                <td colspan="3" class="empty">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStatistics } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const stats = ref({
  total_questions: 0,
  today_questions: 0,
  total_feedbacks: 0,
  helpful_rate: 0,
  top_questions: []
})

// 获取统计数据
const fetchStats = async () => {
  try {
    const res = await getStatistics()
    if (res.success) {
      stats.value = res.data
    }
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 退出登录
const logout = () => {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_id')
  localStorage.removeItem('admin_username')
  router.push('/admin/login')
}

onMounted(() => {
  fetchStats()
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

.username {
  color: #666;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  text-align: center;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #1890ff;
  margin-bottom: 10px;
}

.stat-label {
  color: #666;
  font-size: 14px;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
  
  .main-content {
    margin-left: 0;
  }
}</style>