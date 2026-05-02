<template>
  <div ref="rootRef" class="custom-select" :class="{ 'is-open': open, 'is-disabled': disabled }">
    <button
      class="custom-select-trigger"
      type="button"
      :disabled="disabled"
      :aria-expanded="open"
      @click="toggleMenu"
      @keydown="handleTriggerKeydown"
    >
      <span class="custom-select-value" :class="{ 'is-placeholder': !selectedOption }">
        {{ selectedLabel }}
      </span>
      <span class="custom-select-caret">⌄</span>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="menuRef"
        class="custom-select-menu"
        :style="menuStyle"
        role="listbox"
      >
        <button
          v-for="(option, index) in normalizedOptions"
          :key="String(option.value)"
          class="custom-select-option"
          :class="{ 'is-selected': option.value === modelValue, 'is-active': index === activeIndex }"
          type="button"
          role="option"
          :aria-selected="option.value === modelValue"
          :disabled="option.disabled"
          @mousemove="activeIndex = index"
          @click="selectOption(option)"
        >
          <span class="custom-select-check"></span>
          <span class="custom-select-option-label">{{ option.label }}</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: ''
  },
  options: {
    type: Array,
    default: () => []
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const rootRef = ref(null)
const menuRef = ref(null)
const open = ref(false)
const activeIndex = ref(-1)
const menuStyle = ref({})

const normalizedOptions = computed(() => props.options.map((option) => {
  if (typeof option === 'object') return option
  return { value: option, label: String(option) }
}))

const selectedOption = computed(() => normalizedOptions.value.find(option => option.value === props.modelValue))
const selectedLabel = computed(() => selectedOption.value?.label || props.placeholder)

const syncPosition = async () => {
  await nextTick()
  if (!rootRef.value) return
  const rect = rootRef.value.getBoundingClientRect()
  const menuHeight = menuRef.value?.offsetHeight || 260
  const viewportPadding = 8
  const gap = 6
  const downSpace = window.innerHeight - rect.bottom - viewportPadding
  const upSpace = rect.top - viewportPadding
  const openUpward = downSpace < 140 && upSpace > downSpace
  const maxHeight = Math.max(120, Math.min(280, openUpward ? upSpace - gap : downSpace - gap))
  const top = openUpward
    ? Math.max(viewportPadding, rect.top - Math.min(menuHeight, maxHeight) - gap)
    : rect.bottom + gap
  const left = Math.min(Math.max(viewportPadding, rect.left), window.innerWidth - rect.width - viewportPadding)

  menuStyle.value = {
    position: 'fixed',
    top: `${top}px`,
    left: `${left}px`,
    width: `${rect.width}px`,
    maxHeight: `${maxHeight}px`,
    zIndex: 1000
  }
}

const openMenu = async () => {
  if (props.disabled) return
  activeIndex.value = Math.max(0, normalizedOptions.value.findIndex(option => option.value === props.modelValue))
  open.value = true
  await syncPosition()
}

const closeMenu = () => {
  open.value = false
}

const toggleMenu = () => {
  if (open.value) closeMenu()
  else openMenu()
}

const selectOption = (option) => {
  if (!option) return
  if (option.disabled) return
  emit('update:modelValue', option.value)
  emit('change', option.value, option)
  closeMenu()
}

const moveActive = (step) => {
  const enabled = normalizedOptions.value
    .map((option, index) => ({ option, index }))
    .filter(item => !item.option.disabled)
  if (!enabled.length) return
  const current = enabled.findIndex(item => item.index === activeIndex.value)
  const next = current === -1 ? 0 : (current + step + enabled.length) % enabled.length
  activeIndex.value = enabled[next].index
}

const handleTriggerKeydown = (event) => {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!open.value) openMenu()
    else moveActive(event.key === 'ArrowDown' ? 1 : -1)
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (!open.value) openMenu()
    else if (activeIndex.value >= 0) selectOption(normalizedOptions.value[activeIndex.value])
  }
  if (event.key === 'Escape') closeMenu()
}

const handleDocumentPointerDown = (event) => {
  const target = event.target
  if (rootRef.value?.contains(target) || menuRef.value?.contains(target)) return
  closeMenu()
}

watch(open, (value) => {
  if (value) {
    document.addEventListener('pointerdown', handleDocumentPointerDown)
    window.addEventListener('resize', syncPosition)
    window.addEventListener('scroll', syncPosition, true)
  } else {
    document.removeEventListener('pointerdown', handleDocumentPointerDown)
    window.removeEventListener('resize', syncPosition)
    window.removeEventListener('scroll', syncPosition, true)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  window.removeEventListener('resize', syncPosition)
  window.removeEventListener('scroll', syncPosition, true)
})
</script>
