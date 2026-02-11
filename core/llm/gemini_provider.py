import time
from datetime import datetime
from .base import LLMProvider

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

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash", max_retries: int = 3):
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

    def summarize(self, transcript: str, meeting_datetime: datetime = None) -> str:
        """
        Generates a summary from the transcript using Gemini with retry logic.
        """
        print(f"Generating summary with Gemini ({self.model_name})...")
        
        # Format meeting date/time
        if meeting_datetime:
            date_str = meeting_datetime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = f"""
        You are an expert meeting assistant. Analyze the following meeting transcript. Result must be in Russian.
        
        Meeting Date/Time: {date_str}
        
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
        Try to assign tasks to specific speakers based on the conversation context.
        """
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                if USE_NEW_API:
                    # New API
                    try:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt
                        )
                        return response.text
                    except Exception as e:
                        error_str = str(e)
                        # 404 or 429 Handle - specific fallback logic for Gemini 2.0 Flash
                        if (("404" in error_str) or ("429" in error_str)) and self.model_name == 'gemini-2.0-flash':
                            print(f"[!] Gemini 2.0 Flash issue, falling back to gemini-flash-latest")
                            # Create a temporary fallback instance or just change model name
                            # Changing model name locally for retry
                            self.model_name = 'gemini-flash-latest'
                            return self.summarize(transcript, meeting_datetime)
                        
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
                        response = self.model.generate_content(prompt)
                        return response.text
                    except Exception as e:
                         # Fallback for legacy if 2.0 fails
                        if "404" in str(e) and self.model_name == 'gemini-2.0-flash':
                             print(f"[!] Gemini 2.0 Flash stable not available, trying 1.5 flash")
                             self.model_name = 'gemini-1.5-flash'
                             self.model = genai.GenerativeModel(self.model_name)
                             # Retry immediately
                             continue
                        raise e

            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a retryable error
                is_retryable = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'temporary', '429', 'quota'
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
