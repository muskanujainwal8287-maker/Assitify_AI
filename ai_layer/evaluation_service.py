import json
from collections import defaultdict
from typing import Any

from openai import OpenAI

from ai_layer.config import settings
from ai_layer.schemas import AnswerReview, WeakTopic


class EvaluationService:
    _client: OpenAI | None = None

    @classmethod
    def _get_client(cls) -> OpenAI | None:
        if not settings.openai_api_key:
            return None
        if cls._client is None:
            cls._client = OpenAI(api_key=settings.openai_api_key)
        return cls._client

    @staticmethod
    def _extract_json(content: str) -> dict[str, Any] | None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def review_answers(
        answers: dict[str, str],
        expected: dict[str, dict],
    ) -> tuple[list[AnswerReview], float, list[WeakTopic], str]:
        topic_scores: dict[str, list[float]] = defaultdict(list)
        reviews: list[AnswerReview] = []

        for question_id, user_answer in answers.items():
            expected_item = expected.get(question_id)
            if not expected_item:
                continue

            expected_answer = expected_item["answer"]
            topic = expected_item["topic"]
            score, explanation = EvaluationService._score_answer(user_answer, expected_answer)
            is_correct = score >= 0.6
            topic_scores[topic].append(score)

            reviews.append(
                AnswerReview(
                    question_id=question_id,
                    expected_answer=expected_answer,
                    user_answer=user_answer,
                    is_correct=is_correct,
                    score=round(score * 100, 2),
                    explanation=explanation,
                    topic=topic,
                )
            )

        total_score = round(sum(item.score for item in reviews) / len(reviews), 2) if reviews else 0.0
        weak_topics = EvaluationService._weak_topics(topic_scores)
        recommended_difficulty = EvaluationService._recommend_difficulty(total_score)
        return reviews, total_score, weak_topics, recommended_difficulty

    @staticmethod
    def _score_answer(user_answer: str, expected_answer: str) -> tuple[float, str]:
        llm_score = EvaluationService._score_with_llm(user_answer=user_answer, expected_answer=expected_answer)
        if llm_score:
            return llm_score

        # Fallback: token overlap heuristic.
        user_tokens = {token.lower() for token in user_answer.split() if token.strip()}
        expected_tokens = {token.lower() for token in expected_answer.split() if token.strip()}
        if not expected_tokens:
            return 0.0, "Unable to evaluate because expected answer is empty."
        overlap = len(user_tokens.intersection(expected_tokens))
        score = min(1.0, overlap / len(expected_tokens))
        explanation = (
            "Strong answer. Keep this structure."
            if score >= 0.6
            else "Partially correct. Focus on key concept terms and examples."
        )
        return score, explanation

    @staticmethod
    def _score_with_llm(user_answer: str, expected_answer: str) -> tuple[float, str] | None:
        client = EvaluationService._get_client()
        if client is None:
            return None
        prompt = (
            "You evaluate a student's answer.\n"
            "Return strict JSON with keys: score_0_to_1 (number), explanation (string).\n"
            "Score should reward conceptual correctness over exact wording.\n\n"
            f"Expected answer:\n{expected_answer}\n\n"
            f"Student answer:\n{user_answer}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = getattr(response, "output_text", "") or ""
            parsed = EvaluationService._extract_json(output_text)
            if not parsed:
                return None
            score = float(parsed.get("score_0_to_1", 0))
            explanation = str(parsed.get("explanation", "")).strip()
            score = max(0.0, min(1.0, score))
            if not explanation:
                explanation = "Evaluation generated."
            return score, explanation
        except Exception:
            return None

    @staticmethod
    def _weak_topics(topic_scores: dict[str, list[float]]) -> list[WeakTopic]:
        llm_topics = EvaluationService._weak_topics_with_llm(topic_scores)
        if llm_topics is not None:
            return llm_topics

        results: list[WeakTopic] = []
        for topic, scores in topic_scores.items():
            accuracy = round(sum(scores) / len(scores) * 100, 2)
            if accuracy < 65:
                suggestion = "Revise basics and solve 5 more practice questions."
            else:
                suggestion = "Maintain practice with medium and hard questions."
            results.append(WeakTopic(topic=topic, accuracy=accuracy, suggestion=suggestion))
        return sorted(results, key=lambda item: item.accuracy)

    @staticmethod
    def _weak_topics_with_llm(topic_scores: dict[str, list[float]]) -> list[WeakTopic] | None:
        client = EvaluationService._get_client()
        if client is None or not topic_scores:
            return None
        payload = {
            "topic_scores": {topic: [round(score * 100, 2) for score in scores] for topic, scores in topic_scores.items()}
        }
        prompt = (
            "You are an exam mentor.\n"
            "Given topic-wise scores, return strict JSON with key weak_topics.\n"
            "weak_topics should be an array of objects: topic, accuracy, suggestion.\n"
            "Include all topics sorted by low to high accuracy. Keep suggestions concise.\n\n"
            f"Input:\n{json.dumps(payload)}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = getattr(response, "output_text", "") or ""
            parsed = EvaluationService._extract_json(output_text)
            if not parsed:
                return None
            raw_topics = parsed.get("weak_topics", [])
            if not isinstance(raw_topics, list):
                return None
            results: list[WeakTopic] = []
            for item in raw_topics:
                if not isinstance(item, dict):
                    continue
                topic = str(item.get("topic", "")).strip()
                if not topic:
                    continue
                accuracy = float(item.get("accuracy", 0))
                suggestion = str(item.get("suggestion", "")).strip() or "Revise this topic with focused practice."
                results.append(WeakTopic(topic=topic, accuracy=round(max(0.0, min(100.0, accuracy)), 2), suggestion=suggestion))
            return sorted(results, key=lambda item: item.accuracy) if results else None
        except Exception:
            return None

    @staticmethod
    def _recommend_difficulty(total_score: float) -> str:
        if total_score < 50:
            return "easy"
        if total_score < 75:
            return "medium"
        return "hard"
