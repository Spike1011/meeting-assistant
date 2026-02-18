"""Abstract base class for prompt templates."""
from abc import ABC, abstractmethod
from datetime import datetime


class BasePrompt(ABC):
    """Abstract base class defining the interface for all prompt templates."""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Returns the system instruction string for the LLM.
        
        Returns:
            System prompt string that defines the assistant's role and behavior.
        """
        pass

    @abstractmethod
    def get_user_prompt_template(self) -> str:
        """
        Returns the user prompt template string.
        
        This template should include placeholders for:
        - {date_str}: Meeting date/time string
        - {transcript}: The transcript content
        
        Returns:
            User prompt template string with placeholders.
        """
        pass

    def format_user_prompt(self, transcript: str, meeting_datetime: datetime = None) -> str:
        """
        Formats the user prompt with transcript and datetime.
        
        Args:
            transcript: The meeting transcript text.
            meeting_datetime: Optional datetime of when the meeting occurred.
            
        Returns:
            Formatted user prompt string.
        """
        if meeting_datetime:
            date_str = meeting_datetime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return self.get_user_prompt_template().format(
            date_str=date_str,
            transcript=transcript
        )
