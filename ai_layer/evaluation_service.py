from collections import defaultdict

from ai_layer.schemas import AnswerReview, WeakTopic


class EvaluationService:
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
            score = EvaluationService._score_answer(user_answer, expected_answer)
            is_correct = score >= 0.6
            topic_scores[topic].append(score)
            explanation = (
                "Strong answer. Keep this structure."
                if is_correct
                else "Partially correct. Focus on key concept terms and examples."
            )

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
    def _score_answer(user_answer: str, expected_answer: str) -> float:
        user_tokens = {token.lower() for token in user_answer.split() if token.strip()}
        expected_tokens = {token.lower() for token in expected_answer.split() if token.strip()}
        if not expected_tokens:
            return 0.0
        overlap = len(user_tokens.intersection(expected_tokens))
        return min(1.0, overlap / len(expected_tokens))

    @staticmethod
    def _weak_topics(topic_scores: dict[str, list[float]]) -> list[WeakTopic]:
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
    def _recommend_difficulty(total_score: float) -> str:
        if total_score < 50:
            return "easy"
        if total_score < 75:
            return "medium"
        return "hard"
