import { computed, ref } from 'vue'

export const theme = ref(localStorage.getItem('theme') || 'light')

export const applyTheme = () => {
  document.documentElement.dataset.theme = theme.value
  document.documentElement.style.colorScheme = theme.value === 'dark' ? 'dark' : 'light'
}

export const setTheme = (value) => {
  theme.value = value === 'dark' ? 'dark' : 'light'
  localStorage.setItem('theme', theme.value)
  applyTheme()
}

export const toggleTheme = () => {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}

export const useTheme = () => {
  const currentTheme = computed(() => theme.value)
  const isDark = computed(() => theme.value === 'dark')
  return { theme: currentTheme, isDark, setTheme, toggleTheme, applyTheme }
}
