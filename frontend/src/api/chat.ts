import { apiClient, getWebSocketUrl } from './api'
import type { AxiosResponse } from 'axios'


export interface ChatMessageResponse {
  id: number
  conversation_id: number
  sender_id: number
  sender_name?: string
  sender_role?: string
  content: string
  has_image?: boolean
  is_read: boolean
  created_at: string
}

export interface ConversationResponse {
  id: number
  patient_id: number
  patient_name?: string
  secretary_id: number | null
  secretary_name?: string
  updated_at: string
  last_message?: string | ChatMessageResponse | null
  unread_count?: number
}

export interface ConversationListResponse {
  conversations: ConversationResponse[]
  total_unread: number
}

export interface ChatHistoryResponse {
  conversation_id: number
  messages: ChatMessageResponse[]
  total_count: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ConversationCreateRequest {
  patient_id?: number
}

export interface MessageHistoryQueryParams {
  limit?: number
  before_id?: number
  newest?: boolean
}

export interface ChatWebSocketOptions {
  onMessage?: (message: ChatMessageResponse) => void
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onConversationUpdated?: () => void
  onConversationDeleted?: (conversationId: number) => void
  autoReconnect?: boolean
  reconnectIntervalMs?: number
}

export interface ChatWebSocketClient {
  socket: WebSocket | null
  send: (payload: { conversation_id: number; content: string }) => void
  close: () => void
}


export const chatApi = {

  listConversations(): Promise<AxiosResponse<ConversationResponse[]>> {
    return apiClient.get('/chat/conversations')
  },


  createConversation(patientId?: number): Promise<AxiosResponse<ConversationResponse>> {
    return apiClient.post('/chat/conversations', { patient_id: patientId })
  },


  getConversationHistory(
    conversationId: number,
    params?: MessageHistoryQueryParams,
  ): Promise<AxiosResponse<ChatMessageResponse[]>> {
    return apiClient.get(`/chat/conversations/${conversationId}/history`, { params })
  },


  markAsRead(conversationId: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.post(`/chat/conversations/${conversationId}/read`)
  },

  sendMessage(conversationId: number, content: string): Promise<AxiosResponse<ChatMessageResponse>> {
    return apiClient.post(`/chat/conversations/${conversationId}/messages`, { content })
  },

  sendImage(conversationId: number, image: File, caption: string): Promise<AxiosResponse<ChatMessageResponse>> {
    const form = new FormData()
    form.append('file', image)
    if (caption) form.append('caption', caption)
    return apiClient.post(`/chat/conversations/${conversationId}/images`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  getMessageImage(conversationId: number, messageId: number, signal: AbortSignal): Promise<AxiosResponse<Blob>> {
    return apiClient.get(`/chat/conversations/${conversationId}/messages/${messageId}/image`, {
      responseType: 'blob',
      signal,
    })
  },

  deleteConversation(conversationId: number): Promise<AxiosResponse<void>> {
    return apiClient.delete(`/chat/conversations/${conversationId}`)
  },


  createChatSocket(options: ChatWebSocketOptions = {}): ChatWebSocketClient {
    const {
      onMessage,
      onOpen,
      onClose,
      onError,
      onConversationUpdated,
      onConversationDeleted,
      autoReconnect = true,
      reconnectIntervalMs = 3000,
    } = options

    let ws: WebSocket | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null
    let intentionallyClosed = false

    const connect = () => {
      try {
        const url = getWebSocketUrl('/ws/chat')
        ws = new WebSocket(url)

        ws.onmessage = (event) => {
          try {
            const raw = JSON.parse(event.data)
            if (raw.type === 'connection_ack') {
              onOpen?.(event)
            } else if (raw.type === 'conversation_updated') {
              onConversationUpdated?.()
            } else if (raw.type === 'conversation_deleted' && typeof raw.conversation_id === 'number') {
              onConversationDeleted?.(raw.conversation_id)
            } else if (raw.type === 'new_message' && raw.message) {
              onMessage?.(raw.message as ChatMessageResponse)
            } else if (raw.id && raw.conversation_id && raw.content) {
              onMessage?.(raw as ChatMessageResponse)
            }
          } catch {
          }
        }

        ws.onerror = (event) => {
          onError?.(event)
        }

        ws.onclose = (event) => {
          onClose?.(event)
          if (!intentionallyClosed && autoReconnect) {
            reconnectTimeout = setTimeout(connect, reconnectIntervalMs)
          }
        }
      } catch (err) {
        if (!intentionallyClosed && autoReconnect) {
          reconnectTimeout = setTimeout(connect, reconnectIntervalMs)
        }
      }
    }

    connect()

    return {
      get socket() {
        return ws
      },
      send(payload: { conversation_id: number; content: string }) {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'send_message', ...payload }))
        }
      },
      close() {
        intentionallyClosed = true
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout)
        }
        if (ws) {
          ws.close()
        }
      },
    }
  },
}

export default chatApi
