"""Standard meeting mode prompt template."""
from .base_prompt import BasePrompt


class MeetingPrompt(BasePrompt):
    """Prompt template for standard meeting summarization."""

    def get_system_prompt(self) -> str:
        """Returns the system prompt for meeting mode."""
        return """You are an expert meeting assistant. Analyze the meeting transcript and provide a comprehensive summary in Russian.

Focus on:
- General discussion topics
- Key decisions made
- Action items and tasks assigned to participants

The transcript may contain multiple speakers. Try to identify speakers and assign tasks accordingly."""

    def get_user_prompt_template(self) -> str:
        """Returns the user prompt template for meeting mode."""
        return """Meeting Date/Time: {date_str}

Transcript:
{transcript}

Please provide a concise summary in Markdown format with the following sections:

## Дата и время встречи
{date_str}

## Ключевые темы
- (List of main topics discussed)

## Решения
- (List of agreed decisions)

## Задачи
- [ ] Спикер N (если возможно определить) - (Task description)

If any section is not applicable, state "Не указано" or "Нет".
Try to assign tasks to specific speakers based on the conversation context."""
