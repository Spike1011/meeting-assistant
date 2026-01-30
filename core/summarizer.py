import os
import google.generativeai as genai

class LLMSummarizer:
    """Генерация саммари через LLM (Google Gemini)"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("LLM API Key is missing.")
        
        genai.configure(api_key=api_key)
        # using 'gemini-flash-latest' as 'gemini-1.5-flash' alias was not found
        self.model = genai.GenerativeModel('gemini-flash-latest')

    def summarize(self, transcript: str) -> str:
        """Generates a summary from the transcript using Gemini."""
        print("Generating summary with Gemini...")
        
        prompt = f"""
        You are an expert meeting assistant. Analyze the following meeting transcript. Result must be in Russian.
        
        Transcript:
        {transcript}
        
        Please provide a concise summary in Markdown format with the following sections:
        
        ## Ключевые темы
        - (List of main topics discussed)
        
        ## Решения
        - (List of agreed decisions)
        
        ## Задачи
        - [ ] (List of tasks assigned to specific people)
        
        If any section is not applicable, state "None".
        """

        # No try/except here - let the main loop handle errors
        response = self.model.generate_content(prompt)
        return response.text
