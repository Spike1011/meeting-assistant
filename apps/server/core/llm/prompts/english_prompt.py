"""English lesson mode prompt template."""
from .base_prompt import BasePrompt


class EnglishPrompt(BasePrompt):
    """Prompt template for English lesson summarization."""

    def get_system_prompt(self) -> str:
        """Returns the system prompt for English lesson mode."""
        return """You are an expert English language learning assistant. Analyze the English lesson transcript and provide a structured summary in Russian.

IMPORTANT AUDIO CHANNEL MAPPING:
- Channels 1-2: Teacher's audio (feedback, explanations, corrections)
- Channel 3: Student's audio (your responses and questions)

Focus on:
- Teacher's feedback and corrections
- New vocabulary introduced
- Grammar points explained or corrected
- Homework review and assignments

Structure the summary to help the student review and learn from the lesson."""

    def get_user_prompt_template(self) -> str:
        """Returns the user prompt template for English lesson mode."""
        return """Lesson Date/Time: {date_str}

Transcript:
{transcript}

Please provide a structured summary in Markdown format with the following sections:

## Дата и время урока
{date_str}

## Разбор домашнего задания (Homework Review)
- (What homework was reviewed and teacher's feedback)

## Новая лексика (New Vocabulary)
- (New words/phrases introduced with context)

## Грамматические исправления (Grammar Corrections)
- (Grammar mistakes corrected and explanations provided)

## Домашнее задание (Homework Assignment)
- (New homework assigned, if any)

If any section is not applicable, state "Не указано" or "Нет".
Focus on capturing the teacher's feedback and corrections from Channels 1-2."""
