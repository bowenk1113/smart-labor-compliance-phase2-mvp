<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="login-title">管理后台登录</h1>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="form.username" 
            type="text" 
            class="input" 
            placeholder="请输入用户名"
            required
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="form.password" 
            type="password" 
            class="input" 
            placeholder="请输入密码"
            required
          />
        </div>
        <div v-if="error" class="error-message">{{ error }}</div>
        <button type="submit" class="btn btn-primary login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
      <div class="login-tip">
        <p>默认管理员账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminLogin } from '@/api'

const router = useRouter()

const form = ref({
  username: '',
  password: ''
})
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    error.value = '请输入用户名和密码'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    const res = await adminLogin(form.value)
    
    if (res.success) {
      localStorage.setItem('admin_token', res.data.token)
      localStorage.setItem('admin_id', res.data.admin_id)
      localStorage.setItem('admin_username', res.data.username)
      router.push('/admin')
    } else {
      error.value = res.error || '登录失败'
    }
  } catch (err) {
    error.value = '网络错误，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

.login-title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  font-size: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #666;
  font-weight: 500;
}

.login-btn {
  width: 100%;
  padding: 12px;
  font-size: 16px;
}

.error-message {
  color: #ff4d4f;
  margin-bottom: 15px;
  text-align: center;
}

.login-tip {
  margin-top: 20px;
  text-align: center;
  color: #999;
  font-size: 12px;
}
</style>