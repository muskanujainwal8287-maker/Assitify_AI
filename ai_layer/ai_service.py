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
    _PROMPT_CONTENT_LIMIT = 12000

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
    def summarize(text: str) -> str:
        sentence_count = AIService._summary_sentence_count_for_length(len(text))
        llm_result = AIService._summarize_with_llm(text=text, sentence_count=sentence_count)
        if llm_result:
            return llm_result

        # Fallback summary if OpenAI is unavailable or parsing fails.
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return "No usable content was found in the document."

        selected = AIService._pick_balanced_items(sentences, sentence_count)

        return " ".join(selected)

    @staticmethod
    def _summarize_with_llm(text: str, sentence_count: int) -> str | None:
        client = AIService._get_client()
        if client is None:
            return None

        target_length = f"{max(2, sentence_count - 1)}-{sentence_count + 1} sentences"
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are an educational assistant.\n"
            "Return strict JSON with exactly this key: summary (string).\n"
            f"Summary length target: {target_length}.\n"
            "Use only the provided content; do not hallucinate.\n"
            "Read the full content and summarize coverage across beginning, middle, and end.\n"
            "If multiple distinct topics are present, include each topic in a balanced way.\n"
            "Focus on factual content and avoid generic filler language.\n\n"
            f"Content:\n{prepared_content}"
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
    def recommend_key_points(text: str) -> list[str]:
        count = AIService._key_point_count_for_length(len(text))
        llm_key_points = AIService._recommend_key_points_with_llm(text=text, count=count)
        if llm_key_points:
            return llm_key_points

        return AIService._fallback_key_points(text=text, count=count)

    @staticmethod
    def _recommend_key_points_with_llm(text: str, count: int = 5) -> list[str] | None:
        client = AIService._get_client()
        if client is None:
            return None

        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are an educational assistant extracting study key points.\n"
            "Return strict JSON with exactly one key: key_points (array of strings).\n"
            f"Provide exactly {count} key points.\n"
            "Read the full content and summarize coverage across beginning, middle, and end.\n"
            "If multiple distinct topics are present, include each topic in a balanced way.\n"
            "Use only the provided content and do not hallucinate.\n\n"
            f"Content:\n{prepared_content}"
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

            key_points = AIService._finalize_key_points(raw_points=key_points_raw, source_text=text, count=count)
            if not key_points:
                return None
            return key_points
        except Exception:
            return None

    @staticmethod
    def _finalize_key_points(raw_points: list[Any], source_text: str, count: int) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for item in raw_points:
            point = str(item).strip()
            if not point:
                continue
            # Remove numbering/bullets returned by some model responses.
            point = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", point).strip()
            point = re.sub(r"\s+", " ", point)
            if len(point) < 20:
                continue
            normalized = re.sub(r"[^\w\s]", "", point).lower().strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(point)
            if len(cleaned) == count:
                return cleaned

        fallback = AIService._fallback_key_points(text=source_text, count=count)
        for point in fallback:
            normalized = re.sub(r"[^\w\s]", "", point).lower().strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(point)
            if len(cleaned) == count:
                break
        return cleaned

    @staticmethod
    def _fallback_key_points(text: str, count: int) -> list[str]:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 40]
        if sentences:
            selected = AIService._pick_balanced_items(sentences, count)
            return [sentence[:220] for sentence in selected]

        words = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", text)]
        return [f"Important concept: {term}" for term, _ in Counter(words).most_common(count)]

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
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are an educational assistant generating exam-prep questions.\n"
            "Return strict JSON with exactly one key: questions.\n"
            "questions must be an array of objects with keys: prompt, options, answer, topic.\n"
            f"question_type={question_type}, difficulty={difficulty}, count={count}, topic={chosen_topic}.\n"
            "Use only the provided content and do not hallucinate.\n"
            "Questions should cover the full content and avoid near-duplicates.\n"
            "If question_type is objective, provide exactly 4 options and one clearly correct answer.\n"
            "If question_type is subjective, options must be an empty array.\n\n"
            f"Content:\n{prepared_content}"
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
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are a teaching assistant.\n"
            "Answer the student's doubt using only the provided content.\n"
            "If content is insufficient, explicitly say what is missing.\n"
            "Keep the response concise, accurate, and easy to understand.\n"
            "Read the full content and summarize coverage across beginning, middle, and end.\n"
            "If multiple distinct topics are present, include each topic in a balanced way.\n"
            "Do not invent facts that are not present in content.\n\n"
            f"Content:\n{prepared_content}\n\n"
            f"Student doubt:\n{question}"
        )
        try:
            response = client.responses.create(model=settings.llm_model, input=prompt)
            output_text = (getattr(response, "output_text", "") or "").strip()
            return output_text or "I'am Sorry, Unable to find answer. Can you please Eleborate your Query. "
        except Exception:
            return "Something went wrong. Please try again later."

    @staticmethod
    def _prepare_content_for_prompt(text: str, limit: int | None = None) -> str:
        max_len = limit or AIService._PROMPT_CONTENT_LIMIT
        content = text.strip()
        if len(content) <= max_len:
            return content

        head_len = int(max_len * 0.7)
        tail_len = max_len - head_len
        head = content[:head_len].rstrip()
        tail = content[-tail_len:].lstrip()
        return f"{head}\n\n[... middle content omitted for length ...]\n\n{tail}"

    @staticmethod
    def _pick_balanced_items(items: list[str], count: int) -> list[str]:
        if count <= 0 or not items:
            return []
        if len(items) <= count:
            return items

        first_half_count = (count + 1) // 2
        second_half_count = count - first_half_count
        selected = items[:first_half_count]
        if second_half_count:
            selected.extend(items[-second_half_count:])
        return selected

    @staticmethod
    def _summary_sentence_count_for_length(content_len: int) -> int:
        if content_len < 1500:
            return 3
        if content_len < 5000:
            return 5
        if content_len < 12000:
            return 7
        return 9

    @staticmethod
    def _key_point_count_for_length(content_len: int) -> int:
        if content_len < 1500:
            return 3
        if content_len < 5000:
            return 5
        if content_len < 12000:
            return 7
        return 9
