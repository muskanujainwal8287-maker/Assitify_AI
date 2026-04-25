import json
import re
import uuid
from collections import Counter
from typing import Any

from openai import OpenAI

from ai_layer.config import settings
from ai_layer.schemas import Question


class AIService:
    _client: OpenAI | None = None

    @classmethod
    def _get_client(cls) -> OpenAI | None:
        if not settings.openai_api_key:
            return None
        if cls._client is None:
            cls._client = OpenAI(api_key=settings.openai_api_key)
        return cls._client

    @staticmethod
    def _extract_json_from_text(content: str) -> dict[str, Any] | None:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = content[start : end + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def summarize(text: str, mode: str) -> str:
        llm_result = AIService._summarize_with_llm(text=text, mode=mode)
        if llm_result:
            return llm_result

        # Fallback summary if OpenAI is unavailable or parsing fails.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return "No usable content was found in the document."

        if mode == "short":
            selected = sentences[:2]
        elif mode == "detailed":
            selected = sentences[:6]
        else:
            selected = sentences[:4]

        return " ".join(selected)

    @staticmethod
    def _summarize_with_llm(text: str, mode: str) -> str | None:
        client = AIService._get_client()
        if client is None:
            return None

        target_length = {"short": "2-3 lines", "standard": "5-7 lines", "detailed": "10-14 lines"}.get(mode, "5-7 lines")
        prompt = (
            "You are an educational assistant.\n"
            "Return strict JSON with keys: summary (string)\n"
            f"Summary length target: {target_length}.\n"
            "Use only the provided content, avoid hallucinations.\n\n"
            f"Content:\n{text[:12000]}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = getattr(response, "output_text", "") or ""
            parsed = AIService._extract_json_from_text(output_text)
            if not parsed:
                return None
            summary = str(parsed.get("summary", "")).strip()
            if summary:
                return summary
            return None
        except Exception:
            return None

    @staticmethod
    def recommend_key_points(text: str, count: int = 5) -> list[str]:
        llm_key_points = AIService._recommend_key_points_with_llm(text=text, count=count)
        if llm_key_points:
            return llm_key_points

        words = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", text)]
        return [term for term, _ in Counter(words).most_common(count)]

    @staticmethod
    def _recommend_key_points_with_llm(text: str, count: int = 5) -> list[str] | None:
        client = AIService._get_client()
        if client is None:
            return None

        prompt = (
            "You recommend study key points from material.\n"
            "Return strict JSON with key 'key_points' as an array of concise strings.\n"
            f"Provide exactly {count} key points.\n"
            "Use only the provided content, avoid hallucinations.\n\n"
            f"Content:\n{text[:12000]}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = getattr(response, "output_text", "") or ""
            parsed = AIService._extract_json_from_text(output_text)
            if not parsed:
                return None

            key_points_raw = parsed.get("key_points", [])
            if not isinstance(key_points_raw, list):
                return None

            key_points = [str(item).strip() for item in key_points_raw if str(item).strip()]
            if not key_points:
                return None
            return key_points[:count]
        except Exception:
            return None

    @staticmethod
    def generate_questions(
        text: str,
        question_type: str,
        difficulty: str,
        count: int,
        topic: str | None = None,
    ) -> list[Question]:
        llm_questions = AIService._generate_questions_with_llm(
            text=text, question_type=question_type, difficulty=difficulty, count=count, topic=topic
        )
        if llm_questions:
            return llm_questions

        # Fallback question generation if OpenAI is unavailable.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 40]
        if not sentences:
            sentences = ["This content was too short. Can't generate questions."]

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

    @staticmethod
    def _generate_questions_with_llm(
        text: str,
        question_type: str,
        difficulty: str,
        count: int,
        topic: str | None = None,
    ) -> list[Question] | None:
        client = AIService._get_client()
        if client is None:
            return None

        chosen_topic = topic or "general"
        prompt = (
            "You generate exam prep questions from study material.\n"
            "Return strict JSON with key 'questions'.\n"
            "questions must be an array of objects with keys: prompt, options, answer, topic.\n"
            f"question_type={question_type}, difficulty={difficulty}, count={count}, topic={chosen_topic}.\n"
            "If question_type is objective, provide exactly 4 options. "
            "If subjective, options should be an empty array.\n\n"
            f"Content:\n{text[:12000]}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = getattr(response, "output_text", "") or ""
            parsed = AIService._extract_json_from_text(output_text)
            if not parsed:
                return None
            questions_raw = parsed.get("questions", [])
            if not isinstance(questions_raw, list):
                return None

            parsed_questions: list[Question] = []
            for item in questions_raw[:count]:
                if not isinstance(item, dict):
                    continue
                prompt_text = str(item.get("prompt", "")).strip()
                answer_text = str(item.get("answer", "")).strip()
                item_topic = str(item.get("topic", chosen_topic) or chosen_topic).strip() or chosen_topic
                options_raw = item.get("options", [])
                options = [str(opt).strip() for opt in options_raw] if isinstance(options_raw, list) else []
                if question_type == "objective" and len(options) != 4:
                    continue
                if not prompt_text or not answer_text:
                    continue
                parsed_questions.append(
                    Question(
                        id=str(uuid.uuid4()),
                        prompt=prompt_text,
                        question_type=question_type,
                        options=options if question_type == "objective" else [],
                        answer=answer_text,
                        difficulty=difficulty,
                        topic=item_topic,
                    )
                )
            return parsed_questions or None
        except Exception:
            return None

    @staticmethod
    def answer_doubt(text: str, question: str) -> str:
        client = AIService._get_client()
        if client is None:
            return (
                "OpenAI key is not configured. Please set OPENAI_API_KEY in .env to use doubt support."
            )
        prompt = (
            "You are a teaching assistant. Answer the student's doubt using only provided content.\n"
            "If content is insufficient, clearly say what is missing.\n\n"
            f"Content:\n{text[:12000]}\n\n"
            f"Student doubt:\n{question}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = (getattr(response, "output_text", "") or "").strip()
            return output_text or "I'am Sorry, Unable to find answer. Can you please Eleborate your Query. "
        except Exception:
            return "Something went wrong. Please try again later."
