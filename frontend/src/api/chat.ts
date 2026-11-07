import { apiClient, getWebSocketUrl } from './api'
import type { AxiosResponse } from 'axios'

// ===========================================================================
// Colocated TypeScript Types & Contracts
// ===========================================================================

export interface ChatMessageResponse {
  id: number
  conversation_id: number
  sender_id: number
  sender_name?: string
  content: string
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
  last_message?: string
  unread_count?: number
}

export interface ConversationCreateRequest {
  patient_id?: number // Required when staff initiates conversation; optional for patients
}

export interface MessageHistoryQueryParams {
  limit?: number // default 50
  before_id?: number // pagination cursor for loading earlier messages
}

export interface ChatWebSocketOptions {
  onMessage?: (message: ChatMessageResponse) => void
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  autoReconnect?: boolean
  reconnectIntervalMs?: number
}

export interface ChatWebSocketClient {
  socket: WebSocket | null
  send: (payload: { conversation_id: number; content: string }) => void
  close: () => void
}

// ===========================================================================
// Real-Time Chat & Messaging API Endpoints
// ===========================================================================

export const chatApi = {
  /**
   * List inbox conversations with real-time unread message counts.
   * Patients see their own conversation; staff see all active patient chats.
   * Endpoint: GET /chat/conversations
   */
  listConversations(): Promise<AxiosResponse<ConversationResponse[]>> {
    return apiClient.get('/chat/conversations')
  },

  /**
   * Initiate a conversation between a patient and clinic staff.
   * Endpoint: POST /chat/conversations
   */
  createConversation(patientId?: number): Promise<AxiosResponse<ConversationResponse>> {
    return apiClient.post('/chat/conversations', { patient_id: patientId })
  },

  /**
   * Retrieve paginated message history for a conversation.
   * Supports infinite scroll upwards via `before_id`.
   * Endpoint: GET /chat/conversations/{conversationId}/history
   */
  getConversationHistory(
    conversationId: number,
    params?: MessageHistoryQueryParams,
  ): Promise<AxiosResponse<ChatMessageResponse[]>> {
    return apiClient.get(`/chat/conversations/${conversationId}/history`, { params })
  },

  /**
   * Mark all unread messages in a conversation as read.
   * Endpoint: POST /chat/conversations/{conversationId}/read
   */
  markAsRead(conversationId: number): Promise<AxiosResponse<{ message: string }>> {
    return apiClient.post(`/chat/conversations/${conversationId}/read`)
  },

  /**
   * Establish a bi-directional WebSocket connection to the backend (/ws/chat?token={jwt}).
   * Includes automatic reconnection, JSON message parsing, and type-safe payload sender.
   */
  createChatSocket(options: ChatWebSocketOptions = {}): ChatWebSocketClient {
    const {
      onMessage,
      onOpen,
      onClose,
      onError,
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

        ws.onopen = (event) => {
          onOpen?.(event)
        }

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data) as ChatMessageResponse
            onMessage?.(data)
          } catch {
            // Ignore non-JSON or ping/pong frame
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
        console.error('WebSocket connection error:', err)
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
          ws.send(JSON.stringify(payload))
        } else {
          console.warn('Chat WebSocket is not open. ReadyState:', ws?.readyState)
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

