<template>
  <div class="home">
    <!-- 头部导航 -->
    <header class="header">
      <div class="header-content">
        <h1 class="logo">企业用工与社保合规智能平台</h1>
        <nav class="nav">
          <router-link to="/">问答首页</router-link>
          <router-link to="/history">历史记录</router-link>
          <router-link to="/admin">管理后台</router-link>
        </nav>
      </div>
    </header>

    <div class="container">
      <!-- 问答输入区 -->
      <div class="card chat-card">
        <h2 class="subtitle">智能问答</h2>
        <div class="chat-input-area">
          <textarea
            v-model="question"
            class="chat-input"
            placeholder="请输入您的问题，如：陕西产假多少天？"
            @keydown.enter.ctrl="submitQuestion"
            rows="3"
          ></textarea>
          <button 
            class="btn btn-primary submit-btn" 
            @click="submitQuestion"
            :disabled="loading || !question.trim()"
          >
            {{ loading ? '回答中...' : '提交问题' }}
          </button>
        </div>
      </div>

      <!-- 推荐问题区 -->
      <div class="card">
        <h2 class="subtitle">推荐问题</h2>
        <div class="recommended-questions">
          <button
            v-for="item in recommendedQuestions"
            :key="item.id"
            class="question-tag"
            @click="fillQuestion(item.question)"
          >
            {{ item.question }}
          </button>
        </div>
      </div>

      <!-- 回答结果区 -->
      <div v-if="answer" class="card">
        <h2 class="subtitle">回答结果</h2>
        <div class="answer-content">
          <div class="answer-text" v-html="formatAnswer(answer)"></div>
        </div>
        
        <!-- 来源说明区 -->
        <div v-if="sources && sources.length > 0" class="sources-section">
          <h3 class="section-title">来源说明</h3>
          <ul class="sources-list">
            <li v-for="(source, index) in sources" :key="index">
              <a :href="source.url" target="_blank">{{ source.title }}</a>
              <span class="source-date">{{ source.date }}</span>
            </li>
          </ul>
        </div>

        <!-- 办事路径卡片区 -->
        <div v-if="relatedTasks && relatedTasks.length > 0" class="tasks-section">
          <h3 class="section-title">办事路径</h3>
          <div class="tasks-grid">
            <div v-for="(task, index) in relatedTasks" :key="index" class="task-card">
              <h4>{{ task.title }}</h4>
              <p>{{ task.path }}</p>
              <p v-if="task.contact" class="task-contact">{{ task.contact }}</p>
            </div>
          </div>
        </div>

        <!-- 结果反馈模块 -->
        <div class="feedback-section">
          <span class="feedback-label">这份回答对您有帮助吗？</span>
          <button class="btn btn-success" @click="handleFeedback(true)" :disabled="feedbackSubmitted">
            有帮助
          </button>
          <button class="btn btn-danger" @click="handleFeedback(false)" :disabled="feedbackSubmitted">
            无帮助
          </button>
        </div>

        <!-- 无帮助反馈备注 -->
        <div v-if="showFeedbackRemark" class="feedback-remark">
          <textarea
            v-model="feedbackRemark"
            class="input"
            placeholder="请告诉我们哪里需要改进..."
            rows="2"
          ></textarea>
          <button class="btn btn-primary" @click="submitFeedback(false)">提交反馈</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { chat, getRecommendedQuestions, submitFeedback } from '@/api'

const question = ref('')
const loading = ref(false)
const answer = ref('')
const sources = ref([])
const relatedTasks = ref([])
const recommendedQuestions = ref([])
const feedbackSubmitted = ref(false)
const showFeedbackRemark = ref(false)
const feedbackRemark = ref('')
const currentQuestionId = ref(null)

// 获取推荐问题
onMounted(async () => {
  try {
    const res = await getRecommendedQuestions()
    if (res.success) {
      recommendedQuestions.value = res.data || []
    }
  } catch (error) {
    console.error('获取推荐问题失败:', error)
    // 使用默认推荐问题
    recommendedQuestions.value = [
      { id: 1, question: '陕西产假多少天' },
      { id: 2, question: '西安劳动仲裁去哪里' },
      { id: 3, question: '居民医保断缴后怎么处理' },
      { id: 4, question: '试用期工资标准' },
      { id: 5, question: '加班费计算方式' }
    ]
  }
})

// 填充问题
const fillQuestion = (q) => {
  question.value = q
}

// 提交问题
const submitQuestion = async () => {
  if (!question.value.trim() || loading.value) return
  
  loading.value = true
  feedbackSubmitted.value = false
  showFeedbackRemark.value = false
  feedbackRemark.value = ''
  
  try {
    const res = await chat({
      question: question.value,
      user_id: localStorage.getItem('user_id') || 'anonymous'
    })
    
    if (res.success) {
      answer.value = res.data.answer
      sources.value = res.data.sources || []
      relatedTasks.value = res.data.related_tasks || []
      currentQuestionId.value = res.data.question_id
    } else {
      answer.value = '抱歉，系统出现了问题，请稍后再试。'
    }
  } catch (error) {
    console.error('问答失败:', error)
    answer.value = '抱歉，网络连接出现问题，请检查网络后重试。'
  } finally {
    loading.value = false
  }
}

// 格式化回答（支持富文本）
const formatAnswer = (text) => {
  // 简单处理换行
  return text.replace(/\n/g, '<br>')
}

// 提交反馈
const handleFeedback = async (isHelpful) => {
  if (!currentQuestionId.value || feedbackSubmitted.value) return
  
  try {
    await submitFeedback({
      question_id: currentQuestionId.value,
      is_helpful: isHelpful,
      remark: isHelpful ? '' : feedbackRemark.value,
      user_id: localStorage.getItem('user_id') || 'anonymous'
    })
    feedbackSubmitted.value = true
    showFeedbackRemark.value = false
    alert('感谢您的反馈！')
  } catch (error) {
    console.error('提交反馈失败:', error)
    alert('反馈提交失败，请重试')
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
}

.header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  padding: 15px 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 20px;
  color: #1890ff;
  margin: 0;
}

.nav a {
  margin-left: 20px;
  color: #666;
  text-decoration: none;
}

.nav a:hover,
.nav a.router-link-active {
  color: #1890ff;
}

.chat-card {
  margin-top: 20px;
}

.chat-input-area {
  display: flex;
  gap: 15px;
  flex-direction: column;
}

.chat-input {
  width: 100%;
  padding: 15px;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  min-height: 80px;
}

.chat-input:focus {
  outline: none;
  border-color: #40a9ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.submit-btn {
  align-self: flex-end;
}

.recommended-questions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.question-tag {
  padding: 8px 16px;
  background: #f0f5ff;
  border: 1px solid #adc6ff;
  border-radius: 20px;
  color: #1890ff;
  cursor: pointer;
  transition: all 0.3s;
}

.question-tag:hover {
  background: #e6f7ff;
  border-color: #40a9ff;
}

.answer-content {
  padding: 20px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.answer-text {
  font-size: 15px;
  line-height: 1.8;
  color: #333;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 20px 0 15px;
  color: #333;
}

.sources-list {
  list-style: none;
  padding: 0;
}

.sources-list li {
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.sources-list a {
  color: #1890ff;
  text-decoration: none;
}

.sources-list a:hover {
  text-decoration: underline;
}

.source-date {
  margin-left: 10px;
  color: #999;
  font-size: 12px;
}

.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 15px;
}

.task-card {
  padding: 15px;
  background: #f0f5ff;
  border-radius: 8px;
  border-left: 4px solid #1890ff;
}

.task-card h4 {
  margin: 0 0 10px;
  color: #1890ff;
}

.task-card p {
  margin: 5px 0;
  font-size: 13px;
  color: #666;
}

.task-contact {
  color: #333 !important;
  font-weight: 500;
}

.feedback-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 15px;
}

.feedback-label {
  color: #666;
}

.feedback-remark {
  margin-top: 15px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 10px;
  }
  
  .nav a {
    margin: 0 10px;
  }
  
  .tasks-grid {
    grid-template-columns: 1fr;
  }
}</style>