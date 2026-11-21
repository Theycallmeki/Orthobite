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
  let session = 0
  let syncingSession: number | null = null
  let inboxRevision = 0

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
    const history = messages.value[convId]
    if (history?.some((message) => message.id === msg.id)) return
    if (history) history.push(msg)
    else if (activeConversationId.value === convId) messages.value[convId] = [msg]

    const convIdx = conversations.value.findIndex((c) => c.id === convId)
    if (convIdx === -1) {
      fetchConversations(true).catch(() => {})
      return
    }
    if (convIdx !== -1) {
      const conv = conversations.value[convIdx]!
      const authStore = useAuthStore()
      const isFromOther = authStore.user?.id !== msg.sender_id
      const isCurrentlyActive = activeConversationId.value === convId

      conv.last_message = msg
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
    const currentSession = session
    wsStatus.value = 'CONNECTING'
    wsClient = chatApi.createChatSocket({
      autoReconnect: true,
      reconnectIntervalMs: 3000,
      onOpen: () => {
        if (session !== currentSession) return
        wsStatus.value = 'CONNECTED'
        syncChat()
      },
      onMessage: (message) => {
        if (session === currentSession) _appendMessage(message)
      },
      onClose: () => {
        if (session === currentSession) wsStatus.value = 'DISCONNECTED'
      },
      onError: () => {
        if (session === currentSession) wsStatus.value = 'DISCONNECTED'
      },
      onConversationUpdated: () => {
        if (session === currentSession) fetchConversations(true).catch(() => {})
      },
      onConversationDeleted: (conversationId) => {
        if (session === currentSession) removeConversation(conversationId)
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

  function resetChat(): void {
    session++
    disconnectWebSocket()
    conversations.value = []
    messages.value = {}
    activeConversationId.value = null
    error.value = null
    isLoading.value = false
    inboxRevision++
  }

  function removeConversation(conversationId: number): void {
    inboxRevision++
    conversations.value = conversations.value.filter((conversation) => conversation.id !== conversationId)
    delete messages.value[conversationId]
    if (activeConversationId.value === conversationId) activeConversationId.value = null
  }

  async function deleteConversation(conversationId: number): Promise<boolean> {
    const currentSession = session
    error.value = null
    try {
      await chatApi.deleteConversation(conversationId)
      if (session !== currentSession) return false
      removeConversation(conversationId)
      return true
    } catch (err) {
      if (session === currentSession) error.value = extractError(err, 'Failed to delete conversation')
      return false
    }
  }

  async function fetchConversations(background = false): Promise<ConversationResponse[]> {
    const currentSession = session
    const revision = ++inboxRevision
    if (!background) {
      isLoading.value = true
      error.value = null
    }
    try {
      const response = await chatApi.listConversations()
      const data = response.data as unknown
      const list = Array.isArray(data)
        ? (data as ConversationResponse[])
        : (data as { conversations?: ConversationResponse[] })?.conversations || []
      if (session !== currentSession) return []
      if (revision !== inboxRevision) return conversations.value
      conversations.value = list
      const activeId = activeConversationId.value
      if (activeId !== null && !conversations.value.some((conversation) => conversation.id === activeId)) {
        activeConversationId.value = null
      }
      return conversations.value
    } catch (err: unknown) {
      if (!background && session === currentSession) error.value = extractError(err, 'Failed to load conversations')
      throw err
    } finally {
      if (!background && session === currentSession) isLoading.value = false
    }
  }

  async function createOrGetConversation(patientId?: number): Promise<ConversationResponse> {
    const currentSession = session
    isLoading.value = true
    error.value = null
    try {
      const response = await chatApi.createConversation(patientId)
      if (session !== currentSession) return response.data
      inboxRevision++
      const exists = conversations.value.some((c) => c.id === response.data.id)
      if (!exists) {
        conversations.value.unshift(response.data)
      }
      activeConversationId.value = response.data.id
      return response.data
    } catch (err: unknown) {
      if (session === currentSession) error.value = extractError(err, 'Failed to initialize conversation')
      throw err
    } finally {
      if (session === currentSession) isLoading.value = false
    }
  }

  async function fetchHistory(
    conversationId: number,
    params?: MessageHistoryQueryParams,
    background = false,
  ): Promise<ChatMessageResponse[]> {
    const currentSession = session
    if (!background) {
      isLoading.value = true
      error.value = null
    }
    try {
      const response = await chatApi.getConversationHistory(conversationId, { newest: true, ...params })
      if (session !== currentSession || !conversations.value.some((entry) => entry.id === conversationId)) return []
      const data = response.data as unknown
      const incoming = Array.isArray(data)
        ? (data as ChatMessageResponse[])
        : (data as { messages?: ChatMessageResponse[] })?.messages || []
      const merged = new Map((messages.value[conversationId] ?? []).map((message) => [message.id, message]))
      for (const message of incoming) merged.set(message.id, message)
      messages.value[conversationId] = [...merged.values()].sort((first, second) => first.id - second.id)
      return messages.value[conversationId]
    } catch (err: unknown) {
      if (!background && session === currentSession) error.value = extractError(err, 'Failed to load message history')
      throw err
    } finally {
      if (!background && session === currentSession) isLoading.value = false
    }
  }

  async function syncChat(): Promise<void> {
    const currentSession = session
    if (syncingSession === currentSession || isLoading.value) return
    syncingSession = currentSession
    try {
      const inbox = await fetchConversations(true)
      if (session !== currentSession) return
      const active = inbox.find((conversation) => conversation.id === activeConversationId.value)
      if (active) {
        await fetchHistory(active.id, undefined, true)
        if (session === currentSession && active.id === activeConversationId.value && active.unread_count) {
          await markAsRead(active.id)
        }
      }
    } catch {
      // Keep the current inbox visible and retry on the next sync.
    } finally {
      if (syncingSession === currentSession) syncingSession = null
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

  async function sendMessage(content: string, image?: File): Promise<boolean> {
    const trimmed = content.trim()
    const conversationId = activeConversationId.value
    if ((!trimmed && !image) || conversationId === null) return false
    const currentSession = session
    error.value = null
    try {
      const { data } = image
        ? await chatApi.sendImage(conversationId, image, trimmed)
        : await chatApi.sendMessage(conversationId, trimmed)
      if (session !== currentSession || !conversations.value.some((entry) => entry.id === conversationId)) return false
      if (!messages.value[conversationId]) messages.value[conversationId] = []
      _appendMessage(data)
      return true
    } catch (err) {
      if (session === currentSession) error.value = extractError(err, 'Failed to send message')
      return false
    }
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
    resetChat,
    fetchConversations,
    syncChat,
    deleteConversation,
    createOrGetConversation,
    fetchHistory,
    markAsRead,
    selectConversation,
    sendMessage,
  }
})

