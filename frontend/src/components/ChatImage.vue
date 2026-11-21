<script setup lang="ts">
import { ref, watch } from 'vue'
import { chatApi } from '@/api/chat'

const props = defineProps<{ conversationId: number; messageId: number }>()
const source = ref('')
const failed = ref(false)

watch(() => [props.conversationId, props.messageId] as const, async ([conversationId, messageId], _, onCleanup) => {
  const controller = new AbortController()
  let imageUrl = ''
  onCleanup(() => {
    controller.abort()
    if (imageUrl) URL.revokeObjectURL(imageUrl)
  })
  source.value = ''
  failed.value = false
  try {
    const { data } = await chatApi.getMessageImage(conversationId, messageId, controller.signal)
    if (!controller.signal.aborted) {
      imageUrl = URL.createObjectURL(data)
      source.value = imageUrl
    }
  } catch {
    if (!controller.signal.aborted) failed.value = true
  }
}, { immediate: true })
</script>

<template>
  <a v-if="source" :href="source" target="_blank" rel="noopener" aria-label="Open attached image">
    <img :src="source" alt="Image attached to this message" class="max-h-64 max-w-full rounded-lg object-contain" />
  </a>
  <span v-else class="text-sm">{{ failed ? 'Image unavailable.' : 'Loading image…' }}</span>
</template>
