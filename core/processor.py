import os
import json
import time
from deepgram import DeepgramClient

class DeepgramProcessor:
    """Sends audio to Deepgram with retry logic and parses speaker roles."""
    
    def __init__(self, api_key: str, timeout: int = 600, max_retries: int = 3):
        if not api_key:
            raise ValueError("Deepgram API Key is missing.")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Fix GRPC DNS resolution issues on macOS
        os.environ['GRPC_DNS_RESOLVER'] = 'native'
        
        # Use keyword argument to avoid BaseClient initialization errors
        self.client = DeepgramClient(api_key=api_key, timeout=timeout)

    def process_audio(self, audio_path: str, model: str = "nova-2", language: str = "ru") -> str:
        """
        Transcribes audio file and returns formatted transcript with speaker diarization.
        Implements retry logic with exponential backoff.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        print(f"Sending {audio_path} to Deepgram...")
        
        # Retry with exponential backoff
        for attempt in range(self.max_retries):
            try:
                with open(audio_path, "rb") as file:
                    buffer_data = file.read()

                # Correct call for deepgram-sdk v5+
                response = self.client.listen.v1.media.transcribe_file(
                    request=buffer_data,
                    model=model,
                    diarize=True,
                    smart_format=True,
                    language=language,
                )
                
                # Parse response
                return self._parse_transcript(response)

            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a retryable error
                is_retryable = any(keyword in error_msg.lower() for keyword in [
                    'connection', 'timeout', 'network', 'dns', 'temporary'
                ])
                
                if attempt < self.max_retries - 1 and is_retryable:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"[!] Attempt {attempt + 1} failed: {error_msg}")
                    print(f"    Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    print(f"[-] Deepgram API Error after {attempt + 1} attempts: {e}")
                    if 'dns' in error_msg.lower() or 'grpc' in error_msg.lower():
                        print("\n[i] Troubleshooting tip: GRPC DNS resolution issue detected.")
                        print("    GRPC_DNS_RESOLVER=native has been set, but the error persists.")
                        print("    Try restarting your terminal or checking your network connection.")
                    raise

    def _parse_transcript(self, response) -> str:
        """Parses Deepgram JSON response into a readable transcript with [MM:SS] Speaker N: format."""
        transcript_lines = []
        
        try:
            # Navigate through the response object
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

