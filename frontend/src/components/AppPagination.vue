<template>
  <div v-if="total > 0" class="pagination">
    <div class="pagination-size">
      <span class="pagination-total">{{ totalText }}</span>
      <span class="pagination-label">{{ t('pageSize') }}</span>
      <AppSelect
        class="pagination-select"
        :model-value="pageSize"
        :options="normalizedPageSizeOptions"
        @update:model-value="changePageSize"
      />
    </div>
    <div class="pagination-nav">
      <button class="btn" :disabled="page <= 1" @click="goTo(page - 1)">{{ t('previousPage') }}</button>
      <span class="pagination-info">{{ page }} / {{ totalPages }}</span>
      <button class="btn" :disabled="page >= totalPages" @click="goTo(page + 1)">{{ t('nextPage') }}</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import AppSelect from '@/components/AppSelect.vue'

const props = defineProps({
  page: {
    type: Number,
    required: true
  },
  pageSize: {
    type: Number,
    required: true
  },
  total: {
    type: Number,
    default: 0
  },
  pageSizeOptions: {
    type: Array,
    default: () => [10, 20, 50, 100]
  }
})

const emit = defineEmits(['update:page', 'update:pageSize', 'change'])
const { t } = useI18n()

const totalPages = computed(() => Math.max(1, Math.ceil((props.total || 0) / Math.max(1, props.pageSize))))
const totalText = computed(() => t('paginationTotal').replace('{total}', props.total || 0))
const normalizedPageSizeOptions = computed(() => props.pageSizeOptions.map(value => ({
  value,
  label: `${value} ${t('itemsPerPage')}`
})))

const goTo = (nextPage) => {
  const normalized = Math.min(Math.max(1, nextPage), totalPages.value)
  if (normalized === props.page) return
  emit('update:page', normalized)
  emit('change', normalized, props.pageSize)
}

const changePageSize = (nextPageSize) => {
  const normalized = Number(nextPageSize) || props.pageSize
  if (normalized === props.pageSize && props.page === 1) return
  emit('update:pageSize', normalized)
  emit('update:page', 1)
  emit('change', 1, normalized)
}
</script>
