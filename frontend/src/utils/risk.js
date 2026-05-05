export const normalizeRiskLevel = (value) => {
  const normalized = String(value || '').trim().toLowerCase().replace(/^[*：:，,。.;；\s]+|[*：:，,。.;；\s]+$/g, '')
  const mapping = {
    高: 'high',
    高风险: 'high',
    high: 'high',
    中: 'medium',
    中风险: 'medium',
    中等: 'medium',
    中等风险: 'medium',
    medium: 'medium',
    低: 'low',
    低风险: 'low',
    low: 'low'
  }
  return mapping[normalized] || ''
}

export const riskFromAnswer = (value) => {
  const text = String(value || '')
  const patterns = [
    /风险等级\s*[:：]\s*(?:\*\*)?\s*(高风险|中风险|低风险|高|中|低|high|medium|low)/i,
    /初步风险等级\s*为\s*[:：]?\s*(?:\*\*)?\s*(高风险|中风险|低风险|高|中|低|high|medium|low)/i
  ]
  for (const pattern of patterns) {
    const match = text.match(pattern)
    const risk = normalizeRiskLevel(match?.[1])
    if (risk) return risk
  }
  return ''
}

export const displayedRiskLevel = (item) => {
  return riskFromAnswer(item?.answer) || normalizeRiskLevel(item?.risk_level ?? item?.riskLevel) || 'medium'
}
