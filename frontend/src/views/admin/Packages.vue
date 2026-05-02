<template>
  <AdminLayout :title="t('packagesTitle')" :subtitle="t('packagesSubtitle')">
    <section class="panel">
      <div class="section-title">
        <h2>{{ t('packageList') }}</h2>
        <button class="btn" @click="fetchPackages">{{ t('refresh') }}</button>
      </div>
      <AppTable :columns="packageColumns" :rows="packages" :empty-text="t('noPackages')" :sequence-start="sequenceStart">
        <template #cell-status="{ row }">
          <span :class="['tag', row.status === 'active' ? 'success' : 'warning']">{{ statusLabel(row.status) || row.status }}</span>
        </template>
        <template #cell-action="{ row }">
          <div class="table-actions">
            <button class="btn" @click="toggle(row)">{{ row.status === 'active' ? t('disable') : t('enable') }}</button>
          </div>
        </template>
      </AppTable>
      <AppPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="fetchPackages" />
    </section>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getKnowledgePackages, updatePackageStatus } from '@/api'
import { useI18n } from '@/i18n'
import AppPagination from '@/components/AppPagination.vue'
import AppTable from '@/components/AppTable.vue'
import AdminLayout from './AdminLayout.vue'

const { t, statusLabel } = useI18n()
const packages = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const sequenceStart = computed(() => (page.value - 1) * pageSize.value + 1)
const packageColumns = computed(() => [
  { key: 'sequence', label: t('sequence'), width: '64px' },
  { key: 'tenant_name', label: t('tenant'), width: '27%' },
  { key: 'name', label: t('name'), width: '29%' },
  { key: 'region', label: t('region'), width: '88px' },
  { key: 'version', label: t('version'), width: '80px' },
  { key: 'faq_count', label: 'FAQ', width: '64px' },
  { key: 'doc_count', label: t('sourceCount'), width: '80px' },
  { key: 'status', label: t('status'), width: '96px' },
  { key: 'action', label: t('action'), width: '88px' }
])
const fetchPackages = async () => {
  const res = await getKnowledgePackages({ page: page.value, page_size: pageSize.value })
  packages.value = res.data?.list || []
  total.value = res.data?.total || 0
}
const toggle = async (item) => {
  await updatePackageStatus(item.id, { status: item.status === 'active' ? 'disabled' : 'active' })
  fetchPackages()
}
onMounted(fetchPackages)
</script>
