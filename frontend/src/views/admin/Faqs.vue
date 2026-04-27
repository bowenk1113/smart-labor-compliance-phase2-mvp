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
        <h1>FAQ管理</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 操作栏 -->
        <div class="card">
          <div class="action-bar">
            <button class="btn btn-primary" @click="showAddModal = true">添加FAQ</button>
            <input 
              v-model="searchKeyword" 
              type="text" 
              class="input" 
              placeholder="搜索问题..."
              style="width: 300px;"
            />
            <button class="btn btn-primary" @click="searchFaqs">搜索</button>
          </div>
        </div>

        <!-- FAQ列表 -->
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>问题</th>
                <th>答案摘要</th>
                <th>分类</th>
                <th>关键词</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in faqsList" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="question-cell">{{ item.question }}</td>
                <td class="answer-cell">{{ truncateText(item.answer) }}</td>
                <td>{{ item.category }}</td>
                <td>{{ (item.keywords || []).join(', ') }}</td>
                <td>{{ formatTime(item.updated_at) }}</td>
                <td>
                  <button class="btn-link" @click="editFaq(item)">编辑</button>
                  <button class="btn-link btn-danger" @click="deleteFaq(item)">删除</button>
                </td>
              </tr>
              <tr v-if="faqsList.length === 0">
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

    <!-- 添加/编辑弹窗 -->
    <div v-if="showAddModal" class="modal" @click.self="closeModal">
      <div class="modal-content">
        <h3>{{ isEdit ? '编辑FAQ' : '添加FAQ' }}</h3>
        <form @submit.prevent="submitFaq">
          <div class="form-group">
            <label>问题</label>
            <input v-model="form.question" type="text" class="input" required />
          </div>
          <div class="form-group">
            <label>答案</label>
            <textarea v-model="form.answer" class="input" rows="4" required></textarea>
          </div>
          <div class="form-group">
            <label>分类</label>
            <input v-model="form.category" type="text" class="input" />
          </div>
          <div class="form-group">
            <label>关键词（逗号分隔）</label>
            <input v-model="form.keywords" type="text" class="input" placeholder="如：产假,生育,陕西" />
          </div>
          <div class="form-actions">
            <button type="button" class="btn" @click="closeModal">取消</button>
            <button type="submit" class="btn btn-primary">保存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getFaqs, addFaq, updateFaq, deleteFaq } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const faqsList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const searchKeyword = ref('')
const showAddModal = ref(false)
const isEdit = ref(false)
const editingId = ref(null)

const form = ref({
  question: '',
  answer: '',
  category: '',
  keywords: ''
})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

// 获取FAQ列表
const fetchFaqs = async () => {
  try {
    const res = await getFaqs({
      page: page.value,
      page_size: pageSize.value,
      keyword: searchKeyword.value
    })
    
    if (res.success) {
      faqsList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取FAQ失败:', error)
  }
}

// 搜索
const searchFaqs = () => {
  page.value = 1
  fetchFaqs()
}

// 翻页
const changePage = (delta) => {
  const newPage = page.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchFaqs()
  }
}

// 编辑FAQ
const editFaq = (item) => {
  isEdit.value = true
  editingId.value = item.id
  form.value = {
    question: item.question,
    answer: item.answer,
    category: item.category || '',
    keywords: (item.keywords || []).join(', ')
  }
  showAddModal.value = true
}

// 删除FAQ
const deleteFaqConfirm = async (item) => {
  if (!confirm(`确定要删除FAQ"${item.question}"吗？`)) return
  
  try {
    await deleteFaq(item.id)
    alert('删除成功')
    fetchFaqs()
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败，请重试')
  }
}

// 提交FAQ
const submitFaq = async () => {
  const data = {
    question: form.value.question,
    answer: form.value.answer,
    category: form.value.category,
    keywords: form.value.keywords.split(',').map(k => k.trim()).filter(k => k)
  }
  
  try {
    if (isEdit.value) {
      await updateFaq(editingId.value, data)
      alert('更新成功')
    } else {
      await addFaq(data)
      alert('添加成功')
    }
    closeModal()
    fetchFaqs()
  } catch (error) {
    console.error('保存失败:', error)
    alert('保存失败，请重试')
  }
}

// 关闭弹窗
const closeModal = () => {
  showAddModal.value = false
  isEdit.value = false
  editingId.value = null
  form.value = {
    question: '',
    answer: '',
    category: '',
    keywords: ''
  }
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
  fetchFaqs()
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

.action-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.question-cell {
  max-width: 180px;
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
  margin-right: 10px;
}

.btn-link:hover {
  text-decoration: underline;
}

.btn-link.btn-danger {
  color: #ff4d4f;
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

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .sidebar {
    display: none;
  }
  
  .main-content {
    margin-left: 0;
  }
}</style>