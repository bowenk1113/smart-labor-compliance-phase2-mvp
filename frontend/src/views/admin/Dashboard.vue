<template>
  <AdminLayout :title="t('dashboardTitle')" :subtitle="t('dashboardSubtitle')">
    <div class="grid">
      <div class="stat-grid">
        <div class="stat"><span>{{ t('totalQuestions') }}</span><strong>{{ stats.total_questions || 0 }}</strong></div>
        <div class="stat"><span>{{ t('todayQuestions') }}</span><strong>{{ stats.today_questions || 0 }}</strong></div>
        <div class="stat"><span>{{ t('helpfulRate') }}</span><strong>{{ stats.helpful_rate || 0 }}%</strong></div>
        <div class="stat"><span>{{ t('avgResponse') }}</span><strong>{{ stats.avg_response_time || 0 }}ms</strong></div>
      </div>

      <div class="dashboard-grid">
        <section class="panel">
          <div class="section-title">
            <h2>{{ t('serviceStatus') }}</h2>
            <button class="btn" @click="fetchStats">{{ t('refresh') }}</button>
          </div>
          <div class="grid">
            <div class="service-row">
              <strong>MySQL Docker</strong>
              <span class="tag success">connected</span>
            </div>
            <div v-for="(service, key) in services" :key="key" class="service-row">
              <div>
                <strong>{{ service.name }}</strong>
                <div class="muted">{{ service.url }}</div>
              </div>
              <span :class="['tag', service.online ? 'success' : 'danger']">
                {{ service.online ? 'online' : 'offline' }}
              </span>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="section-title">
            <h2>{{ t('topQuestions') }}</h2>
          </div>
          <AppTable
            :columns="topQuestionColumns"
            :rows="topQuestionRows"
            :empty-text="t('noData')"
            :row-key="row => row.question"
            dense
          />
        </section>
      </div>
    </div>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getStatistics } from '@/api'
import { useI18n } from '@/i18n'
import AppTable from '@/components/AppTable.vue'
import AdminLayout from './AdminLayout.vue'

const { t } = useI18n()
const stats = ref({})
const services = ref({})
const topQuestionRows = computed(() => (stats.value.top_questions || []).map((item, index) => ({
  ...item,
  rank: index + 1
})))
const topQuestionColumns = computed(() => [
  { key: 'rank', label: '', width: '44px', align: 'center' },
  { key: 'question', label: t('question') },
  { key: 'count', label: '', width: '48px', align: 'center' }
])

const fetchStats = async () => {
  const res = await getStatistics()
  stats.value = res.data || {}
  services.value = stats.value.services || {}
}

onMounted(fetchStats)
</script>

<style scoped>
.service-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 3fr) minmax(360px, 2fr);
  gap: 16px;
  align-items: stretch;
}

@media (max-width: 1180px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
