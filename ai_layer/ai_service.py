import logging
import re
import uuid
from collections import Counter
from typing import Any

from ai_layer.llm_result import LLMResult
from ai_layer.llm_utils import call_llm, extract_json_from_text
from ai_layer.schemas import ChapterNotes, Question, TopicNotes

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
        source_sentences = len([s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()])
        sentence_count = min(sentence_count,max(1, source_sentences // 4) if source_sentences else sentence_count,)
        low = max(1, sentence_count - 1)
        high = max(low, sentence_count)
        target_length = f"{low}-{high} sentences"
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
            f"Provide Keypoints on the basis of content length if short then provide 3 key points if medium then provide 5 key points if long then provide 7 key points if really long provide as many as needed.\n"
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

        key_points = AIService._finalize_key_points(raw_points=key_points_raw, count=count)
        if not key_points:
            return None, "OpenAI key points failed validation (empty or too short)"
        return key_points, None

    @staticmethod
    def recommend_topic_key_points(text: str, topic: str) -> LLMResult[list[str]]:
        count = AIService._key_point_count_for_length(len(text))
        llm_key_points, error = AIService._recommend_topic_key_points_with_llm(
            text=text, topic=topic, count=count
        )
        if llm_key_points:
            return LLMResult.from_openai(llm_key_points)

        fallback = AIService._fallback_topic_key_points(text=text, topic=topic, count=count)
        reason = error or "OpenAI topic key-point response could not be parsed"
        logger.info("Using fallback topic key points: %s", reason)
        return LLMResult.from_fallback(fallback, error=error, reason=reason)

    @staticmethod
    def _recommend_topic_key_points_with_llm(
        text: str, topic: str, count: int
    ) -> tuple[list[str] | None, str | None]:
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are an educational assistant extracting study key points for one topic.\n"
            "Return strict JSON with exactly one key: key_points (array of strings).\n"
            f"Topic: {topic}\n"
            f"Provide Keypoints on the basis of content length if short then provide 3 key points if medium then provide 5 key points if long then provide 7 key points if really long provide as many as needed.\n"
            "Provide keypoints that are specifically about this topic from provided content.\n"
            "Ignore content that is not related to the topic.\n"
            "Each key point must be at least 20 characters and written as a concise bullet.\n"
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

        key_points = AIService._finalize_key_points(raw_points=key_points_raw, count=count)
        if not key_points:
            return None, "OpenAI topic key points failed validation (empty or too short)"
        return key_points, None

    @staticmethod
    def _fallback_topic_key_points(text: str, topic: str, count: int) -> list[str]:
        topic_l = topic.lower()
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 40]
        related = [s for s in sentences if topic_l in s.lower()]
        pool = related or sentences
        if pool:
            selected = AIService._pick_balanced_items(pool, count)
            return [sentence[:220] for sentence in selected]
        return [f"No key points found for topic: {topic}"]

    @staticmethod
    def _finalize_key_points(raw_points: list[Any], count: int) -> list[str]:
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
    def generate_notes(
        sections: list[dict[str, Any]],
        *,
        topic: str | None = None,
    ) -> LLMResult[list[ChapterNotes]]:
        llm_notes, error = AIService._generate_notes_with_llm(sections=sections, topic=topic)
        if llm_notes:
            return LLMResult.from_openai(llm_notes)

        fallback = AIService._fallback_notes(sections=sections, topic=topic)
        reason = error or "OpenAI notes response could not be parsed"
        logger.info("Using fallback notes: %s", reason)
        return LLMResult.from_fallback(fallback, error=error, reason=reason)

    @staticmethod
    def _generate_notes_with_llm(
        sections: list[dict[str, Any]],
        *,
        topic: str | None,
    ) -> tuple[list[ChapterNotes] | None, str | None]:
        labeled_parts: list[str] = []
        for index, section in enumerate(sections, start=1):
            title = str(section.get("title") or f"Chapter {index}").strip()
            body = AIService._prepare_content_for_prompt(str(section.get("text") or ""), limit=2500)
            labeled_parts.append(f"### {title}\n{body}")
        prepared_content = AIService._prepare_content_for_prompt("\n\n".join(labeled_parts), limit=14000)

        topic_line = (
            f"Include only this topic: {topic.strip()}. Drop chapters that do not cover it.\n"
            if topic and topic.strip()
            else ""
        )
        prompt = (
            "You are an educational assistant writing revision notes for exam prep.\n"
            "Return strict JSON with exactly one key: chapters (array of objects).\n"
            "Each chapter object must have: title (string), topics (array).\n"
            "Each topic object must have: topic (string), notes (array of short bullet-point strings).\n"
            "Structure must be: chapter -> topics inside that chapter -> notes as bullet points.\n"
            "Keep  topics on the basis of content length if short then provide 1-2 topics if medium then provide 3-5 topics if long then provide 4-6 topics if really long provide as many as needed per chapter and 2-20 (20 if its a really large topic to cover) note points per topic.\n"
            "Each note must be one concise bullet (not a paragraph), at least 20 characters.\n"
            "Use the provided chapter headings as chapter titles when possible.\n"
            "Key points must be related to the topic and the content and do not hallucinate or make up facts.\n"
            f"{topic_line}"
            "Use only the provided content and do not hallucinate.\n\n"
            f"Content:\n{prepared_content}"
        )
        output_text, error = call_llm(prompt, json_mode=True)
        if error:
            return None, error

        parsed, parse_error = extract_json_from_text(output_text or "")
        if not parsed:
            return None, parse_error

        chapters_raw = parsed.get("chapters", [])
        if not isinstance(chapters_raw, list):
            return None, "OpenAI JSON response 'chapters' was not an array"

        chapter_lookup = {
            str(section.get("title") or "").strip().lower(): section for section in sections
        }
        chapters: list[ChapterNotes] = []
        for item in chapters_raw:
            chapter = AIService._parse_chapter_notes(item, chapter_lookup=chapter_lookup, topic=topic)
            if chapter:
                chapters.append(chapter)

        if not chapters:
            return None, "OpenAI notes failed validation (empty chapters, topics, or points)"
        return chapters, None

    @staticmethod
    def _parse_chapter_notes(
        item: Any,
        *,
        chapter_lookup: dict[str, dict[str, Any]],
        topic: str | None,
    ) -> ChapterNotes | None:
        if not isinstance(item, dict):
            return None
        title = str(item.get("title") or "").strip()
        if not title:
            return None
        topics_raw = item.get("topics", [])
        if not isinstance(topics_raw, list):
            return None

        topic_filter = (topic or "").strip().lower()
        topics: list[TopicNotes] = []
        for topic_item in topics_raw:
            if not isinstance(topic_item, dict):
                continue
            topic_name = str(topic_item.get("topic") or "").strip()
            if not topic_name:
                continue
            if topic_filter and topic_filter not in topic_name.lower():
                continue
            points = AIService._finalize_note_points(topic_item.get("notes", []))
            if not points:
                continue
            topics.append(TopicNotes(topic=topic_name[:150], notes=points))

        if not topics:
            return None

        matched = chapter_lookup.get(title.lower())
        return ChapterNotes(
            title=title[:150],
            chapter_id=str(matched["chapter_id"]) if matched and matched.get("chapter_id") else None,
            chapter_number=int(matched["chapter_number"]) if matched and matched.get("chapter_number") else None,
            topics=topics,
        )

    @staticmethod
    def _finalize_note_points(raw_points: Any) -> list[str]:
        if not isinstance(raw_points, list):
            return []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in raw_points:
            point = str(item).strip()
            if not point:
                continue
            point = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", point).strip()
            point = re.sub(r"\s+", " ", point)
            if len(point) < 12:
                continue
            normalized = re.sub(r"[^\w\s]", "", point).lower().strip()
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(point)
            if len(cleaned) == 8:
                break
        return cleaned

    @staticmethod
    def _fallback_notes(
        sections: list[dict[str, Any]],
        *,
        topic: str | None,
    ) -> list[ChapterNotes]:
        chapters: list[ChapterNotes] = []
        topic_filter = (topic or "").strip()
        for index, section in enumerate(sections, start=1):
            title = str(section.get("title") or f"Chapter {index}").strip()
            text = str(section.get("text") or "")
            if topic_filter and topic_filter.lower() not in f"{title}\n{text}".lower():
                continue
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 12]
            points = [item[:180] for item in AIService._pick_balanced_items(sentences, 6)]
            if not points:
                points = ["No usable notes were found in this chapter."]
            topic_name = topic_filter or title[:80] or "Overview"
            chapters.append(
                ChapterNotes(
                    title=title[:150],
                    chapter_id=str(section["chapter_id"]) if section.get("chapter_id") else None,
                    chapter_number=int(section["chapter_number"]) if section.get("chapter_number") else None,
                    topics=[TopicNotes(topic=topic_name, notes=points)],
                )
            )
        if chapters:
            return chapters
        return [
            ChapterNotes(
                title="Full Document",
                chapter_number=1,
                topics=[
                    TopicNotes(
                        topic=topic_filter or "General",
                        notes=["No usable content was found in the document."],
                    )
                ],
            )
        ]

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
    def answer_doubt(
        text: str,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> LLMResult[str]:
        prepared_content = AIService._prepare_content_for_prompt(text)
        history_block = AIService._format_chat_history(history or [])
        prompt = (
            "You are a teaching assistant Bot for AI Study Companion running a question-asking tutoring session.\n"
            "The student just replied in a live two-way chat.\n"
            "Briefly respond to their message using only the provided content.\n"
            "Then ALWAYS end with one clear study question for the student to answer next.\n"
            "Use conversation history for follow-ups like 'explain that' or short answers.\n"
            "If content is insufficient, say what is missing, then still ask one question from what is available.\n"
            "Keep the whole reply concise and easy to understand and do not hallucinate or make up facts.\n"
            "Do not invent facts that are not present in content.\n\n"
            f"Content:\n{prepared_content}\n\n"
            f"{history_block}"
            f"Student:\n{question}"
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
    def start_doubt_session(text: str) -> LLMResult[str]:
        prepared_content = AIService._prepare_content_for_prompt(text)
        prompt = (
            "You are starting a question-asking tutoring session for exam prep.\n"
            "Using only the provided content, write a short tutor opening message that:\n"
            "1) greets the student in one sentence,\n"
            "2) names the main topic of the material,\n"
            "3) asks ONE clear question the student should answer first.\n"
            "Do not answer the question yourself. Do not invent facts.\n\n"
            f"Content:\n{prepared_content}"
        )
        output_text, error = call_llm(prompt)
        if error:
            fallback = AIService._fallback_session_opener(text)
            logger.info("Doubt session start failed: %s", error)
            return LLMResult.from_fallback(fallback, error=error, reason=error)

        message = (output_text or "").strip()
        if not message:
            return LLMResult.from_fallback(AIService._fallback_session_opener(text), reason="empty opener")
        return LLMResult.from_openai(message)

    @staticmethod
    def _fallback_session_opener(text: str) -> str:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) >= 20]
        seed = sentences[0][:180] if sentences else "this document"
        return (
            "Hi! Let's study this material together. "
            f"To start, can you explain this in your own words: {seed}"
        )

    @staticmethod
    def _format_chat_history(history: list[dict[str, str]], limit: int = 10) -> str:
        turns = history[-limit:]
        if not turns:
            return ""
        lines = ["Conversation so far:"]
        for turn in turns:
            role = "Student" if turn.get("role") == "user" else "Tutor"
            content = str(turn.get("content") or "").strip()
            if not content:
                continue
            lines.append(f"{role}: {content}")
        lines.append("")
        return "\n".join(lines) + "\n"

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
        return 10

    @staticmethod
    def _key_point_count_for_length(content_len: int) -> int:
        if content_len < 1500:
            return 3
        if content_len < 5000:
            return 5
        if content_len < 12000:
            return 7
        return 10
