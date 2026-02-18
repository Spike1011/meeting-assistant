"""Prompt abstraction layer for multi-mode summarization."""

from .base_prompt import BasePrompt
from .meeting_prompt import MeetingPrompt
from .english_prompt import EnglishPrompt
from .interview_prompt import InterviewPrompt

__all__ = [
    "BasePrompt",
    "MeetingPrompt",
    "EnglishPrompt",
    "InterviewPrompt",
]
