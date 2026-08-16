import type {
  AttemptDetailResponse,
  AttemptListResponse,
  AuthTokenResponse,
  DocumentChaptersResponse,
  DocumentDetailResponse,
  DocumentListResponse,
  DocumentUploadResponse,
  DoubtResponse,
  DoubtSessionDetailResponse,
  DoubtSessionListResponse,
  ForgotPasswordRequest,
  ForgotPasswordResponse,
  KeyPointsResponse,
  MessageResponse,
  NotesResponse,
  QuestionGenerationRequest,
  QuestionGenerationResponse,
  ResetPasswordRequest,
  SummaryResponse,
  TestReviewResponse,
  TopicKeyPointsResponse,
  User,
  UserLoginRequest,
  UserRegisterRequest,
  UserUpdateRequest,
  AnswerSubmission,
} from '../types/api.ts'

export const TOKEN_KEY = 'assitify.token'
export const USER_KEY = 'assitify.user'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

async function readError(response: Response): Promise<string> {
  const text = await response.text()
  if (!text) return response.statusText || `Request failed (${response.status})`
  try {
    const data = JSON.parse(text) as { detail?: unknown }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (typeof item === 'string') return item
          if (item && typeof item === 'object' && 'msg' in item) {
            return String((item as { msg: string }).msg)
          }
          return JSON.stringify(item)
        })
        .join(' ')
    }
    return text
  } catch {
    return text
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = new Headers(init.headers)
  const isForm = init.body instanceof FormData
  if (!isForm && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  const isAuthForm =
    path === '/api/auth/login' ||
    path === '/api/auth/register' ||
    path === '/api/auth/forgot-password' ||
    path === '/api/auth/reset-password'
  if (response.status === 401 && token && !isAuthForm) {
    window.dispatchEvent(new Event('assitify:unauthorized'))
  }
  if (!response.ok) {
    throw new ApiError(await readError(response), response.status)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}

export const authApi = {
  login(payload: UserLoginRequest) {
    return request<AuthTokenResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  register(payload: UserRegisterRequest) {
    return request<AuthTokenResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  forgotPassword(payload: ForgotPasswordRequest) {
    return request<ForgotPasswordResponse>('/api/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  resetPassword(payload: ResetPasswordRequest) {
    return request<MessageResponse>('/api/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  me() {
    return request<User>('/api/auth/me')
  },
  updateMe(payload: UserUpdateRequest) {
    return request<User>('/api/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },
}

export const documentsApi = {
  list() {
    return request<DocumentListResponse>('/api/documents')
  },
  get(documentId: string) {
    return request<DocumentDetailResponse>(`/api/documents/${documentId}`)
  },
  upload(file?: File, text?: string) {
    const form = new FormData()
    if (file) form.append('file', file)
    if (text?.trim()) form.append('text', text.trim())
    return request<DocumentUploadResponse>('/api/documents/upload', {
      method: 'POST',
      body: form,
    })
  },
  delete(documentId: string) {
    return request<{ status: string; document_id: string }>(`/api/documents/${documentId}`, {
      method: 'DELETE',
    })
  },
  summary(documentId: string) {
    return request<SummaryResponse>(`/api/documents/${documentId}/summary`)
  },
  keypoints(documentId: string) {
    return request<KeyPointsResponse>(`/api/documents/${documentId}/keypoints`)
  },
  topicKeypoints(documentId: string, topic: string) {
    const query = new URLSearchParams({ topic })
    return request<TopicKeyPointsResponse>(
      `/api/documents/${documentId}/topic-keypoints?${query.toString()}`,
    )
  },
  notes(documentId: string, chapterId: string, topic?: string) {
    const query = new URLSearchParams({ chapter_id: chapterId })
    if (topic?.trim()) query.set('topic', topic.trim())
    return request<NotesResponse>(`/api/documents/${documentId}/notes?${query.toString()}`)
  },
  chapters(documentId: string) {
    return request<DocumentChaptersResponse>(`/api/documents/${documentId}/chapters`)
  },
  questions(documentId: string, payload: QuestionGenerationRequest) {
    return request<QuestionGenerationResponse>(`/api/documents/${documentId}/questions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },
  review(documentId: string, answers: AnswerSubmission[]) {
    return request<TestReviewResponse>(`/api/documents/${documentId}/review`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    })
  },
  attempts(documentId: string) {
    return request<AttemptListResponse>(`/api/documents/${documentId}/attempts`)
  },
  attempt(documentId: string, attemptId: string) {
    return request<AttemptDetailResponse>(`/api/documents/${documentId}/attempts/${attemptId}`)
  },
  doubtSessions(documentId: string) {
    return request<DoubtSessionListResponse>(`/api/documents/${documentId}/doubt/sessions`)
  },
  createDoubtSession(documentId: string) {
    return request<DoubtSessionDetailResponse>(`/api/documents/${documentId}/doubt/sessions`, {
      method: 'POST',
    })
  },
  getDoubtSession(documentId: string, sessionId: string) {
    return request<DoubtSessionDetailResponse>(
      `/api/documents/${documentId}/doubt/sessions/${sessionId}`,
    )
  },
  deleteDoubtSession(documentId: string, sessionId: string) {
    return request<{ status: string }>(
      `/api/documents/${documentId}/doubt/sessions/${sessionId}`,
      { method: 'DELETE' },
    )
  },
  sendDoubt(documentId: string, question: string, sessionId?: string) {
    return request<DoubtResponse>(`/api/documents/${documentId}/doubt`, {
      method: 'POST',
      body: JSON.stringify({ question, session_id: sessionId ?? null }),
    })
  },
}
