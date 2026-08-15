import { useState, type SubmitEvent } from 'react'
import { Button, Card, ErrorBanner, SourceBadge, Spinner, fieldClass } from '../../components/ui.tsx'
import { documentsApi } from '../../lib/api.ts'
import { errorMessage, formatScore } from '../../lib/format.ts'
import type {
  Difficulty,
  QuestionGenerationResponse,
  QuestionOut,
  QuestionType,
  TestReviewResponse,
} from '../../types/api.ts'

export function PracticePanel({ documentId }: { documentId: string }) {
  const [questionType, setQuestionType] = useState<QuestionType>('objective')
  const [difficulty, setDifficulty] = useState<Difficulty>('easy')
  const [count, setCount] = useState(5)
  const [topic, setTopic] = useState('')
  const [quiz, setQuiz] = useState<QuestionGenerationResponse | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<TestReviewResponse | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function generate(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const generated = await documentsApi.questions(documentId, {
        question_type: questionType,
        difficulty,
        count,
        topic: topic.trim() || null,
      })
      setQuiz(generated)
      setAnswers({})
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function submit() {
    if (!quiz) return
    const missing = quiz.questions.filter((question) => !answers[question.id]?.trim())
    if (missing.length > 0) {
      setError('Answering all questions is mandatory before submitting.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const review = await documentsApi.review(
        documentId,
        quiz.questions.map((question) => ({
          question_id: question.id,
          user_answer: answers[question.id],
        })),
      )
      setResult(review)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="space-y-5">
      <header>
        <h2 className="font-serif text-2xl">Practice</h2>
        <p className="text-sm text-muted2">Generate a set, answer it, then get scored with weak-topic hints.</p>
      </header>

      <form onSubmit={generate} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm">
          Type
          <select
            className={`${fieldClass} mt-1`}
            value={questionType}
            onChange={(event) => setQuestionType(event.target.value as QuestionType)}
          >
            <option value="objective">Objective</option>
            <option value="subjective">Subjective</option>
          </select>
        </label>
        <label className="text-sm">
          Difficulty
          <select
            className={`${fieldClass} mt-1`}
            value={difficulty}
            onChange={(event) => setDifficulty(event.target.value as Difficulty)}
          >
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
        <label className="text-sm">
          Count
          <input
            className={`${fieldClass} mt-1`}
            type="number"
            min={1}
            max={100}
            value={count}
            onChange={(event) => setCount(Number(event.target.value))}
          />
        </label>
        <label className="text-sm">
          Topic (optional)
          <input
            className={`${fieldClass} mt-1`}
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
          />
        </label>
        <div className="sm:col-span-2 lg:col-span-4">
          <Button type="submit" disabled={busy}>
            {busy && !quiz ? 'Generating questions…' : 'Generate questions'}
          </Button>
        </div>
      </form>

      {error ? <ErrorBanner message={error} /> : null}
      {busy && !result ? <Spinner label="Working... This may take a minute." /> : null}

      {quiz && !result ? (
        <div className="space-y-4">
          <SourceBadge source={quiz.source} />
          {quiz.questions.map((question, index) => (
            <QuestionCard
              key={question.id}
              index={index}
              question={question}
              value={answers[question.id] ?? ''}
              onChange={(value) => setAnswers((current) => ({ ...current, [question.id]: value }))}
            />
          ))}
          <Button onClick={submit} disabled={busy}>
            {busy ? 'Scoring…' : 'Submit answers'}
          </Button>
        </div>
      ) : null}

      {result ? (
        <div className="space-y-4">
          <Card>
            <p className="text-sm text-muted2">Score</p>
            <p className="font-serif text-4xl">{formatScore(result.total_score)}</p>
            <p className="mt-2 text-sm">
              Next recommended difficulty: <strong>{result.recommended_difficulty}</strong>
            </p>
            <div className="mt-2 flex gap-2">
              <SourceBadge source={result.scoring_source} />
            </div>
          </Card>
          {result.weak_topics.length > 0 ? (
            <div>
              <h3 className="font-serif text-xl">Weak topics</h3>
              <ul className="mt-2 space-y-2">
                {result.weak_topics.map((topicItem) => (
                  <li key={topicItem.topic} className="rounded-lg border border-line px-3 py-2 text-sm">
                    <strong>{topicItem.topic}</strong> · {Math.round(topicItem.accuracy)}%
                    <p className="text-muted2">{topicItem.suggestion}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {result.reviews.map((review) => (
            <Card key={review.question_id}>
              <p className={`text-xs font-medium ${review.is_correct ? 'text-good' : 'text-bad'}`}>
                {review.is_correct ? 'Correct' : 'Needs work'} · {Math.round(review.score)} / 100 · {review.topic}
              </p>
              <p className="mt-2 text-sm">
                <span className="text-muted2">Your answer:</span> {review.user_answer}
              </p>
              <p className="mt-1 text-sm">
                <span className="text-muted2">Expected:</span> {review.expected_answer}
              </p>
              <p className="mt-2 text-sm text-muted2">{review.explanation}</p>
            </Card>
          ))}
          <Button
            variant="ghost"
            onClick={() => {
              setResult(null)
              setQuiz(null)
              setAnswers({})
            }}
          >
            Start another set
          </Button>
        </div>
      ) : null}
    </section>
  )
}

function QuestionCard({
  index,
  question,
  value,
  onChange,
}: {
  index: number
  question: QuestionOut
  value: string
  onChange: (value: string) => void
}) {
  const isObjective = question.question_type === 'objective' && question.options.length > 0
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-muted2">
        Q{index + 1} · {question.difficulty} · {question.topic}
      </p>
      <p className="mt-2 font-medium">{question.prompt}</p>
      {isObjective ? (
        <div className="mt-3 space-y-2">
          {question.options.map((option) => (
            <label key={option} className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="radio"
                name={question.id}
                value={option}
                checked={value === option}
                onChange={() => onChange(option)}
                className="mt-1"
              />
              <span>{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          className={`${fieldClass} mt-3 min-h-24`}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Write your answer"
        />
      )}
    </Card>
  )
}
