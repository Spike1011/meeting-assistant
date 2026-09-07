import time
from datetime import datetime
from .base import LLMProvider, TITLE_SYSTEM_PROMPT, build_title_user_prompt, normalize_meeting_title
from core.utils.prompt_manager import PromptManager

try:
    # Try new google.genai first
    from google import genai
    from google.genai import types
    USE_NEW_API = True
except ImportError:
    # Fallback to legacy google.generativeai
    import google.generativeai as genai
    USE_NEW_API = False

class GeminiProvider(LLMProvider):
    """Generates meeting summaries via Google Gemini."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", max_retries: int = 3):
        super().__init__(api_key, model_name)
        self.max_retries = max_retries
        
        if not api_key:
            raise ValueError("Gemini API Key is missing.")

        if USE_NEW_API:
            # New google.genai API
            self.client = genai.Client(api_key=api_key)
        else:
            # Legacy google.generativeai API
            genai.configure(api_key=api_key)
            try:
                self.model = genai.GenerativeModel(self.model_name)
            except Exception:
                # Fallback handled in summarize if model is invalid/unavailable
                pass

    def summarize(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """
        Generates a summary from the transcript using Gemini with retry logic.
        
        Args:
            transcript: The meeting transcript text.
            meeting_datetime: Optional datetime of when the meeting occurred.
            mode: Summarization mode ("meeting", "english", "interview"). Defaults to "meeting".
        """
        print(f"Generating summary with Gemini ({self.model_name}) in {mode} mode...")
        
        # Get mode-specific prompt
        prompt_instance = PromptManager.get_prompt(mode)
        system_prompt = prompt_instance.get_system_prompt()
        user_prompt = prompt_instance.format_user_prompt(transcript, meeting_datetime)
        
        # Combine system and user prompts for Gemini
        # For Gemini, we can include system instruction in the prompt or use system_instruction parameter if available
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                if USE_NEW_API:
                    # New API
                    try:
                        # Try with system_instruction parameter if available
                        try:
                            response = self.client.models.generate_content(
                                model=self.model_name,
                                contents=user_prompt,
                                config=types.GenerateContentConfig(
                                    system_instruction=system_prompt
                                )
                            )
                            return response.text
                        except (TypeError, AttributeError):
                            # Fallback: include system prompt in contents if system_instruction not supported
                            response = self.client.models.generate_content(
                                model=self.model_name,
                                contents=full_prompt
                            )
                            return response.text
                    except Exception as e:
                        error_str = str(e)
                        # Use the current low-cost model if 2.5 Flash itself is unavailable.
                        if "404" in error_str and self.model_name == 'gemini-2.5-flash':
                            print(f"[!] Gemini 2.5 Flash is unavailable, falling back to gemini-2.5-flash-lite")
                            self.model_name = 'gemini-2.5-flash-lite'
                            return self.summarize(transcript, meeting_datetime, mode)
                        
                        # If even fallback is exhausted, we need to wait
                        if "429" in error_str:
                            print(f"[!] Quota exceeded for {self.model_name}. Waiting 30s...")
                            time.sleep(30)
                        raise
                else:
                    # Legacy API
                    # Ensure model is initialized with current model_name
                    if not hasattr(self, 'model') or self.model.model_name != f"models/{self.model_name}" and self.model.model_name != self.model_name:
                         self.model = genai.GenerativeModel(self.model_name)

                    try:
                        # Legacy API: include system prompt in the content
                        response = self.model.generate_content(full_prompt)
                        return response.text
                    except Exception as e:
                        # Fallback for legacy clients if 2.5 Flash is unavailable.
                        if "404" in str(e) and self.model_name == 'gemini-2.5-flash':
                             print(f"[!] Gemini 2.5 Flash is unavailable, trying 2.5 Flash-Lite")
                             self.model_name = 'gemini-2.5-flash-lite'
                             self.model = genai.GenerativeModel(self.model_name)
                             # Retry immediately
                             continue
                        raise e

            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a retryable error
                is_retryable = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'temporary', '429', 'quota',
                    '503', 'unavailable', 'resource_exhausted'
                ])
                
                if attempt < self.max_retries - 1 and is_retryable:
                    # Increase wait time for quota errors
                    wait_time = 30 if "429" in error_msg else (2 ** attempt)
                    print(f"[!] Attempt {attempt + 1} failed: {error_msg}")
                    print(f"    Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"[-] LLM Error after {attempt + 1} attempts: {e}")
                    raise

    def generate_title(self, transcript: str, meeting_datetime: datetime = None, mode: str = "meeting") -> str:
        """Generates a short folder title from the transcript using Gemini."""
        print(f"Generating meeting title with Gemini ({self.model_name})...")

        user_prompt = build_title_user_prompt(transcript, mode)
        full_prompt = f"{TITLE_SYSTEM_PROMPT}\n\n{user_prompt}"

        if USE_NEW_API:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=TITLE_SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
            except (TypeError, AttributeError):
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_prompt,
                )
            return normalize_meeting_title(response.text)

        if not hasattr(self, 'model') or self.model.model_name != f"models/{self.model_name}" and self.model.model_name != self.model_name:
            self.model = genai.GenerativeModel(self.model_name)

        response = self.model.generate_content(full_prompt)
        return normalize_meeting_title(response.text)
