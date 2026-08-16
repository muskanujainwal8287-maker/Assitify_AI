export type LlmSource = 'openai' | 'fallback' | 'mixed'

export type QuestionType = 'objective' | 'subjective'
export type Difficulty = 'easy' | 'medium' | 'hard'

export type User = {
  id: string
  email: string
  mobile_number: string
  full_name: string
  created_at: string
}

export type AuthTokenResponse = {
  access_token: string
  token_type: string
  user: User
}

export type UserRegisterRequest = {
  email: string
  mobile_number: string
  password: string
  full_name?: string
}

export type UserLoginRequest = {
  email?: string
  mobile_number?: string
  password: string
}

export type UserUpdateRequest = {
  email: string
  mobile_number: string
  full_name?: string
}

export type ForgotPasswordRequest = {
  email?: string
  mobile_number?: string
}

export type ForgotPasswordResponse = {
  message: string
  channel: 'email' | 'sms'
}

export type ResetPasswordRequest = {
  new_password: string
  token?: string
  mobile_number?: string
  otp?: string
}

export type MessageResponse = {
  message: string
}

export type DocumentListItem = {
  document_id: string
  filename: string
  detected_type: string
  created_at: string
  question_attempted_count: number
}

export type DocumentListResponse = {
  documents: DocumentListItem[]
  total: number
}

export type DocumentUploadResponse = {
  document_id: string
  filename: string
  detected_type: string
  extracted_text_preview: string
}

export type DocumentDetailResponse = {
  document_id: string
  filename: string
  detected_type: string
  created_at: string
  text_preview: string
  text_length: number
  question_attempted_count: number
  attempt_count: number
}

export type AiMeta = {
  source: LlmSource
  llm_error: string | null
  fallback_reason: string | null
}

export type SummaryResponse = AiMeta & {
  document_id: string
  summary: string
}

export type KeyPointsResponse = AiMeta & {
  document_id: string
  key_points: string[]
}

export type TopicKeyPointsResponse = AiMeta & {
  document_id: string
  topic: string
  key_points: string[]
}

export type TopicNotes = {
  topic: string
  notes: string[]
}

export type ChapterNotes = {
  title: string
  chapter_id: string | null
  chapter_number: number | null
  topics: TopicNotes[]
}

export type NotesResponse = AiMeta & {
  document_id: string
  chapters: ChapterNotes[]
}

export type QuestionOut = {
  id: string
  prompt: string
  question_type: string
  options: string[]
  answer: string
  difficulty: string
  topic: string
}

export type QuestionGenerationRequest = {
  topic?: string | null
  question_type: QuestionType
  difficulty: Difficulty
  count: number
}

export type QuestionGenerationResponse = AiMeta & {
  document_id: string
  questions: QuestionOut[]
}

export type AnswerSubmission = {
  question_id: string
  user_answer: string
}

export type AnswerReviewOut = {
  question_id: string
  expected_answer: string
  user_answer: string
  is_correct: boolean
  score: number
  explanation: string
  topic: string
}

export type WeakTopicOut = {
  topic: string
  accuracy: number
  suggestion: string
}

export type TestReviewResponse = AiMeta & {
  document_id: string
  attempt_id: string
  total_score: number
  reviews: AnswerReviewOut[]
  weak_topics: WeakTopicOut[]
  recommended_difficulty: string
  scoring_source: LlmSource
  weak_topics_source: 'openai' | 'fallback'
}

export type ChatMessageOut = {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export type DoubtResponse = AiMeta & {
  document_id: string
  session_id: string
  question: string
  answer: string
  messages: ChatMessageOut[]
}

export type DoubtSessionListItem = {
  session_id: string
  document_id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export type DoubtSessionListResponse = {
  document_id: string
  sessions: DoubtSessionListItem[]
  total: number
}

export type DoubtSessionDetailResponse = {
  session_id: string
  document_id: string
  title: string
  messages: ChatMessageOut[]
  created_at: string
  updated_at: string
}

export type ChapterInfo = {
  chapter_id: string
  chapter_number: number
  title: string
  start_char: number
  end_char: number
  chunk_count: number
}

export type DocumentChaptersResponse = {
  document_id: string
  total_chapters: number
  chapters: ChapterInfo[]
}

export type AttemptListItem = {
  attempt_id: string
  document_id: string
  total_score: number
  recommended_difficulty: string
  source: string
  scoring_source: string
  weak_topics: WeakTopicOut[] | unknown[]
  created_at: string
  answer_count: number
}

export type AttemptListResponse = {
  document_id: string
  attempts: AttemptListItem[]
  total: number
}

export type AttemptDetailResponse = {
  attempt_id: string
  document_id: string
  total_score: number
  recommended_difficulty: string
  source: string
  scoring_source: string
  weak_topics: WeakTopicOut[] | unknown[]
  created_at: string
  reviews: AnswerReviewOut[]
}

export const DOCUMENT_SECTIONS = [
  'overview',
  'summary',
  'keypoints',
  'notes',
  'practice',
  'attempts',
  'doubt',
] as const

export type DocumentSection = (typeof DOCUMENT_SECTIONS)[number]
