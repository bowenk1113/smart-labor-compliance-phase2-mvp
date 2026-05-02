<template>
  <div class="app-page">
    <AppTopbar :tenant="tenant" />

    <main class="split-workspace">
      <section class="split-workspace-inner">
        <div class="split-pane split-pane-left">
          <div class="split-pane-content">
            <div class="panel">
          <div class="section-title">
            <div>
              <h1>{{ t('chat') }}</h1>
              <p class="page-desc">{{ t('homeIntro') }}</p>
            </div>
            <span class="tag">{{ t('tenant') }}: {{ tenantCode }}</span>
          </div>

          <textarea
            v-model="question"
            class="textarea"
            :placeholder="t('askPlaceholder')"
            @keydown.ctrl.enter="submitQuestion"
          />
          <div class="split-actions" style="margin-top: 12px">
            <div class="toolbar">
              <input v-model="tenantCode" class="input" style="width: 150px" :placeholder="t('tenantCode')" @change="persistTenant" />
              <span class="muted">Ctrl + Enter</span>
            </div>
            <button class="btn primary" :disabled="loading || !question.trim()" @click="submitQuestion">
              {{ loading ? t('answering') : t('ask') }}
            </button>
          </div>

          <div v-if="answer" class="answer-block">
            <div class="section-title">
              <h2>{{ t('answer') }}</h2>
              <div class="toolbar">
                <span :class="['tag', riskClass]">{{ t('risk') }}: {{ riskText }}</span>
                <span class="tag">{{ t('provider') }}: {{ provider }}</span>
              </div>
            </div>
            <div class="answer-text preline">{{ answer }}</div>

            <div v-if="sources.length" class="subsection">
              <h3>{{ t('sources') }}</h3>
              <div class="source-list">
                <a v-for="source in sources" :key="source.title" :href="source.url || '#'" target="_blank" rel="noreferrer" class="source-item">
                  <strong>{{ source.title }}</strong>
                  <span>{{ source.snippet }}</span>
                </a>
              </div>
            </div>

            <div v-if="tasks.length" class="subsection">
              <h3>{{ t('tasks') }}</h3>
              <div v-for="task in tasks" :key="task.title" class="task-card">
                <strong>{{ task.title }}</strong>
                <ol>
                  <li v-for="step in task.steps" :key="step">{{ step }}</li>
                </ol>
              </div>
            </div>

            <div v-if="suggestions.length" class="subsection">
              <h3>{{ t('followUp') }}</h3>
              <div class="toolbar">
                <button v-for="item in suggestions" :key="item" class="chip" @click="fillQuestion(item)">{{ item }}</button>
              </div>
            </div>

            <div class="feedback-row">
              <span>{{ t('feedback') }}</span>
              <button class="btn" :disabled="feedbackSubmitted" @click="sendFeedback(true)">{{ t('helpful') }}</button>
              <button class="btn danger" :disabled="feedbackSubmitted" @click="showRemark = true">{{ t('notHelpful') }}</button>
            </div>
            <div v-if="showRemark" class="feedback-form">
              <textarea v-model="feedbackRemark" class="textarea" :placeholder="t('feedbackPlaceholder')" />
              <button class="btn primary" @click="sendFeedback(false)">{{ t('submitFeedback') }}</button>
            </div>
          </div>
        </div>
          </div>
        </div>

        <aside class="split-pane split-pane-right">
          <div class="split-pane-content">
            <div class="card">
            <div class="section-title">
              <h2>{{ t('recommendedQuestions') }}</h2>
              <button class="btn" @click="loadRecommended">{{ t('refresh') }}</button>
            </div>
            <div class="recommend-list">
              <button v-for="item in recommended" :key="item.id || item.question" class="recommend-item" @click="fillQuestion(item.question)">
                <strong>{{ item.question }}</strong>
                <span>{{ item.category }} · {{ riskLabel(item.risk_level) }}</span>
              </button>
            </div>
          </div>
            <div class="card">
            <h2>{{ t('dataSecurity') }}</h2>
            <p class="page-desc">{{ t('dataSecurityText') }}</p>
          </div>
          </div>
        </aside>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { chat, getRecommendedQuestions, getTenantCode, getTenantPublic, setTenantCode, submitFeedback } from '@/api'
import { useI18n } from '@/i18n'
import AppTopbar from '@/components/AppTopbar.vue'

const { t, locale, riskLabel } = useI18n()
const tenantCode = ref(getTenantCode())
const tenant = ref({})
const question = ref('')
const answer = ref('')
const sources = ref([])
const tasks = ref([])
const suggestions = ref([])
const provider = ref('')
const riskLevel = ref('medium')
const questionId = ref(null)
const recommended = ref([])
const loading = ref(false)
const feedbackSubmitted = ref(false)
const showRemark = ref(false)
const feedbackRemark = ref('')
const answeredQuestion = ref('')

const riskText = computed(() => riskLabel(riskLevel.value))
const riskClass = computed(() => riskLevel.value === 'high' ? 'danger' : riskLevel.value === 'medium' ? 'warning' : 'success')

const clearAnswer = () => {
  answer.value = ''
  sources.value = []
  tasks.value = []
  suggestions.value = []
  provider.value = ''
  riskLevel.value = 'medium'
  questionId.value = null
  feedbackSubmitted.value = false
  showRemark.value = false
  feedbackRemark.value = ''
}

const persistTenant = () => {
  setTenantCode(tenantCode.value)
  loadTenant()
  loadRecommended()
}

const loadTenant = async () => {
  try {
    const res = await getTenantPublic()
    tenant.value = res.data || {}
  } catch (error) {
    tenant.value = { name: t('defaultTenantName'), region: t('defaultRegion') }
  }
}

const loadRecommended = async () => {
  try {
    const res = await getRecommendedQuestions()
    recommended.value = res.data || []
  } catch (error) {
    recommended.value = [
      { question: '陕西产假多少天？', category: '假期', risk_level: 'medium' },
      { question: '试用期工资可以低于最低工资吗？', category: '工资', risk_level: 'high' }
    ]
  }
}

const fillQuestion = (value) => {
  question.value = value
}

const submitQuestion = async () => {
  if (!question.value.trim() || loading.value) return
  const submittedQuestion = question.value
  loading.value = true
  feedbackSubmitted.value = false
  showRemark.value = false
  feedbackRemark.value = ''
  try {
    const res = await chat({
      question: question.value,
      user_id: localStorage.getItem('user_id') || 'demo-user',
      tenant_code: tenantCode.value,
      language: locale.value
    })
    const data = res.data || {}
    answer.value = data.answer || ''
    sources.value = data.sources || []
    tasks.value = data.related_tasks || []
    suggestions.value = data.suggestions || []
    provider.value = data.provider || 'local_faq'
    riskLevel.value = data.risk_level || 'medium'
    questionId.value = data.question_id
    answeredQuestion.value = submittedQuestion
  } catch (error) {
    answer.value = error.response?.data?.message || t('systemError')
    sources.value = []
    tasks.value = []
    answeredQuestion.value = submittedQuestion
  } finally {
    loading.value = false
  }
}

const sendFeedback = async (isHelpful) => {
  if (!questionId.value || feedbackSubmitted.value) return
  await submitFeedback({
    tenant_code: tenantCode.value,
    question_id: questionId.value,
    user_id: localStorage.getItem('user_id') || 'demo-user',
    is_helpful: isHelpful,
    remark: isHelpful ? '' : feedbackRemark.value
  })
  feedbackSubmitted.value = true
  showRemark.value = false
}

onMounted(() => {
  loadTenant()
  loadRecommended()
})

watch(question, (value) => {
  if (loading.value || !answeredQuestion.value) return
  if (value !== answeredQuestion.value) {
    clearAnswer()
    answeredQuestion.value = ''
  }
})
</script>

<style scoped>
.answer-block {
  margin-top: 18px;
  border-top: 1px solid var(--line);
  padding-top: 18px;
}

.answer-text {
  padding: 16px;
  background: var(--surface-soft);
  border: 1px solid var(--line);
  border-radius: 8px;
}

.subsection {
  margin-top: 18px;
}

.source-list,
.recommend-list {
  display: grid;
  gap: 10px;
}

.source-item,
.recommend-item {
  display: grid;
  gap: 4px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface);
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  color: var(--text);
}

.source-item span,
.recommend-item span {
  color: var(--muted);
  font-size: 13px;
}

.task-card {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--surface-soft);
}

.feedback-row {
  margin-top: 18px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.feedback-form {
  margin-top: 12px;
  display: grid;
  gap: 10px;
}
</style>
