from abc import ABC, abstractmethod
from datetime import datetime

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name

    @abstractmethod
    def summarize(self, transcript: str, meeting_datetime: datetime = None) -> str:
        """
        Generates a summary from the transcript.

        Args:
            transcript: The meeting transcript text.
            meeting_datetime: Optional datetime of when the meeting occurred.

        Returns:
            Formatted Markdown summary.
        """
        pass
