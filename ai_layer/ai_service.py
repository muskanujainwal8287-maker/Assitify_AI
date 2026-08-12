import logging
import re
import uuid
from collections import Counter
from typing import Any

from ai_layer.llm_result import LLMResult
from ai_layer.llm_utils import call_llm, extract_json_from_text
from ai_layer.schemas import Question

logger = logging.getLogger(__name__)


class AIService:
    _PROMPT_CONTENT_LIMIT = 12000

    @staticmethod
    def summarize(text: str) -> LLMResult[str]:
        sentence_count = AIService._summary_sentence_count_for_length(len(text))
        llm_result, error = AIService._summarize_with_llm(text=text, sentence_count=sentence_count)
        if llm_result:
            return LLMResult.from_openai(llm_result)

        fallback = AIService._fallback_summary(text, sentence_count)
        reason = error or "OpenAI summary response could not be parsed"
        logger.info("Using fallback summary: %s", reason)
        return LLMResult.from_fallback(fallback, error=error, reason=reason)

    @staticmethod
    def _summarize_with_llm(text: str, sentence_count: int) -> tuple[str | None, str | None]:
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
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        summary = str(parsed.get("summary", "")).strip()
        if summary:
            return summary, None
        return None, "OpenAI JSON response did not include a non-empty 'summary' field"

    @staticmethod
    def _fallback_summary(text: str, sentence_count: int) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return "No usable content was found in the document."
        selected = AIService._pick_balanced_items(sentences, sentence_count)
        return " ".join(selected)

    @staticmethod
    def recommend_key_points(text: str) -> LLMResult[list[str]]:
        count = AIService._key_point_count_for_length(len(text))
        llm_key_points, error = AIService._recommend_key_points_with_llm(text=text, count=count)
        if llm_key_points:
            return LLMResult.from_openai(llm_key_points)

        fallback = AIService._fallback_key_points(text=text, count=count)
        reason = error or "OpenAI key-point response could not be parsed"
        logger.info("Using fallback key points: %s", reason)
        return LLMResult.from_fallback(fallback, error=error, reason=reason)

    @staticmethod
    def _recommend_key_points_with_llm(text: str, count: int = 5) -> tuple[list[str] | None, str | None]:
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are an educational assistant extracting study key points.\n"
            "Return strict JSON with exactly one key: key_points (array of strings).\n"
            f"Provide exactly {count} key points.\n"
            "Each key point must be at least 20 characters.\n"
            "Read the full content and summarize coverage across beginning, middle, and end.\n"
            "If multiple distinct topics are present, include each topic in a balanced way.\n"
            "Use only the provided content and do not hallucinate.\n\n"
            f"Content:\n{prepared_content}"
        )
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        key_points_raw = parsed.get("key_points", [])
        if not isinstance(key_points_raw, list):
            return None, "OpenAI JSON response 'key_points' was not an array"

        key_points = AIService._finalize_key_points(raw_points=key_points_raw, source_text=text, count=count)
        if not key_points:
            return None, "OpenAI key points failed validation (empty or too short)"
        return key_points, None

    @staticmethod
    def _finalize_key_points(raw_points: list[Any], source_text: str, count: int) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()

        for item in raw_points:
            point = str(item).strip()
            if not point:
                continue
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
    ) -> LLMResult[list[Question]]:
        llm_questions, error = AIService._generate_questions_with_llm(
            text=text, question_type=question_type, difficulty=difficulty, count=count, topic=topic
        )
        if llm_questions:
            return LLMResult.from_openai(llm_questions)

        fallback = AIService._fallback_questions(
            text=text, question_type=question_type, difficulty=difficulty, count=count, topic=topic
        )
        reason = error or "OpenAI question response could not be parsed"
        logger.info("Using fallback questions: %s", reason)
        return LLMResult.from_fallback(fallback, error=error, reason=reason)

    @staticmethod
    def _fallback_questions(
        text: str,
        question_type: str,
        difficulty: str,
        count: int,
        topic: str | None,
    ) -> list[Question]:
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
    ) -> tuple[list[Question] | None, str | None]:
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
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        questions_raw = parsed.get("questions", [])
        if not isinstance(questions_raw, list):
            return None, "OpenAI JSON response 'questions' was not an array"

        parsed_questions: list[Question] = []
        skipped = 0
        for item in questions_raw[: count * 2]:
            if not isinstance(item, dict):
                skipped += 1
                continue
            prompt_text = str(item.get("prompt", "")).strip()
            answer_text = str(item.get("answer", "")).strip()
            item_topic = str(item.get("topic", chosen_topic) or chosen_topic).strip() or chosen_topic
            options_raw = item.get("options", [])
            options = [str(opt).strip() for opt in options_raw] if isinstance(options_raw, list) else []
            if question_type == "objective" and len(options) != 4:
                skipped += 1
                continue
            if not prompt_text or not answer_text:
                skipped += 1
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
            if len(parsed_questions) == count:
                break

        if parsed_questions:
            return parsed_questions, None
        detail = f"OpenAI returned no valid questions ({skipped} item(s) failed validation)"
        return None, detail

    @staticmethod
    def answer_doubt(text: str, question: str) -> LLMResult[str]:
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
        output_text, error = call_llm(prompt)
        if error:
            fallback_answer = (
                f"Unable to reach OpenAI: {error}. "
                "Please verify OPENAI_API_KEY, LLM_MODEL, and billing, then try again."
            )
            logger.info("Doubt answering failed: %s", error)
            return LLMResult.from_fallback(fallback_answer, error=error, reason=error)

        answer = output_text or "I am sorry, unable to find an answer. Can you please elaborate your query?"
        return LLMResult.from_openai(answer)

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
