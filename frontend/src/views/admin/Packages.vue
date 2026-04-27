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
        <h1>知识包管理</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 知识包列表 -->
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>知识包名称</th>
                <th>适用地区</th>
                <th>描述</th>
                <th>FAQ数量</th>
                <th>文档数量</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in packagesList" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="name-cell">{{ item.name }}</td>
                <td>{{ item.region }}</td>
                <td class="desc-cell">{{ truncateText(item.description) }}</td>
                <td>{{ item.faq_count }}</td>
                <td>{{ item.doc_count }}</td>
                <td>
                  <span 
                    class="tag" 
                    :class="item.status === 'active' ? 'tag-success' : 'tag-default'"
                  >
                    {{ item.status === 'active' ? '启用' : '禁用' }}
                  </span>
                </td>
                <td>{{ formatTime(item.updated_at) }}</td>
                <td>
                  <button 
                    class="btn-link" 
                    @click="toggleStatus(item)"
                  >
                    {{ item.status === 'active' ? '禁用' : '启用' }}
                  </button>
                  <button class="btn-link" @click="viewDetail(item)">详情</button>
                </td>
              </tr>
              <tr v-if="packagesList.length === 0">
                <td colspan="9" class="empty">暂无数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>

    <!-- 详情弹窗 -->
    <div v-if="showDetail" class="modal" @click.self="showDetail = false">
      <div class="modal-content">
        <h3>知识包详情</h3>
        <div class="detail-item">
          <label>名称：</label>
          <p>{{ currentDetail.name }}</p>
        </div>
        <div class="detail-item">
          <label>适用地区：</label>
          <p>{{ currentDetail.region }}</p>
        </div>
        <div class="detail-item">
          <label>描述：</label>
          <p>{{ currentDetail.description || '无' }}</p>
        </div>
        <div class="detail-item">
          <label>状态：</label>
          <p>{{ currentDetail.status === 'active' ? '启用' : '禁用' }}</p>
        </div>
        <div class="detail-item">
          <label>FAQ数量：</label>
          <p>{{ currentDetail.faq_count }}</p>
        </div>
        <div class="detail-item">
          <label>文档数量：</label>
          <p>{{ currentDetail.doc_count }}</p>
        </div>
        <div class="detail-item">
          <label>创建时间：</label>
          <p>{{ formatTime(currentDetail.created_at) }}</p>
        </div>
        <div class="detail-item">
          <label>更新时间：</label>
          <p>{{ formatTime(currentDetail.updated_at) }}</p>
        </div>
        <button class="btn btn-primary" @click="showDetail = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getKnowledgePackages, updatePackageStatus } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const packagesList = ref([])
const showDetail = ref(false)
const currentDetail = ref({})

// 获取知识包列表
const fetchPackages = async () => {
  try {
    const res = await getKnowledgePackages()
    if (res.success) {
      packagesList.value = res.data || []
    }
  } catch (error) {
    console.error('获取知识包失败:', error)
  }
}

// 切换状态
const toggleStatus = async (item) => {
  const newStatus = item.status === 'active' ? 'inactive' : 'active'
  const action = newStatus === 'active' ? '启用' : '禁用'
  
  if (!confirm(`确定要${action}知识包"${item.name}"吗？`)) return
  
  try {
    await updatePackageStatus(item.id, { status: newStatus })
    alert(`${action}成功`)
    fetchPackages()
  } catch (error) {
    console.error('更新状态失败:', error)
    alert('操作失败，请重试')
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
  return text.length > 30 ? text.substring(0, 30) + '...' : text
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
  fetchPackages()
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

.name-cell {
  font-weight: 500;
}

.desc-cell {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-default {
  background: #f5f5f5;
  color: #999;
  border: 1px solid #d9d9d9;
}

.btn-link {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  margin-right: 10px;
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