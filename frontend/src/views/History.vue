<template>
  <div class="app-page">
    <AppTopbar :tenant="tenant" />

    <main class="fixed-workspace">
      <div class="fixed-workspace-inner">
        <section class="fixed-panel">
          <div class="fixed-panel-header compact">
            <div class="section-title history-title">
              <div>
                <h1>{{ t('history') }}</h1>
                <p class="page-desc">{{ t('historyDesc') }}</p>
              </div>
              <button class="btn danger" :disabled="!items.length" @click="clearAll">{{ t('clear') }}</button>
            </div>
          </div>

          <div class="fixed-panel-body">
            <div v-if="loading" class="loading">{{ t('loading') }}</div>
            <div v-else-if="!items.length" class="empty">{{ t('noHistory') }}</div>
            <div v-else class="history-list">
              <article v-for="item in items" :key="item.id" class="history-card">
                <div class="split-actions">
                  <strong>{{ item.question }}</strong>
                  <span class="tag">{{ item.provider }} · {{ item.response_time || 0 }}ms</span>
                </div>
                <p class="preline">{{ item.answer }}</p>
                <div class="muted">{{ formatTime(item.created_at) }}</div>
              </article>
            </div>
            <div v-if="total > pageSize" class="pagination">
              <button class="btn" :disabled="page === 1" @click="changePage(-1)">{{ t('previousPage') }}</button>
              <span>{{ page }} / {{ totalPages }}</span>
              <button class="btn" :disabled="page >= totalPages" @click="changePage(1)">{{ t('nextPage') }}</button>
            </div>
          </div>
        </section>
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { clearHistory, getHistory } from '@/api'
import { getTenantPublic } from '@/api'
import { useI18n } from '@/i18n'
import AppTopbar from '@/components/AppTopbar.vue'

const { t, formatDateTime } = useI18n()
const tenant = ref({})
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await getHistory({
      user_id: localStorage.getItem('user_id') || 'demo-user',
      page: page.value,
      page_size: pageSize.value
    })
    items.value = res.data?.list || []
    total.value = res.data?.total || 0
  } finally {
    loading.value = false
  }
}

const changePage = (delta) => {
  page.value += delta
  fetchHistory()
}

const clearAll = async () => {
  if (!confirm(t('clearHistoryConfirm'))) return
  await clearHistory(localStorage.getItem('user_id') || 'demo-user')
  items.value = []
  total.value = 0
}

const formatTime = (time) => formatDateTime(time)

const loadTenant = async () => {
  try {
    const res = await getTenantPublic()
    tenant.value = res.data || {}
  } catch (error) {
    tenant.value = { name: t('defaultTenantName'), region: t('defaultRegion') }
  }
}

onMounted(() => {
  loadTenant()
  fetchHistory()
})
</script>

<style scoped>
.history-list {
  display: grid;
  gap: 12px;
  padding-top: 4px;
}

.history-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: var(--surface);
}

.history-card p {
  max-height: 140px;
  overflow: auto;
  color: var(--text);
}

.history-title {
  margin-bottom: 0;
}
</style>
