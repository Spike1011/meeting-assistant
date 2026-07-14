"""Prompt manager factory for retrieving mode-specific prompts."""
from core.llm.prompts.base_prompt import BasePrompt
from core.llm.prompts.meeting_prompt import MeetingPrompt
from core.llm.prompts.english_prompt import EnglishPrompt
from core.llm.prompts.interview_prompt import InterviewPrompt


class PromptManager:
    """Factory class for retrieving mode-specific prompt instances."""

    # Valid mode strings
    VALID_MODES = {
        "meeting": MeetingPrompt,
        "english": EnglishPrompt,
        "interview": InterviewPrompt,
    }

    @classmethod
    def get_prompt(cls, mode: str = "meeting") -> BasePrompt:
        """
        Get the appropriate prompt instance based on mode.
        
        Args:
            mode: Mode string ("meeting", "english", "interview")
            
        Returns:
            Instance of the appropriate BasePrompt subclass
            
        Raises:
            ValueError: If mode is not recognized
        """
        mode_lower = mode.lower().strip()
        
        if mode_lower not in cls.VALID_MODES:
            valid_modes = ", ".join(cls.VALID_MODES.keys())
            raise ValueError(
                f"Invalid mode '{mode}'. Valid modes are: {valid_modes}"
            )
        
        prompt_class = cls.VALID_MODES[mode_lower]
        return prompt_class()

    @classmethod
    def get_valid_modes(cls) -> list:
        """Returns a list of valid mode strings."""
        return list(cls.VALID_MODES.keys())
