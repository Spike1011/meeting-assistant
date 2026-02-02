import os
import sys
import argparse
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from core.recorder import AudioRecorder
from core.processor import DeepgramProcessor
from core.summarizer import LLMSummarizer

# Load environment variables
load_dotenv()

async def main(existing_audio_path: str = None):
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

    # 2. Check existing file
    if existing_audio_path:
        if not os.path.exists(existing_audio_path):
            print(f"Error: File not found at {existing_audio_path}")
            return
        print(f"Processing existing file: {existing_audio_path}")

    # 3. Initialize components
    try:
        # Only init recorder if we need to record
        if not existing_audio_path:
            recorder = AudioRecorder(device_name="Unit")
        else:
            recorder = None
            
        processor = DeepgramProcessor(api_key=deepgram_key)
        summarizer = LLMSummarizer(api_key=llm_key)
    except Exception as e:
        print(f"Initialization Error: {e}")
        return

    # 4. Prepare Session Folder
    if existing_audio_path:
        session_dir = os.path.dirname(os.path.abspath(existing_audio_path))
    else:
        start_time = datetime.now()
        folder_name = start_time.strftime("%Y_%m_%d %H:%M")
        session_dir = os.path.join("output", folder_name)
        os.makedirs(session_dir, exist_ok=True)
    
    print(f"\nSession directory: {session_dir}")

    # 5. Record or Use Existing Audio
    audio_path = None
    
    if existing_audio_path:
        audio_path = existing_audio_path
    else:
        try:
            # Use simple fixed filename since the folder timestamp is unique
            audio_filename = "recording.wav"
            audio_path = recorder.record(output_dir=session_dir, filename=audio_filename)
        except Exception as e:
            print(f"Recording failed: {e}")
            return

    if not audio_path:
        print("No audio recorded or provided.")
        return

    # 6. Transcribe
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

    # 7. Summarize
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
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Meeting Assistant CLI")
    parser.add_argument("-f", "--file", type=str, help="Path to an existing audio file to transcribe and summarize")
    args = parser.parse_args()

    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        asyncio.run(main(existing_audio_path=args.file))
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
        sys.exit(0)
