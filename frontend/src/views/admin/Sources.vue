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
        <h1>来源管理</h1>
        <span class="username">{{ username }}</span>
      </div>

      <div class="container">
        <!-- 操作栏 -->
        <div class="card">
          <div class="action-bar">
            <button class="btn btn-primary" @click="showAddModal = true">添加来源</button>
            <select v-model="docTypeFilter" class="input" style="width: 150px;">
              <option value="">全部类型</option>
              <option value="national">国家</option>
              <option value="provincial">省级</option>
              <option value="enterprise">企业</option>
            </select>
            <button class="btn btn-primary" @click="searchSources">筛选</button>
          </div>
        </div>

        <!-- 来源列表 -->
        <div class="card">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>文档标题</th>
                <th>文档类型</th>
                <th>适用地区</th>
                <th>发布日期</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sourcesList" :key="item.id">
                <td>{{ item.id }}</td>
                <td class="title-cell">
                  <a :href="item.url" target="_blank">{{ item.title }}</a>
                </td>
                <td>
                  <span class="tag" :class="getDocTypeClass(item.doc_type)">
                    {{ getDocTypeText(item.doc_type) }}
                  </span>
                </td>
                <td>{{ item.region }}</td>
                <td>{{ item.publish_date }}</td>
                <td>
                  <button class="btn-link" @click="editSource(item)">编辑</button>
                  <button class="btn-link btn-danger" @click="deleteSource(item)">删除</button>
                </td>
              </tr>
              <tr v-if="sourcesList.length === 0">
                <td colspan="6" class="empty">暂无数据</td>
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
        <h3>{{ isEdit ? '编辑来源' : '添加来源' }}</h3>
        <form @submit.prevent="submitSource">
          <div class="form-group">
            <label>文档标题</label>
            <input v-model="form.title" type="text" class="input" required />
          </div>
          <div class="form-group">
            <label>文档链接</label>
            <input v-model="form.url" type="url" class="input" required />
          </div>
          <div class="form-group">
            <label>文档类型</label>
            <select v-model="form.doc_type" class="input" required>
              <option value="national">国家</option>
              <option value="provincial">省级</option>
              <option value="enterprise">企业</option>
            </select>
          </div>
          <div class="form-group">
            <label>适用地区</label>
            <input v-model="form.region" type="text" class="input" placeholder="如：陕西、西安" />
          </div>
          <div class="form-group">
            <label>发布日期</label>
            <input v-model="form.publish_date" type="date" class="input" />
          </div>
          <div class="form-group">
            <label>描述</label>
            <textarea v-model="form.description" class="input" rows="3"></textarea>
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
import { getSources, addSource, updateSource, deleteSource } from '@/api'

const router = useRouter()
const username = ref(localStorage.getItem('admin_username') || '管理员')

const sourcesList = ref([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const docTypeFilter = ref('')
const showAddModal = ref(false)
const isEdit = ref(false)
const editingId = ref(null)

const form = ref({
  title: '',
  url: '',
  doc_type: 'provincial',
  region: '',
  publish_date: '',
  description: ''
})

const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

// 获取来源列表
const fetchSources = async () => {
  try {
    const res = await getSources({
      page: page.value,
      page_size: pageSize.value,
      doc_type: docTypeFilter.value
    })
    
    if (res.success) {
      sourcesList.value = res.data.list || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('获取来源失败:', error)
  }
}

// 筛选
const searchSources = () => {
  page.value = 1
  fetchSources()
}

// 翻页
const changePage = (delta) => {
  const newPage = page.value + delta
  if (newPage >= 1 && newPage <= totalPages.value) {
    page.value = newPage
    fetchSources()
  }
}

// 编辑来源
const editSource = (item) => {
  isEdit.value = true
  editingId.value = item.id
  form.value = {
    title: item.title,
    url: item.url,
    doc_type: item.doc_type,
    region: item.region || '',
    publish_date: item.publish_date || '',
    description: item.description || ''
  }
  showAddModal.value = true
}

// 删除来源
const deleteSourceConfirm = async (item) => {
  if (!confirm(`确定要删除来源"${item.title}"吗？`)) return
  
  try {
    await deleteSource(item.id)
    alert('删除成功')
    fetchSources()
  } catch (error) {
    console.error('删除失败:', error)
    alert('删除失败，请重试')
  }
}

// 提交来源
const submitSource = async () => {
  const data = {
    title: form.value.title,
    url: form.value.url,
    doc_type: form.value.doc_type,
    region: form.value.region,
    publish_date: form.value.publish_date,
    description: form.value.description
  }
  
  try {
    if (isEdit.value) {
      await updateSource(editingId.value, data)
      alert('更新成功')
    } else {
      await addSource(data)
      alert('添加成功')
    }
    closeModal()
    fetchSources()
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
    title: '',
    url: '',
    doc_type: 'provincial',
    region: '',
    publish_date: '',
    description: ''
  }
}

// 获取文档类型文本
const getDocTypeText = (type) => {
  const map = {
    national: '国家',
    provincial: '省级',
    enterprise: '企业'
  }
  return map[type] || type
}

// 获取文档类型样式
const getDocTypeClass = (type) => {
  const map = {
    national: 'tag-danger',
    provincial: 'tag-success',
    enterprise: 'tag-warning'
  }
  return map[type] || ''
}

// 退出登录
const logout = () => {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_id')
  localStorage.removeItem('admin_username')
  router.push('/admin/login')
}

onMounted(() => {
  fetchSources()
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

.title-cell {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.title-cell a {
  color: #1890ff;
  text-decoration: none;
}

.title-cell a:hover {
  text-decoration: underline;
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