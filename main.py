import os
import sys
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from core.recorder import AudioRecorder
from core.processor import DeepgramProcessor
from core.summarizer import LLMSummarizer

# Load environment variables
load_dotenv()

async def main():
    print("Meeting Assistant initialized.")
    
    # 1. Setup keys
    deepgram_key = os.getenv("DEEPGRAM_API_KEY")
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY")
    
    if not deepgram_key:
        print("Error: DEEPGRAM_API_KEY is missing in .env")
        return
    if not llm_key:
        print("Error: LLM_API_KEY (or GEMINI_API_KEY) is missing in .env")
        return

    # 2. Initialize components
    try:
        recorder = AudioRecorder(device_name="Unit")
        processor = DeepgramProcessor(api_key=deepgram_key)
        summarizer = LLMSummarizer(api_key=llm_key)
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    # 3. Prepare Session Folder
    start_time = datetime.now()
    folder_name = start_time.strftime("%Y_%m_%d %H:%M")
    session_dir = os.path.join("output", folder_name)
    os.makedirs(session_dir, exist_ok=True)
    
    print(f"\nSession directory created: {session_dir}")

    # 4. Record Audio
    try:
        # Use simple fixed filename since the folder timestamp is unique
        audio_filename = "recording.wav"
        audio_path = recorder.record(output_dir=session_dir, filename=audio_filename)
    except Exception as e:
        print(f"Recording failed: {e}")
        return

    if not audio_path:
        print("No audio recorded.")
        return

    # 5. Transcribe
    print("\n--- Starting Transcription ---")
    try:
        transcript = processor.process_audio(audio_path)
        
        # Save transcript
        transcript_path = os.path.join(session_dir, "transcript.md")
        
        with open(transcript_path, "w") as f:
            f.write(transcript)
        print(f"Transcript saved to: {transcript_path}")
        
    except Exception as e:
        print(f"Transcription failed: {e}")
        return

    # 6. Summarize
    print("\n--- Starting Summarization ---")
    try:
        summary = summarizer.summarize(transcript)
        
        # Save summary
        summary_path = os.path.join(session_dir, "summary.md")
        
        with open(summary_path, "w") as f:
            f.write(summary)
        print(f"Summary saved to: {summary_path}")
        
    except Exception as e:
        print(f"Summarization failed: {e}")

    print(f"\nDone! All files generated in: {session_dir}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
        sys.exit(0)
