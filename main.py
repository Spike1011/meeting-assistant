import os
import sys
import signal
import argparse
import asyncio
from datetime import datetime
from core.config_manager import ConfigManager
from recorder_factory import RecorderFactory
from core.processor import DeepgramProcessor
from core.summarizer import LLMSummarizer
from core.utils.setup_utils import interactive_setup, check_first_run

# Global recorder instance for signal handling
recorder_instance = None
start_datetime = None

def signal_handler(sig, frame):
    """Handle graceful shutdown on SIGINT (Ctrl+C)."""
    if recorder_instance and recorder_instance.is_recording:
        print("\n\n[!] Interrupt received. Stopping recording gracefully...")
        recorder_instance.stop()
    else:
        print("\n\n[!] Interrupt received. Exiting...")
        sys.exit(0)

async def main(existing_audio_path: str = None, force_setup: bool = False):
    global recorder_instance, start_datetime
    
    # 1. Load configuration
    try:
        config = ConfigManager()
    except Exception as e:
        print(f"[-] Configuration Error: {e}")
        return

    # 2. Check for first run or forced setup
    if force_setup or (not existing_audio_path and check_first_run(config)):
        if not interactive_setup(config):
            print("[-] Setup failed. Exiting.")
            return

    print("[*] Meeting Assistant initialized.")
    print("-" * 60)
    
    # Set GRPC DNS resolver to prevent gRPC issues on macOS
    os.environ['GRPC_DNS_RESOLVER'] = 'native'
    
    # Show recording method
    print(f"[+] Configuration loaded")
    print(f"    Recording method: {config.get_recording_method()}")
    
    # 2. Get API keys
    deepgram_key = config.get_deepgram_api_key()
    gemini_key = config.get_gemini_api_key()
    
    if not deepgram_key:
        print("[-] Error: DEEPGRAM_API_KEY is missing in .env or config.json")
        return
    if not gemini_key:
        print("[-] Error: GEMINI_API_KEY is missing in .env or config.json")
        return
    
    print("[+] API keys validated")
    
    # 3. Check existing file
    if existing_audio_path:
        if not os.path.exists(existing_audio_path):
            print(f"[-] Error: File not found at {existing_audio_path}")
            return
        print(f"[+] Processing existing file: {existing_audio_path}")
    
    # 4. Initialize components
    try:
        # Only init recorder if we need to record
        if not existing_audio_path:
            recorder_instance = RecorderFactory.create_recorder(config)
            print(f"[+] Recorder initialized: {recorder_instance.get_info()['type']}")
        else:
            recorder_instance = None
        
        trans_settings = config.get_transcription_settings()
        processor = DeepgramProcessor(
            api_key=deepgram_key,
            timeout=trans_settings.get('timeout', 600),
            max_retries=3
        )
        print("[+] Transcription processor initialized")
        
        summarizer = LLMSummarizer(api_key=gemini_key, max_retries=3)
        print("[+] Summarizer initialized")
        
    except Exception as e:
        print(f"[-] Initialization Error: {e}")
        return
    
    # 5. Prepare Session Folder
    start_datetime = datetime.now()
    
    if existing_audio_path:
        session_dir = os.path.dirname(os.path.abspath(existing_audio_path))
    else:
        folder_name = start_datetime.strftime("%Y_%m_%d %H:%M")
        session_dir = os.path.join("output", folder_name)
        os.makedirs(session_dir, exist_ok=True)
    
    print(f"[*] Session directory: {session_dir}")
    print("-" * 60)
    
    # 6. Record or Use Existing Audio
    audio_path = None
    
    if existing_audio_path:
        audio_path = existing_audio_path
    else:
        try:
            # Register signal handler for graceful shutdown
            signal.signal(signal.SIGINT, signal_handler)
            
            # Use simple fixed filename since the folder timestamp is unique
            audio_filename = "recording.wav"
            audio_path = recorder_instance.record(output_dir=session_dir, filename=audio_filename)
        except Exception as e:
            print(f"[-] Recording failed: {e}")
            return
    
    if not audio_path or not os.path.exists(audio_path) or os.path.getsize(audio_path) <= 44:
        print("\n[-] Error: Audio file is empty or was not created correctly.")
        print("    Check if your microphone is working and permissions are granted.")
        return
    
    print(f"[+] Audio file ready: {audio_path} ({os.path.getsize(audio_path)} bytes)")
    
    # 7. Transcribe
    print("\n" + "-" * 60)
    print("[*] Starting Transcription")
    print("-" * 60)
    
    try:
        trans_settings = config.get_transcription_settings()
        transcript = processor.process_audio(
            audio_path,
            model=trans_settings.get('model', 'nova-2'),
            language=trans_settings.get('language', 'ru')
        )
        
        # Save transcript with timestamp
        timestamp_str = start_datetime.strftime("%Y%m%d_%H%M%S")
        transcript_filename = f"transcript_{timestamp_str}.md"
        transcript_path = os.path.join(session_dir, transcript_filename)
        
        with open(transcript_path, "w") as f:
            f.write(f"# Meeting Transcript\n\n")
            f.write(f"**Date/Time:** {start_datetime.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"---\n\n")
            f.write(transcript)
        
        print(f"[+] Transcript saved to: {transcript_path}")
        
    except Exception as e:
        print(f"[-] Transcription failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 8. Summarize
    print("\n" + "-" * 60)
    print("[*] Starting Summarization")
    print("-" * 60)
    
    try:
        summary = summarizer.summarize(transcript, meeting_datetime=start_datetime)
        
        # Save summary with timestamp
        summary_filename = f"summary_{timestamp_str}.md"
        summary_path = os.path.join(session_dir, summary_filename)
        
        with open(summary_path, "w") as f:
            f.write(f"# Meeting Summary\n\n")
            f.write(summary)
        
        print(f"[+] Summary saved to: {summary_path}")
        
    except Exception as e:
        print(f"[-] Summarization failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "-" * 60)
    print(f"[+] Done! All files generated in: {session_dir}")
    print("-" * 60)

if __name__ == "__main__":
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Meeting Assistant - Record, transcribe, and summarize meetings"
    )
    parser.add_argument(
        "-f", "--file",
        type=str,
        help="Path to an existing audio file to transcribe and summarize"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup to choose audio devices"
    )
    args = parser.parse_args()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main(existing_audio_path=args.file, force_setup=args.setup))
    except KeyboardInterrupt:
        print("\n\n[!] Program stopped by user.")
        sys.exit(0)

