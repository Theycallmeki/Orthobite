import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  chatApi,
  type ConversationResponse,
  type ChatMessageResponse,
  type MessageHistoryQueryParams,
  type ChatWebSocketClient,
} from '@/api/chat'
import { useAuthStore } from './auth'

export type WebSocketStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED'

function extractError(err: unknown, fallback: string): string {
  return (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || fallback
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<ConversationResponse[]>([])
  const activeConversationId = ref<number | null>(null)
  const messages = ref<Record<number, ChatMessageResponse[]>>({})
  const wsStatus = ref<WebSocketStatus>('DISCONNECTED')
  const isLoading = ref<boolean>(false)
  const error = ref<string | null>(null)

  let wsClient: ChatWebSocketClient | null = null

  const activeConversation = computed<ConversationResponse | null>(() => {
    if (activeConversationId.value === null) {
      return null
    }
    return conversations.value.find((c) => c.id === activeConversationId.value) || null
  })

  const activeMessages = computed<ChatMessageResponse[]>(() => {
    if (activeConversationId.value === null) {
      return []
    }
    return messages.value[activeConversationId.value] || []
  })

  const totalUnreadCount = computed<number>(() =>
    conversations.value.reduce((sum, conv) => sum + (conv.unread_count || 0), 0),
  )

  function _appendMessage(msg: ChatMessageResponse): void {
    const convId = msg.conversation_id
    if (!messages.value[convId]) {
      messages.value[convId] = []
    }
    const exists = messages.value[convId].some((m) => m.id === msg.id)
    if (!exists) {
      messages.value[convId].push(msg)
    }

    const convIdx = conversations.value.findIndex((c) => c.id === convId)
    if (convIdx !== -1) {
      const conv = conversations.value[convIdx]!
      const authStore = useAuthStore()
      const isFromOther = authStore.user?.id !== msg.sender_id
      const isCurrentlyActive = activeConversationId.value === convId

      conv.last_message = msg.content
      conv.updated_at = msg.created_at
      if (isFromOther && !isCurrentlyActive) {
        conv.unread_count = (conv.unread_count || 0) + 1
      }

      if (convIdx > 0) {
        conversations.value.splice(convIdx, 1)
        conversations.value.unshift(conv)
      }

      if (isFromOther && isCurrentlyActive) {
        markAsRead(convId).catch(() => {})
      }
    }
  }

  function connectWebSocket(): void {
    if (wsClient) {
      return
    }
    wsStatus.value = 'CONNECTING'
    wsClient = chatApi.createChatSocket({
      autoReconnect: true,
      reconnectIntervalMs: 3000,
      onOpen: () => {
        wsStatus.value = 'CONNECTED'
      },
      onMessage: (message) => {
        _appendMessage(message)
      },
      onClose: () => {
        wsStatus.value = 'DISCONNECTED'
      },
      onError: () => {
        wsStatus.value = 'DISCONNECTED'
      },
    })
  }

  function disconnectWebSocket(): void {
    if (wsClient) {
      wsClient.close()
      wsClient = null
    }
    wsStatus.value = 'DISCONNECTED'
  }

  async function fetchConversations(): Promise<ConversationResponse[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await chatApi.listConversations()
      conversations.value = response.data
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load conversations')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function createOrGetConversation(patientId?: number): Promise<ConversationResponse> {
    isLoading.value = true
    error.value = null
    try {
      const response = await chatApi.createConversation(patientId)
      const exists = conversations.value.some((c) => c.id === response.data.id)
      if (!exists) {
        conversations.value.unshift(response.data)
      }
      activeConversationId.value = response.data.id
      return response.data
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to initialize conversation')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function fetchHistory(
    conversationId: number,
    params?: MessageHistoryQueryParams,
  ): Promise<ChatMessageResponse[]> {
    isLoading.value = true
    error.value = null
    try {
      const response = await chatApi.getConversationHistory(conversationId, params)
      const incoming = response.data
      if (params?.before_id && messages.value[conversationId]) {
        const existingIds = new Set(messages.value[conversationId].map((m) => m.id))
        const older = incoming.filter((m) => !existingIds.has(m.id))
        messages.value[conversationId] = [...older, ...messages.value[conversationId]]
      } else {
        messages.value[conversationId] = incoming
      }
      return messages.value[conversationId]
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to load message history')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function markAsRead(conversationId: number): Promise<void> {
    try {
      await chatApi.markAsRead(conversationId)
      const conv = conversations.value.find((c) => c.id === conversationId)
      if (conv) {
        conv.unread_count = 0
      }
      if (messages.value[conversationId]) {
        messages.value[conversationId].forEach((m) => {
          m.is_read = true
        })
      }
    } catch (err: unknown) {
      error.value = extractError(err, 'Failed to mark messages as read')
    }
  }

  async function selectConversation(conversationId: number): Promise<void> {
    activeConversationId.value = conversationId
    if (!messages.value[conversationId]) {
      await fetchHistory(conversationId)
    }
    const conv = conversations.value.find((c) => c.id === conversationId)
    if (conv && (conv.unread_count || 0) > 0) {
      await markAsRead(conversationId)
    }
  }

  function sendMessage(content: string): void {
    const trimmed = content.trim()
    if (!trimmed || activeConversationId.value === null) {
      return
    }
    if (!wsClient || wsStatus.value !== 'CONNECTED') {
      connectWebSocket()
    }
    wsClient?.send({
      conversation_id: activeConversationId.value,
      content: trimmed,
    })
  }

  return {
    conversations,
    activeConversationId,
    messages,
    wsStatus,
    isLoading,
    error,
    activeConversation,
    activeMessages,
    totalUnreadCount,
    connectWebSocket,
    disconnectWebSocket,
    fetchConversations,
    createOrGetConversation,
    fetchHistory,
    markAsRead,
    selectConversation,
    sendMessage,
  }
})

