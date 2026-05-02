<template>
  <div class="app-page">
    <AppTopbar />
    <main class="login-page">
      <div class="login-card">
      <div class="section-title login-title">
        <div>
          <h1>{{ t('login') }}</h1>
          <p class="page-desc">{{ t('loginSubtitle') }}</p>
        </div>
      </div>
      <form class="login-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label>{{ t('username') }}</label>
          <input v-model="form.username" class="input" autocomplete="username" required />
        </div>
        <div class="form-group">
          <label>{{ t('password') }}</label>
          <input v-model="form.password" class="input" type="password" autocomplete="current-password" required />
        </div>
        <div class="form-group">
          <label>{{ t('tenantCode') }}</label>
          <input v-model="form.tenant_code" class="input" :placeholder="t('tenantLoginPlaceholder')" />
        </div>
        <div v-if="error" class="tag danger">{{ error }}</div>
        <button class="btn primary" type="submit" :disabled="loading">{{ loading ? t('loggingIn') : t('login') }}</button>
      </form>
      <div class="login-tip">
        <strong>{{ t('initialSuperAdmin') }}</strong>
        <span>admin / Admin@123456</span>
        <strong>{{ t('demoTenantAdmin') }}</strong>
        <span>tenant_admin / Tenant@123456 / demo-sx</span>
      </div>
    </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { adminLogin, setTenantCode } from '@/api'
import { useI18n } from '@/i18n'
import AppTopbar from '@/components/AppTopbar.vue'

const router = useRouter()
const { t } = useI18n()
const loading = ref(false)
const error = ref('')
const form = ref({
  username: 'admin',
  password: 'Admin@123456',
  tenant_code: ''
})

const handleLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await adminLogin(form.value)
    const data = res
    localStorage.setItem('admin_token', data.access_token)
    localStorage.setItem('admin_id', data.admin_id)
    localStorage.setItem('admin_username', data.username)
    localStorage.setItem('admin_role', data.role)
    localStorage.setItem('admin_role_label', data.role_label)
    localStorage.setItem('admin_permissions', JSON.stringify(data.permissions || []))
    localStorage.setItem('admin_tenant_id', data.tenant_id || '')
    localStorage.setItem('admin_tenant_name', data.tenant_name || '')
    if (data.tenant_code) setTenantCode(data.tenant_code)
    router.push('/admin')
  } catch (err) {
    error.value = err.response?.data?.message || err.response?.data?.detail || t('loginFailed')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  overflow: auto;
}

.login-card {
  width: min(440px, 100%);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 24px;
  box-shadow: var(--shadow);
}

.login-title {
  margin-bottom: 0;
}

.login-form,
.login-tip {
  display: grid;
  gap: 12px;
  margin-top: 22px;
}

.login-tip {
  padding: 14px;
  background: var(--surface-soft);
  border-radius: 8px;
  color: var(--muted);
}
</style>
