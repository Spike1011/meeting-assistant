import os
import json
from deepgram import DeepgramClient

class DeepgramProcessor:
    """Отправка в Deepgram и парсинг ролей"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Deepgram API Key is missing.")
        self.api_key = api_key
        # Use keyword argument to avoid BaseClient initialization errors
        self.client = DeepgramClient(api_key=api_key)

    def process_audio(self, audio_path: str):
        """Transcribes audio file and returns formatted transcript with speaker diarization."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"Sending {audio_path} to Deepgram...")

        try:
            with open(audio_path, "rb") as file:
                buffer_data = file.read()

            # Correct call for deepgram-sdk v5+
            response = self.client.listen.v1.media.transcribe_file(
                request=buffer_data,
                model="nova-2",
                diarize=True,
                smart_format=True,
                language="ru",
            )
            
            # Parse response
            return self._parse_transcript(response)

        except Exception as e:
            print(f"Deepgram API Error: {e}")
            raise

    def _parse_transcript(self, response) -> str:
        """Parses Deepgram JSON response into a readable transcript."""
        transcript_lines = []
        
        # Deepgram SDK v3 returns an object, access attributes directly
        # The structure is typically results.channels[0].alternatives[0].paragraphs.paragraphs
        # Or words if paragraphs are not available.
        
        try:
            # Navigate safety through the response object/dictionary
            # Note: SDK v3 returns typed objects usually, but sometimes dicts depending on method.
            # Assuming typed object access:
            if not response.results or not response.results.channels:
                 return "No transcript generated."

            channel = response.results.channels[0]
            alternative = channel.alternatives[0]
            
            if hasattr(alternative, 'paragraphs') and alternative.paragraphs:
                paragraphs = alternative.paragraphs.paragraphs
                for para in paragraphs:
                    speaker = para.speaker
                    start_time = para.start
                    # Format time as [MM:SS]
                    minutes = int(start_time // 60)
                    seconds = int(start_time % 60)
                    time_str = f"[{minutes:02}:{seconds:02}]"
                    
                    text = " ".join([s.text for s in para.sentences])
                    transcript_lines.append(f"{time_str} Speaker {speaker}: {text}")
            else:
                # Fallback to words if paragraphs are missing (shouldn't happen with smart_format)
                 transcript_lines.append(alternative.transcript)

            return "\n\n".join(transcript_lines)

        except Exception as e:
             print(f"Error parsing transcript: {e}")
             # Fallback: dump the raw text
             try:
                 return response.results.channels[0].alternatives[0].transcript
             except:
                 return "Error parsing transcript."
