import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from ai_layer.llm_utils import call_llm, extract_json_from_text
from ai_layer.schemas import AnswerReview, WeakTopic

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    reviews: list[AnswerReview]
    total_score: float
    weak_topics: list[WeakTopic]
    recommended_difficulty: str
    source: Literal["openai", "fallback", "mixed"]
    scoring_source: Literal["openai", "fallback", "mixed"]
    weak_topics_source: Literal["openai", "fallback"]
    llm_error: str | None = None
    fallback_reason: str | None = None


class EvaluationService:
    @staticmethod
    def review_answers(
        answers: dict[str, str],
        expected: dict[str, dict],
    ) -> EvaluationResult:
        topic_scores: dict[str, list[float]] = defaultdict(list)
        reviews: list[AnswerReview] = []
        llm_errors: list[str] = []
        openai_scores = 0
        fallback_scores = 0

        for question_id, user_answer in answers.items():
            expected_item = expected.get(question_id)
            if not expected_item:
                continue

            expected_answer = expected_item["answer"]
            topic = expected_item["topic"]
            score, explanation, score_source, score_error = EvaluationService._score_answer(
                user_answer, expected_answer
            )
            if score_source == "openai":
                openai_scores += 1
            else:
                fallback_scores += 1
            if score_error:
                llm_errors.append(score_error)

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
        weak_topics, weak_topics_source, weak_topics_error = EvaluationService._weak_topics(topic_scores)
        if weak_topics_error:
            llm_errors.append(weak_topics_error)

        scoring_source = EvaluationService._aggregate_source(openai_scores, fallback_scores)
        overall_source = EvaluationService._aggregate_source(
            openai_scores + (1 if weak_topics_source == "openai" else 0),
            fallback_scores + (1 if weak_topics_source == "fallback" else 0),
        )
        unique_errors = list(dict.fromkeys(llm_errors))
        fallback_reason = None
        if overall_source != "openai":
            fallback_reason = unique_errors[0] if unique_errors else "Local scoring/topic heuristics were used"

        recommended_difficulty = EvaluationService._recommend_difficulty(total_score)
        return EvaluationResult(
            reviews=reviews,
            total_score=total_score,
            weak_topics=weak_topics,
            recommended_difficulty=recommended_difficulty,
            source=overall_source,
            scoring_source=scoring_source,
            weak_topics_source=weak_topics_source,
            llm_error="; ".join(unique_errors) if unique_errors else None,
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _aggregate_source(openai_count: int, fallback_count: int) -> Literal["openai", "fallback", "mixed"]:
        if openai_count > 0 and fallback_count > 0:
            return "mixed"
        if openai_count > 0:
            return "openai"
        return "fallback"

    @staticmethod
    def _score_answer(user_answer: str, expected_answer: str) -> tuple[float, str, Literal["openai", "fallback"], str | None]:
        llm_score, llm_error = EvaluationService._score_with_llm(
            user_answer=user_answer, expected_answer=expected_answer
        )
        if llm_score:
            return llm_score[0], llm_score[1], "openai", None

        user_tokens = {token.lower() for token in user_answer.split() if token.strip()}
        expected_tokens = {token.lower() for token in expected_answer.split() if token.strip()}
        if not expected_tokens:
            return 0.0, "Unable to evaluate because expected answer is empty.", "fallback", llm_error

        overlap = len(user_tokens.intersection(expected_tokens))
        score = min(1.0, overlap / len(expected_tokens))
        explanation = (
            "Strong answer. Keep this structure."
            if score >= 0.6
            else "Partially correct. Focus on key concept terms and examples."
        )
        if llm_error:
            explanation = f"{explanation} (LLM scoring unavailable: {llm_error})"
        return score, explanation, "fallback", llm_error

    @staticmethod
    def _score_with_llm(user_answer: str, expected_answer: str) -> tuple[tuple[float, str] | None, str | None]:
        prompt = (
            "You evaluate a student's answer.\n"
            "Return strict JSON with keys: score_0_to_1 (number), explanation (string).\n"
            "Score should reward conceptual correctness over exact wording.\n\n"
            f"Expected answer:\n{expected_answer}\n\n"
            f"Student answer:\n{user_answer}"
        )
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        try:
            score = float(parsed.get("score_0_to_1", 0))
        except (TypeError, ValueError):
            return None, "OpenAI score_0_to_1 was not a valid number"
        explanation = str(parsed.get("explanation", "")).strip()
        score = max(0.0, min(1.0, score))
        if not explanation:
            explanation = "Evaluation generated."
        return (score, explanation), None

    @staticmethod
    def _weak_topics(
        topic_scores: dict[str, list[float]],
    ) -> tuple[list[WeakTopic], Literal["openai", "fallback"], str | None]:
        llm_topics, llm_error = EvaluationService._weak_topics_with_llm(topic_scores)
        if llm_topics is not None:
            return llm_topics, "openai", None

        results: list[WeakTopic] = []
        for topic, scores in topic_scores.items():
            accuracy = round(sum(scores) / len(scores) * 100, 2)
            if accuracy < 65:
                suggestion = "Revise basics and solve 5 more practice questions."
            else:
                suggestion = "Maintain practice with medium and hard questions."
            results.append(WeakTopic(topic=topic, accuracy=accuracy, suggestion=suggestion))

        if llm_error:
            logger.info("Using fallback weak-topic suggestions: %s", llm_error)
        return sorted(results, key=lambda item: item.accuracy), "fallback", llm_error

    @staticmethod
    def _weak_topics_with_llm(topic_scores: dict[str, list[float]]) -> tuple[list[WeakTopic] | None, str | None]:
        if not topic_scores:
            return [], None

        payload = {
            "topic_scores": {
                topic: [round(score * 100, 2) for score in scores] for topic, scores in topic_scores.items()
            }
        }
        prompt = (
            "You are an exam mentor.\n"
            "Given topic-wise scores, return strict JSON with key weak_topics.\n"
            "weak_topics should be an array of objects: topic, accuracy, suggestion.\n"
            "Include all topics sorted by low to high accuracy. Keep suggestions concise.\n\n"
            f"Input:\n{json.dumps(payload)}"
        )
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        raw_topics = parsed.get("weak_topics", [])
        if not isinstance(raw_topics, list):
            return None, "OpenAI JSON response 'weak_topics' was not an array"

        results: list[WeakTopic] = []
        for item in raw_topics:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic", "")).strip()
            if not topic:
                continue
            accuracy = float(item.get("accuracy", 0))
            suggestion = str(item.get("suggestion", "")).strip() or "Revise this topic with focused practice."
            results.append(
                WeakTopic(topic=topic, accuracy=round(max(0.0, min(100.0, accuracy)), 2), suggestion=suggestion)
            )
        if results:
            return sorted(results, key=lambda item: item.accuracy), None
        return None, "OpenAI weak_topics response contained no valid entries"

    @staticmethod
    def _recommend_difficulty(total_score: float) -> str:
        if total_score < 50:
            return "easy"
        if total_score < 75:
            return "medium"
        return "hard"
