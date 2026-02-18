"""Interview mode prompt template."""
from .base_prompt import BasePrompt


class InterviewPrompt(BasePrompt):
    """Prompt template for interview summarization."""

    def get_system_prompt(self) -> str:
        """Returns the system prompt for interview mode."""
        return """You are an expert interview analysis assistant. Analyze the interview transcript and provide a detailed assessment in Russian.

IMPORTANT AUDIO CHANNEL MAPPING:
- Channels 1-2: Interviewer and Candidate audio (questions and answers)
- Channel 3: Your audio (your notes or observations)

Focus on:
- Candidate's skills and qualifications mentioned
- Detailed question-answer pairs
- Behavioral patterns and responses
- Overall hiring recommendation

Provide a comprehensive analysis that helps evaluate the candidate's fit for the position."""

    def get_user_prompt_template(self) -> str:
        """Returns the user prompt template for interview mode."""
        return """Interview Date/Time: {date_str}

Transcript:
{transcript}

Please provide a detailed interview analysis in Markdown format with the following sections:

## Дата и время интервью
{date_str}

## Навыки кандидата (Candidate Skills)
- (Technical skills, soft skills, and qualifications mentioned)

## Вопрос-Ответ (Question-Answer Log)
For each significant question:
- **Вопрос:** (Question asked)
- **Ответ:** (Candidate's response)
- **Оценка:** (Brief assessment of the answer)

## Поведенческие паттерны (Behavioral Patterns)
- (Observations about candidate's communication style, confidence, etc.)

## Вердикт по найму (Hiring Verdict)
- (Overall assessment and recommendation)

If any section is not applicable, state "Не указано" or "Нет".
Focus on capturing detailed information from Channels 1-2 (interviewer and candidate)."""
