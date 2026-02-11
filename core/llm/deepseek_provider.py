import time
from datetime import datetime
from openai import OpenAI
from .base import LLMProvider

class DeepSeekProvider(LLMProvider):
    """Generates meeting summaries via DeepSeek API (OpenAI-compatible)."""

    def __init__(self, api_key: str, model_name: str = "deepseek-chat", max_retries: int = 3):
        super().__init__(api_key, model_name)
        self.max_retries = max_retries
        
        if not api_key:
            raise ValueError("DeepSeek API Key is missing.")

        # DeepSeek uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )

    def summarize(self, transcript: str, meeting_datetime: datetime = None) -> str:
        """
        Generates a summary from the transcript using DeepSeek.
        """
        print(f"Generating summary with DeepSeek ({self.model_name})...")
        
        # Format meeting date/time
        if meeting_datetime:
            date_str = meeting_datetime.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        system_prompt = "You are an expert meeting assistant. Analyze the meeting transcript and provide a summary in Russian."
        
        user_prompt = f"""
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
                
                # Check for 402 Insufficient Balance
                if "402" in error_msg or "Insufficient Balance" in error_msg:
                    print(f"\n[!] DEEPSEEK ERROR: Insufficient Balance (402).")
                    print("    Please top up your DeepSeek API account at https://platform.deepseek.com/")
                    print("    Or switch to Gemini by running: python main.py --setup\n")
                    raise e
                    
                print(f"[-] DeepSeek Error: {error_msg}")
                
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
