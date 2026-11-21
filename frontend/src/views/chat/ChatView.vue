<script setup lang="ts">
import { ref, computed, onBeforeUnmount, onMounted, nextTick, watch } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import ChatImage from '@/components/ChatImage.vue'
import { useChatStore } from '@/stores/chat'
import { useAuthStore } from '@/stores/auth'
import type { ConversationResponse, ChatMessageResponse } from '@/api/chat'
import {
  MessageSquare,
  Send,
  User,
  Stethoscope,
  ShieldAlert,
  Wifi,
  WifiOff,
  RefreshCw,
  Search,
  Check,
  CheckCheck,
  Plus,
  Loader2,
  Clock,
  AlertCircle,
  ImagePlus,
  Trash2,
  X,
} from 'lucide-vue-next'

const chatStore = useChatStore()
const authStore = useAuthStore()

const messageText = ref<string>('')
const searchQuery = ref<string>('')
const messageContainer = ref<HTMLDivElement | null>(null)
const isSending = ref<boolean>(false)
const imageInput = ref<HTMLInputElement | null>(null)
const selectedImage = ref<File | null>(null)
const imageError = ref('')
const deleteTarget = ref<ConversationResponse | null>(null)
const isDeleting = ref(false)
let syncTimer: ReturnType<typeof setInterval> | undefined

onMounted(async () => {
  chatStore.connectWebSocket()
  syncTimer = setInterval(() => { void chatStore.syncChat() }, 5000)
  await chatStore.fetchConversations().catch(() => {})

  if (chatStore.conversations.length > 0 && chatStore.activeConversationId === null) {
    const firstId = chatStore.conversations[0]?.id
    if (firstId) {
      await chatStore.selectConversation(firstId).catch(() => {})
    }
  }

  scrollToBottom()
})

onBeforeUnmount(() => clearInterval(syncTimer))

watch(
  () => chatStore.activeMessages.length,
  () => {
    nextTick(() => {
      scrollToBottom()
    })
  },
)

watch(
  () => chatStore.activeConversationId,
  () => {
    messageText.value = ''
    selectedImage.value = null
    imageError.value = ''
    nextTick(() => {
      scrollToBottom()
    })
  },
)

const filteredConversations = computed<ConversationResponse[]>(() => {
  if (!searchQuery.value.trim()) {
    return chatStore.conversations
  }
  const q = searchQuery.value.toLowerCase().trim()
  return chatStore.conversations.filter((c) => {
    const targetName = getInterlocutorName(c).toLowerCase()
    const lastMsg = (typeof c.last_message === 'string' ? c.last_message : c.last_message?.content || '').toLowerCase()
    return targetName.includes(q) || lastMsg.includes(q)
  })
})

function getInterlocutorName(conv: ConversationResponse): string {
  const currentUserId = authStore.user?.id
  if (currentUserId === conv.patient_id) {
    return conv.secretary_name || 'Clinic Secretary'
  }
  return conv.patient_name || `Patient #${conv.patient_id}`
}

function getInterlocutorRole(conv: ConversationResponse): string {
  const currentUserId = authStore.user?.id
  if (currentUserId === conv.patient_id) {
    return 'Secretary'
  }
  return 'Patient'
}

function formatTime(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function formatDateHeader(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    const today = new Date()
    if (d.toDateString() === today.toDateString()) {
      return 'Today'
    }
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  } catch {
    return ''
  }
}

function scrollToBottom() {
  if (messageContainer.value) {
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  }
}

async function handleSelectConversation(convId: number) {
  await chatStore.selectConversation(convId).catch(() => {})
}

async function handleSendMessage() {
  const text = messageText.value.trim()
  const image = selectedImage.value
  if ((!text && !image) || !chatStore.activeConversationId || isSending.value) return

  isSending.value = true
  try {
    const sent = await chatStore.sendMessage(text, image ?? undefined)
    if (!sent) return
    if (messageText.value.trim() === text) messageText.value = ''
    if (selectedImage.value === image) selectedImage.value = null
    nextTick(() => {
      scrollToBottom()
    })
  } finally {
    isSending.value = false
  }
}

function chooseImage(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    imageError.value = 'Choose an image that is 5 MB or smaller.'
    return
  }
  selectedImage.value = file
  imageError.value = ''
}

async function confirmDelete() {
  if (!deleteTarget.value || isDeleting.value) return
  isDeleting.value = true
  try {
    if (await chatStore.deleteConversation(deleteTarget.value.id)) deleteTarget.value = null
  } finally {
    isDeleting.value = false
  }
}

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSendMessage()
  }
}

async function handleStartNewChat() {
  try {
    const conversation = await chatStore.createOrGetConversation()
    await chatStore.selectConversation(conversation.id)
  } catch {
  }
}
</script>

<template>
  <div class="h-[calc(100vh-140px)] flex flex-col space-y-4">
    <div class="app-panel app-page-heading flex shrink-0 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-teal-100 text-teal-800 flex items-center justify-center font-bold">
          <MessageSquare class="w-5 h-5" />
        </div>
        <div>
          <h1 class="text-xl font-bold leading-tight text-slate-900">Clinic Chat</h1>
          <p class="text-xs text-slate-500">Messages between patients and the clinic secretary</p>
        </div>
      </div>

      <div class="flex items-center gap-2.5">
        <div
          :class="[
            'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border',
            chatStore.wsStatus === 'CONNECTED'
              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
              : chatStore.wsStatus === 'CONNECTING'
                ? 'bg-amber-50 text-amber-800 border-amber-200'
                : 'bg-rose-50 text-rose-800 border-rose-200'
          ]"
        >
          <span
            :class="[
              'w-2 h-2 rounded-full',
              chatStore.wsStatus === 'CONNECTED'
                ? 'bg-emerald-500 animate-pulse'
                : chatStore.wsStatus === 'CONNECTING'
                  ? 'bg-amber-500 animate-spin'
                  : 'bg-rose-500'
            ]"
          ></span>
          <span>
            {{ chatStore.wsStatus === 'CONNECTED' ? 'Live Connected' : chatStore.wsStatus === 'CONNECTING' ? 'Connecting...' : 'Disconnected' }}
          </span>
        </div>

        <button
          v-if="chatStore.wsStatus === 'DISCONNECTED'"
          type="button"
          @click="chatStore.connectWebSocket"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition cursor-pointer"
        >
          <RefreshCw class="w-3.5 h-3.5" />
          Reconnect
        </button>
      </div>
    </div>

    <p v-if="chatStore.error && !deleteTarget" role="alert" class="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{{ chatStore.error }}</p>
    <div class="app-panel grid min-h-0 flex-1 grid-cols-1 overflow-hidden md:grid-cols-12">
      <div class="md:col-span-4 border-r border-slate-200 flex flex-col h-full bg-slate-50/50">
        <div class="p-3.5 border-b border-slate-200 space-y-2">
          <div class="relative">
            <Search class="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search conversations..."
              class="w-full pl-9 pr-3 py-2 rounded-xl border border-slate-200 bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
            />
          </div>

          <div v-if="authStore.isPatient && chatStore.conversations.length === 0" class="pt-1">
            <button
              type="button"
              @click="handleStartNewChat"
              :disabled="chatStore.isLoading"
              class="w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl app-primary-action font-semibold text-xs transition cursor-pointer shadow-xs"
            >
              <Plus class="w-4 h-4" />
              Message the Secretary
            </button>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto divide-y divide-slate-100">
          <div
            v-if="filteredConversations.length === 0"
            class="p-8 text-center text-xs text-slate-400 space-y-2"
          >
            <MessageSquare class="w-6 h-6 mx-auto text-slate-300" />
            <p>No active conversations found.</p>
          </div>

          <div
            v-for="conv in filteredConversations"
            :key="conv.id"
            @click="handleSelectConversation(conv.id)"
            :class="[
              'p-3.5 transition cursor-pointer flex items-start gap-3',
              chatStore.activeConversationId === conv.id
                ? 'bg-teal-50/70 border-l-4 border-teal-600'
                : 'hover:bg-slate-100/70 border-l-4 border-transparent'
            ]"
          >
            <div class="w-10 h-10 rounded-full bg-teal-100 text-teal-800 flex items-center justify-center font-bold text-sm shrink-0 shadow-xs">
              {{ getInterlocutorName(conv).charAt(0) }}
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-1 mb-0.5">
                <span class="text-xs font-bold text-slate-900 truncate">
                  {{ getInterlocutorName(conv) }}
                </span>
                <span class="text-[10px] text-slate-400 shrink-0">
                  {{ formatTime(conv.updated_at) }}
                </span>
              </div>

              <p class="text-[11px] text-teal-700 font-medium truncate mb-1">
                {{ getInterlocutorRole(conv) }}
              </p>

              <div class="flex items-center justify-between">
                <p class="text-[11px] text-slate-500 truncate max-w-[180px]">
                  {{ typeof conv.last_message === 'string' ? conv.last_message : conv.last_message?.content || (conv.last_message?.has_image ? 'Image' : 'No messages yet') }}
                </p>

                <span
                  v-if="(conv.unread_count || 0) > 0"
                  class="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-teal-600 text-white shrink-0 ml-1"
                >
                  {{ conv.unread_count }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="md:col-span-8 flex flex-col h-full bg-white">
        <div v-if="chatStore.activeConversation" class="flex flex-col h-full">
          <div class="p-4 border-b border-slate-200 flex items-center justify-between bg-white shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 rounded-full bg-teal-700 text-white flex items-center justify-center font-bold text-sm shadow-xs">
                {{ getInterlocutorName(chatStore.activeConversation).charAt(0) }}
              </div>
              <div>
                <h2 class="text-sm font-bold text-slate-900 leading-tight">
                  {{ getInterlocutorName(chatStore.activeConversation) }}
                </h2>
                <div class="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
                    {{ getInterlocutorRole(chatStore.activeConversation) }}
                  </span>
                  <span>&bull; Room #{{ chatStore.activeConversation.id }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <Button
                v-if="authStore.isSecretary"
                type="button"
                label="Delete conversation"
                severity="danger"
                size="small"
                text
                @click="deleteTarget = chatStore.activeConversation"
              >
                <Trash2 class="size-4" aria-hidden="true" />
                Delete conversation
              </Button>
            </div>
          </div>

          <div
            v-if="chatStore.wsStatus === 'DISCONNECTED'"
            class="bg-amber-50 border-b border-amber-200 p-2.5 text-xs text-amber-800 flex items-center justify-between px-4 shrink-0"
          >
            <div class="flex items-center gap-2">
              <WifiOff class="w-4 h-4 text-amber-600" />
              <span>Real-time link disconnected. Attempting automatic reconnection...</span>
            </div>
            <button
              type="button"
              @click="chatStore.connectWebSocket"
              class="font-bold underline hover:text-amber-950 cursor-pointer text-xs"
            >
              Retry Now
            </button>
          </div>

          <div
            ref="messageContainer"
            class="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 bg-slate-50/30"
          >
            <div v-if="chatStore.isLoading && chatStore.activeMessages.length === 0" class="py-12 text-center text-slate-400">
              <Loader2 class="w-6 h-6 animate-spin mx-auto text-teal-600 mb-2" />
              <p class="text-xs">Loading consultation history...</p>
            </div>

            <div
              v-else-if="chatStore.activeMessages.length === 0"
              class="py-16 text-center max-w-sm mx-auto space-y-2 text-slate-400"
            >
              <MessageSquare class="w-8 h-8 mx-auto text-slate-300" />
              <p class="text-xs font-medium text-slate-600">Start the Consultation</p>
              <p class="text-[11px] text-slate-400">
                Send a message to discuss symptoms, appointment queries, or post-treatment orthodontic care.
              </p>
            </div>

            <div
              v-for="msg in chatStore.activeMessages"
              :key="msg.id"
              :class="[
                'flex flex-col max-w-[80%] sm:max-w-[70%]',
                msg.sender_id === authStore.user?.id ? 'ml-auto items-end' : 'mr-auto items-start'
              ]"
            >
              <div class="flex items-center gap-1.5 mb-1 px-1 text-[11px]">
                <span class="font-bold text-slate-700">
                  {{ msg.sender_id === authStore.user?.id ? 'You' : msg.sender_name || 'Care Team' }}
                </span>
                <span v-if="msg.sender_role && msg.sender_id !== authStore.user?.id" class="px-1.5 py-0.2 rounded-full text-[9px] font-semibold bg-teal-100 text-teal-800">
                  {{ msg.sender_role }}
                </span>
                <span class="text-slate-400 text-[10px]">
                  {{ formatTime(msg.created_at) }}
                </span>
              </div>

              <div
                :class="[
                  'p-3.5 rounded-2xl text-xs leading-relaxed shadow-xs relative',
                  msg.sender_id === authStore.user?.id
                    ? 'bg-teal-600 text-white rounded-tr-none'
                    : 'bg-white text-slate-800 border border-slate-200/80 rounded-tl-none'
                ]"
              >
                <ChatImage v-if="msg.has_image" :conversation-id="msg.conversation_id" :message-id="msg.id" />
                <p v-if="msg.content" class="whitespace-pre-wrap break-words" :class="{ 'mt-2': msg.has_image }">{{ msg.content }}</p>

                <div
                  v-if="msg.sender_id === authStore.user?.id"
                  class="flex items-center justify-end gap-1 mt-1 text-[10px] text-teal-200"
                >
                  <CheckCheck v-if="msg.is_read" class="w-3.5 h-3.5 text-teal-200" />
                  <Check v-else class="w-3.5 h-3.5 text-teal-200/70" />
                </div>
              </div>
            </div>
          </div>

          <div class="p-3 sm:p-4 border-t border-slate-200 bg-white shrink-0">
            <p v-if="imageError" role="alert" class="mb-2 text-sm text-rose-700">{{ imageError }}</p>
            <div v-if="selectedImage" class="mb-2 flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm">
              <span class="truncate">{{ selectedImage.name }}</span>
              <button type="button" aria-label="Remove attached image" :disabled="isSending" @click="selectedImage = null">
                <X class="size-4" aria-hidden="true" />
              </button>
            </div>
            <form @submit.prevent="handleSendMessage" class="flex items-center gap-2">
              <input ref="imageInput" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="chooseImage" />
              <Button type="button" severity="secondary" outlined aria-label="Attach image" title="Attach image" :disabled="isSending" @click="imageInput?.click()">
                <ImagePlus class="size-4" aria-hidden="true" />
              </Button>
              <input
                v-model="messageText"
                @keydown="handleKeyDown"
                type="text"
                maxlength="2000"
                aria-label="Message"
                placeholder="Write a message…"
                class="min-w-0 flex-1 px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white text-xs text-slate-900 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent transition"
              />

              <button
                type="submit"
                :disabled="(!messageText.trim() && !selectedImage) || isSending"
                class="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl app-primary-action font-semibold text-xs transition cursor-pointer shadow-sm shadow-teal-600/20 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Send class="w-4 h-4" />
                <span class="hidden sm:inline">Send</span>
              </button>
            </form>
          </div>
        </div>

        <div v-else class="flex flex-col items-center justify-center h-full text-center p-8 space-y-3 text-slate-400">
          <MessageSquare class="w-10 h-10 text-slate-300" />
          <h3 class="text-sm font-bold text-slate-700">No Conversation Selected</h3>
          <p class="text-xs text-slate-400 max-w-xs">
            Choose an ongoing conversation from the left inbox or start a new clinical consultation thread.
          </p>
        </div>
      </div>
    </div>
    <Dialog
      :visible="!!deleteTarget"
      modal
      header="Delete conversation?"
      class="w-[min(28rem,calc(100vw-2rem))]"
      :closable="!isDeleting"
      :close-on-escape="!isDeleting"
      @update:visible="deleteTarget = null"
    >
      <p class="mb-4 text-sm text-slate-700">
        This permanently removes the conversation with {{ deleteTarget?.patient_name || 'this patient' }},
        including all messages and images, for both sides.
      </p>
      <p v-if="chatStore.error" role="alert" class="mb-4 text-sm text-rose-700">{{ chatStore.error }}</p>
      <div class="flex justify-end gap-2">
        <Button type="button" label="Cancel" severity="secondary" outlined :disabled="isDeleting" @click="deleteTarget = null" />
        <Button type="button" label="Delete conversation" severity="danger" :loading="isDeleting" @click="confirmDelete" />
      </div>
    </Dialog>
  </div>
</template>
