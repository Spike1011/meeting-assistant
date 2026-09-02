from datetime import datetime
import re

from openai import OpenAI

from .base import LLMProvider, TITLE_SYSTEM_PROMPT, build_title_user_prompt, normalize_meeting_title
from core.utils.prompt_manager import PromptManager


class LocalProvider(LLMProvider):
    """Generates summaries using a local OpenAI-compatible LLM server."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "Qwen3:latest",
        base_url: str = "http://localhost:11434/v1",
    ):
        super().__init__(api_key, model_name)
        self.client = OpenAI(api_key=api_key or "local", base_url=base_url)

    def summarize(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """Generate a summary using the configured local model."""
        print(f"Generating summary with local LLM ({self.model_name}) in {mode} mode...")
        prompt_instance = PromptManager.get_prompt(mode)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": prompt_instance.get_system_prompt()},
                {"role": "user", "content": prompt_instance.format_user_prompt(transcript, meeting_datetime)},
            ],
            stream=False,
        )
        summary = response.choices[0].message.content
        return self._remove_unverified_speaker_names(summary, transcript)

    @staticmethod
    def _remove_unverified_speaker_names(summary: str, transcript: str) -> str:
        """Remove speaker names that are absent from the source transcript.

        This is a final safeguard against a local model inventing a name. It does
        not prove that a mentioned name belongs to a speaker; the prompt requires
        that evidence. It does guarantee that a fabricated name such as "Маша"
        cannot appear when it never occurs in the transcript.
        """
        def is_present(name: str) -> bool:
            normalized_name = name.strip()
            return bool(
                normalized_name
                and re.search(rf"(?<!\w){re.escape(normalized_name)}(?!\w)", transcript, re.IGNORECASE)
            )

        def replace_task_label(match: re.Match) -> str:
            speaker, name = match.group(1), match.group(2)
            return match.group(0) if is_present(name) else f"Спикер {speaker}"

        summary = re.sub(
            r"Спикер\s+(\d+)\s*\(([^()]+)\)",
            replace_task_label,
            summary,
        )

        def replace_participant_line(match: re.Match) -> str:
            prefix, speaker, name = match.group(1), match.group(2), match.group(3)
            return match.group(0) if is_present(name) else f"{prefix}Спикер {speaker}"

        return re.sub(
            r"(?m)^(\s*-\s*)Спикер\s+(\d+)\s*[—-]\s*([^;\n]+)(?:;[^\n]*)?$",
            replace_participant_line,
            summary,
        )

    def generate_title(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """Generate a concise title using the configured local model."""
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": TITLE_SYSTEM_PROMPT},
                {"role": "user", "content": build_title_user_prompt(transcript, mode)},
            ],
            stream=False,
            temperature=0.2,
        )
        return normalize_meeting_title(response.choices[0].message.content)
