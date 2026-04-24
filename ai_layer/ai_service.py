import re
import uuid
from collections import Counter

from ai_layer.schemas import Question


class AIService:
    @staticmethod
    def summarize(text: str, mode: str) -> tuple[str, list[str]]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return "No usable content was found in the document.", []

        if mode == "short":
            selected = sentences[:2]
        elif mode == "detailed":
            selected = sentences[:6]
        else:
            selected = sentences[:4]

        words = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", text)]
        key_points = [term for term, _ in Counter(words).most_common(5)]
        return " ".join(selected), key_points

    @staticmethod
    def generate_questions(
        text: str,
        question_type: str,
        difficulty: str,
        count: int,
        topic: str | None = None,
    ) -> list[Question]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 40]
        if not sentences:
            sentences = ["This content was too short; revise the topic and explain it in your own words."]

        chosen_topic = topic or "general"
        questions: list[Question] = []
        for i in range(count):
            source = sentences[i % len(sentences)]
            base_prompt = f"From this idea, explain: {source[:120]}"
            if question_type == "objective":
                options = [
                    "Concept definition",
                    "Example based answer",
                    "Reasoning and inference",
                    "None of these",
                ]
                answer = options[i % len(options)]
                prompt = f"{base_prompt}. Choose the best fit."
            else:
                options = []
                answer = source[:180]
                prompt = f"{base_prompt}. Write a short response."

            questions.append(
                Question(
                    id=str(uuid.uuid4()),
                    prompt=prompt,
                    question_type=question_type,
                    options=options,
                    answer=answer,
                    difficulty=difficulty,
                    topic=chosen_topic,
                )
            )
        return questions
