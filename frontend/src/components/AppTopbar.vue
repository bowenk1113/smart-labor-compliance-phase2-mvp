<template>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="brand">
        <div class="brand-mark">S</div>
        <div>
          <h1 class="brand-title">{{ t('appName') }}</h1>
          <div class="brand-subtitle">{{ subtitle }}</div>
        </div>
      </div>
      <nav class="nav">
        <router-link to="/">{{ t('chat') }}</router-link>
        <router-link to="/history">{{ t('history') }}</router-link>
        <router-link to="/admin">{{ t('admin') }}</router-link>
        <button class="theme-toggle" type="button" :title="isDark ? t('switchToLight') : t('switchToDark')" @click="toggleTheme">
          <span class="theme-toggle-knob">{{ isDark ? 'D' : 'L' }}</span>
          <span>{{ isDark ? t('darkMode') : t('lightMode') }}</span>
        </button>
        <AppSelect
          class="locale-select"
          :model-value="locale"
          :options="localeOptions"
          @update:model-value="setLocale"
        />
      </nav>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '@/i18n'
import { useTheme } from '@/theme'
import AppSelect from '@/components/AppSelect.vue'

const props = defineProps({
  tenant: {
    type: Object,
    default: () => ({})
  }
})

const { t, locale, setLocale } = useI18n()
const { isDark, toggleTheme } = useTheme()
const localeOptions = [
  { value: 'zh-CN', label: '中文' },
  { value: 'en', label: 'English' }
]
const subtitle = computed(() => {
  const name = props.tenant?.name || t('defaultTenantName')
  const region = props.tenant?.region || t('defaultRegion')
  return `${name} · ${region}`
})
</script>
