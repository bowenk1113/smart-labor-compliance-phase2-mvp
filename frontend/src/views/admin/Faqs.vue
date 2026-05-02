<template>
  <AdminLayout :title="t('faqTitle')" :subtitle="t('faqSubtitle')">
    <div class="grid">
      <section class="panel">
        <div class="section-title">
          <h2>{{ t('faqList') }}</h2>
          <div class="toolbar">
            <input v-model="keyword" class="input" style="width: 240px" :placeholder="t('searchQuestion')" />
            <button class="btn" @click="queryFaqs">{{ t('query') }}</button>
            <button class="btn primary" @click="openCreateModal">{{ t('addFaq') }}</button>
          </div>
        </div>
        <AppTable :columns="faqColumns" :rows="faqs" :empty-text="t('noFaqs')" :sequence-start="sequenceStart">
          <template #cell-risk_level="{ row }">
            <span :class="['tag', riskClass(row.risk_level)]">{{ riskLabel(row.risk_level) }}</span>
          </template>
          <template #cell-action="{ row }">
            <div class="table-actions">
              <button class="btn" @click="editFaq(row)">{{ t('edit') }}</button>
              <button class="btn danger" @click="removeFaq(row.id)">{{ t('delete') }}</button>
            </div>
          </template>
        </AppTable>
        <AppPagination v-model:page="page" v-model:page-size="pageSize" :total="total" @change="fetchFaqs" />
      </section>
    </div>

    <Teleport to="body">
      <div v-if="faqModalOpen" class="modal-mask">
        <div class="modal faq-modal">
          <div class="section-title">
            <h2>{{ editingId ? t('editFaq') : t('addFaq') }}</h2>
            <button class="btn ghost" type="button" @click="closeFaqModal">×</button>
          </div>
          <form class="form-grid" @submit.prevent="saveFaq">
            <div class="form-group full"><label>{{ t('question') }}</label><input v-model="form.question" class="input" required /></div>
            <div class="form-group"><label>{{ t('category') }}</label><input v-model="form.category" class="input" /></div>
            <div class="form-group"><label>{{ t('risk') }}</label><AppSelect v-model="form.risk_level" :options="riskOptions" /></div>
            <div class="form-group"><label>{{ t('region') }}</label><input v-model="form.region" class="input" /></div>
            <div class="form-group"><label>{{ t('keywords') }}</label><input v-model="keywordText" class="input" :placeholder="t('commaSeparated')" /></div>
            <div class="form-group full"><label>{{ t('answer') }}</label><textarea v-model="form.answer" class="textarea faq-answer" required /></div>
            <div class="form-group full modal-actions">
              <button class="btn" type="button" @click="closeFaqModal">{{ t('cancelEdit') }}</button>
              <button class="btn primary" type="submit">{{ editingId ? t('saveChanges') : t('addFaq') }}</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </AdminLayout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { addFaq, deleteFaq, getFaqs, updateFaq } from '@/api'
import { useI18n } from '@/i18n'
import AppPagination from '@/components/AppPagination.vue'
import AppSelect from '@/components/AppSelect.vue'
import AppTable from '@/components/AppTable.vue'
import AdminLayout from './AdminLayout.vue'

const { t, riskLabel } = useI18n()
const faqs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const keywordText = ref('')
const editingId = ref(null)
const faqModalOpen = ref(false)
const initialForm = () => ({ question: '', answer: '', category: '', region: t('defaultRegion'), risk_level: 'medium', keywords: [] })
const form = ref(initialForm())
const sequenceStart = computed(() => (page.value - 1) * pageSize.value + 1)
const faqColumns = computed(() => [
  { key: 'sequence', label: t('sequence'), width: '64px' },
  { key: 'question', label: t('question'), width: '30%' },
  { key: 'category', label: t('category'), width: '104px' },
  { key: 'risk_level', label: t('risk'), width: '96px' },
  { key: 'answer', label: t('answerSummary'), width: '42%' },
  { key: 'action', label: t('action'), width: '128px' }
])
const riskOptions = computed(() => [
  { value: 'low', label: t('riskLow') },
  { value: 'medium', label: t('riskMedium') },
  { value: 'high', label: t('riskHigh') }
])

const fetchFaqs = async () => {
  const res = await getFaqs({ keyword: keyword.value, page: page.value, page_size: pageSize.value })
  faqs.value = res.data?.list || []
  total.value = res.data?.total || 0
}
const queryFaqs = () => {
  page.value = 1
  fetchFaqs()
}
const openCreateModal = () => {
  resetForm()
  faqModalOpen.value = true
}
const closeFaqModal = () => {
  faqModalOpen.value = false
  resetForm()
}
const saveFaq = async () => {
  const payload = { ...form.value, keywords: keywordText.value.split(/[,，]/).map(v => v.trim()).filter(Boolean) }
  if (editingId.value) await updateFaq(editingId.value, payload)
  else await addFaq(payload)
  resetForm()
  faqModalOpen.value = false
  fetchFaqs()
}
const editFaq = (item) => {
  editingId.value = item.id
  form.value = { question: item.question, answer: item.answer, category: item.category || '', region: item.region || t('defaultRegion'), risk_level: item.risk_level || 'medium', keywords: item.keywords || [] }
  keywordText.value = (item.keywords || []).join(', ')
  faqModalOpen.value = true
}
const removeFaq = async (id) => {
  if (!confirm(t('deleteFaqConfirm'))) return
  await deleteFaq(id)
  fetchFaqs()
}
const resetForm = () => {
  editingId.value = null
  form.value = initialForm()
  keywordText.value = ''
}
const riskClass = (risk) => risk === 'high' ? 'danger' : risk === 'medium' ? 'warning' : 'success'

onMounted(fetchFaqs)
</script>

<style scoped>
.faq-modal {
  width: min(860px, calc(100vw - 32px));
}

.faq-answer {
  min-height: 130px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
