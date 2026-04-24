import { useMemo, useState } from "react";
import {
  generateQuestions,
  generateSummary,
  reviewAnswers,
  uploadDocument,
} from "./services/api";

const initialConfig = {
  mode: "standard",
  questionType: "objective",
  difficulty: "medium",
  count: 5,
  topic: "",
};

export default function App() {
  const [file, setFile] = useState(null);
  const [documentInfo, setDocumentInfo] = useState(null);
  const [summaryResult, setSummaryResult] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [review, setReview] = useState(null);
  const [config, setConfig] = useState(initialConfig);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const canRunAI = useMemo(() => Boolean(documentInfo?.document_id), [documentInfo]);

  const handleUpload = async () => {
    if (!file) return;
    setError("");
    setLoading(true);
    try {
      const data = await uploadDocument(file);
      setDocumentInfo(data);
      setSummaryResult(null);
      setQuestions([]);
      setAnswers({});
      setReview(null);
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleSummary = async () => {
    if (!canRunAI) return;
    setLoading(true);
    setError("");
    try {
      const data = await generateSummary({
        document_id: documentInfo.document_id,
        mode: config.mode,
      });
      setSummaryResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Summary generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuestions = async () => {
    if (!canRunAI) return;
    setLoading(true);
    setError("");
    try {
      const data = await generateQuestions({
        document_id: documentInfo.document_id,
        question_type: config.questionType,
        difficulty: config.difficulty,
        count: Number(config.count),
        topic: config.topic || null,
      });
      setQuestions(data.questions);
      setAnswers({});
      setReview(null);
    } catch (err) {
      setError(err?.response?.data?.detail || "Question generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerChange = (questionId, value) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleReview = async () => {
    if (!questions.length) return;
    setLoading(true);
    setError("");
    try {
      const data = await reviewAnswers({
        document_id: documentInfo.document_id,
        answers: questions.map((question) => ({
          question_id: question.id,
          user_answer: answers[question.id] || "",
        })),
      });
      setReview(data);
    } catch (err) {
      setError(err?.response?.data?.detail || "Review failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>AI Exam Prep Platform</h1>
      <p className="sub">Upload PDF, DOCX, TXT, JPG, PNG and generate summary + tests.</p>

      <section className="card">
        <h2>1) Upload</h2>
        <input
          type="file"
          accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp"
          onChange={(event) => setFile(event.target.files?.[0] || null)}
        />
        <button onClick={handleUpload} disabled={!file || loading}>
          {loading ? "Working..." : "Upload Document"}
        </button>
        {documentInfo ? (
          <div className="result">
            <p><strong>Document ID:</strong> {documentInfo.document_id}</p>
            <p><strong>Detected Type:</strong> {documentInfo.detected_type}</p>
            <p><strong>Preview:</strong> {documentInfo.extracted_text_preview || "No preview"}</p>
          </div>
        ) : null}
      </section>

      <section className="card">
        <h2>2) AI Controls</h2>
        <div className="grid">
          <label>
            Summary Mode
            <select value={config.mode} onChange={(e) => setConfig({ ...config, mode: e.target.value })}>
              <option value="short">Short</option>
              <option value="standard">Standard</option>
              <option value="detailed">Detailed</option>
            </select>
          </label>
          <label>
            Question Type
            <select
              value={config.questionType}
              onChange={(e) => setConfig({ ...config, questionType: e.target.value })}
            >
              <option value="objective">Objective</option>
              <option value="subjective">Subjective</option>
            </select>
          </label>
          <label>
            Difficulty
            <select
              value={config.difficulty}
              onChange={(e) => setConfig({ ...config, difficulty: e.target.value })}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label>
            Number of Questions
            <input
              type="number"
              min="1"
              max="20"
              value={config.count}
              onChange={(e) => setConfig({ ...config, count: e.target.value })}
            />
          </label>
          <label>
            Topic (optional)
            <input
              type="text"
              value={config.topic}
              onChange={(e) => setConfig({ ...config, topic: e.target.value })}
              placeholder="e.g. Photosynthesis"
            />
          </label>
        </div>
        <div className="actions">
          <button onClick={handleSummary} disabled={!canRunAI || loading}>Generate Summary</button>
          <button onClick={handleQuestions} disabled={!canRunAI || loading}>Generate Questions</button>
        </div>
      </section>

      {summaryResult ? (
        <section className="card">
          <h2>3) Summary Output</h2>
          <p>{summaryResult.summary}</p>
          <p><strong>Key Points:</strong> {summaryResult.key_points.join(", ")}</p>
        </section>
      ) : null}

      {questions.length ? (
        <section className="card">
          <h2>4) Q&A Session</h2>
          {questions.map((question, index) => (
            <div key={question.id} className="question">
              <p><strong>Q{index + 1}:</strong> {question.prompt}</p>
              {question.question_type === "objective" ? (
                <select
                  value={answers[question.id] || ""}
                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                >
                  <option value="">Select answer</option>
                  {question.options.map((option) => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
              ) : (
                <textarea
                  rows="3"
                  value={answers[question.id] || ""}
                  onChange={(e) => handleAnswerChange(question.id, e.target.value)}
                  placeholder="Write your answer..."
                />
              )}
            </div>
          ))}
          <button onClick={handleReview} disabled={loading}>Review Answers & Score</button>
        </section>
      ) : null}

      {review ? (
        <section className="card">
          <h2>5) Performance Report</h2>
          <p><strong>Total Score:</strong> {review.total_score}%</p>
          <p><strong>Recommended Next Difficulty:</strong> {review.recommended_difficulty}</p>
          <h3>Weak Topics</h3>
          {review.weak_topics.map((topic) => (
            <p key={topic.topic}>
              {topic.topic}: {topic.accuracy}% - {topic.suggestion}
            </p>
          ))}
        </section>
      ) : null}

      {error ? <p className="error">{error}</p> : null}
    </div>
  );
}
