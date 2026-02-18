import time
from datetime import datetime
from openai import OpenAI
from .base import LLMProvider
from core.utils.prompt_manager import PromptManager

class ChatGPTProvider(LLMProvider):
    """Generates meeting summaries via OpenAI ChatGPT."""

    def __init__(self, api_key: str, model_name: str = "gpt-4o", max_retries: int = 3):
        super().__init__(api_key, model_name)
        self.max_retries = max_retries
        
        if not api_key:
            raise ValueError("OpenAI API Key is missing.")

        self.client = OpenAI(api_key=api_key)

    def summarize(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """
        Generates a summary from the transcript using ChatGPT.
        
        Args:
            transcript: The meeting transcript text.
            meeting_datetime: Optional datetime of when the meeting occurred.
            mode: Summarization mode ("meeting", "english", "interview"). Defaults to "meeting".
        """
        print(f"Generating summary with ChatGPT ({self.model_name}) in {mode} mode...")
        
        # Get mode-specific prompt
        prompt_instance = PromptManager.get_prompt(mode)
        system_prompt = prompt_instance.get_system_prompt()
        user_prompt = prompt_instance.format_user_prompt(transcript, meeting_datetime)
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    stream=False
                )
                return response.choices[0].message.content
                
            except Exception as e:
                error_msg = str(e)
                
                # Check for 402 Insufficient Balance / Quota
                if "insufficient_quota" in error_msg or "429" in error_msg: 
                    print(f"\n[!] OPENAI ERROR: Insufficient Quota or Balance (429/402).")
                    print("    Please check your OpenAI billing at https://platform.openai.com/usage")
                    print("    Or switch to Gemini by running: python main.py --setup\n")
                    raise e

                print(f"[-] ChatGPT Error: {error_msg}")
                
                # Check if it's a retryable error
                is_retryable = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'temporary', '429', 'rate limit'
                ])
                
                if attempt < self.max_retries - 1 and is_retryable:
                    wait_time = 30 if "429" in error_msg or "rate limit" in error_msg.lower() else (2 ** attempt)
                    print(f"[!] Attempt {attempt + 1} failed. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
