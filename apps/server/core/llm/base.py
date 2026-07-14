from abc import ABC, abstractmethod
from datetime import datetime
import re


TITLE_SYSTEM_PROMPT = """You are a meeting title classifier. Return one short Russian folder title for the meeting transcript.

Common title patterns:
- "1-1 с <имя>" for one-on-one meetings
- "Отчет для меня" when someone reports status to the user
- "Отчет для тимлида" when the user reports status to a team lead
- "Дейлик <команда/проект>" for daily standups
- "Планы <команда/проект>" for team planning discussions

Rules:
- Return only the title, no quotes, no markdown, no punctuation at the end.
- Keep it short: 2-7 words, up to 60 characters.
- Do not include date or time.
- If unsure, return a specific concise topic, not a generic "Встреча".
"""


def build_title_user_prompt(transcript: str, mode: str = "meeting") -> str:
    """Build a compact prompt for generating a meeting folder title."""
    transcript_excerpt = transcript.strip()[:12000]
    return f"""Mode: {mode}

Transcript:
{transcript_excerpt}

Return only the short folder title."""


def normalize_meeting_title(title: str, default: str = "Встреча") -> str:
    """Normalize an LLM title so it is safe to use as part of a folder name."""
    if not title:
        return default

    cleaned = title.strip()
    cleaned = cleaned.splitlines()[0].strip()
    cleaned = cleaned.strip("`'\"“”«» ")
    cleaned = re.sub(r"[/:\\*?\"<>|]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-_")

    if not cleaned:
        return default

    return cleaned[:60].rstrip(" .-_")

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def summarize(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """
        Generates a summary from the transcript.

        Args:
            transcript: The meeting transcript text.
            meeting_datetime: Optional datetime of when the meeting occurred.
            mode: Summarization mode ("meeting", "english", "interview"). Defaults to "meeting".

        Returns:
            Formatted Markdown summary.
        """
        pass

    def generate_title(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """
        Generates a short folder title from the transcript.

        Providers can override this with their native API calls.
        """
        raise NotImplementedError("Title generation is not implemented for this provider.")
