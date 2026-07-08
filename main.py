import os
import sys
import signal
import argparse
import asyncio
import re
from datetime import datetime
from core.config_manager import ConfigManager
from recorder_factory import RecorderFactory
from core.processor import DeepgramProcessor
from core.llm import create_llm_provider
from core.llm.base import normalize_meeting_title
from core.utils.setup_utils import interactive_setup, check_first_run
from core.utils.prompt_manager import PromptManager

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

def select_mode_interactive() -> str:
    """
    Interactive mode selection menu.
    
    Returns:
        Selected mode string ("meeting", "english", or "interview")
    """
    print("\n" + "-" * 60)
    print("[*] Select Summarization Mode")
    print("-" * 60)
    print("    1. Meeting (Standard)")
    print("    2. English Lesson")
    print("    3. Interview")
    print("-" * 60)
    
    valid_modes = PromptManager.get_valid_modes()
    mode_map = {
        "1": "meeting",
        "2": "english",
        "3": "interview"
    }
    
    while True:
        try:
            choice = input(f"\nSelect mode (1-3) [default: 1]: ").strip()
            if not choice:
                choice = "1"
            
            if choice in mode_map:
                selected_mode = mode_map[choice]
                mode_names = {
                    "meeting": "Meeting (Standard)",
                    "english": "English Lesson",
                    "interview": "Interview"
                }
                print(f"[+] Selected: {mode_names[selected_mode]}")
                return selected_mode
            else:
                print("[!] Please enter a number between 1 and 3")
        except (ValueError, KeyboardInterrupt):
            print("[!] Invalid input. Please enter a number.")
            raise

def _unique_directory_path(parent_dir: str, directory_name: str) -> str:
    """Return a non-existing directory path by appending a numeric suffix if needed."""
    candidate = os.path.join(parent_dir, directory_name)
    if not os.path.exists(candidate):
        return candidate

    suffix = 2
    while True:
        candidate = os.path.join(parent_dir, f"{directory_name} {suffix}")
        if not os.path.exists(candidate):
            return candidate
        suffix += 1

def rename_session_dir_with_title(session_dir: str, title: str) -> str:
    """Append a generated title to the timestamp-based session directory."""
    safe_title = normalize_meeting_title(title)
    parent_dir = os.path.dirname(session_dir)
    time_prefix = os.path.basename(session_dir)
    titled_name = f"{time_prefix} {safe_title}"
    new_session_dir = _unique_directory_path(parent_dir, titled_name)

    if os.path.abspath(new_session_dir) == os.path.abspath(session_dir):
        return session_dir

    os.rename(session_dir, new_session_dir)
    return new_session_dir

def derive_local_meeting_title(content: str, mode: str = "meeting") -> str:
    """Build a best-effort title without an extra LLM call."""
    text = content.lower()

    if mode == "english" or "дата и время урока" in text or "new vocabulary" in text or "новая лексика" in text:
        if "граммат" in text and "лексик" in text:
            return "Урок английского лексика и грамматика"
        return "Урок английского"

    if "1-1" in text or "one-on-one" in text or "один на один" in text:
        name_match = re.search(r"(?:1-1|one-on-one|один на один)\s+(?:с|with)\s+([А-ЯA-Z][а-яa-zё-]+)", content)
        if name_match:
            return f"1-1 с {name_match.group(1)}"
        return "1-1 встреча"

    scope = ""
    if "flowwow" in text and "yudora" in text:
        scope = " Flowwow и Yudora"
    elif "flowwow" in text:
        scope = " Flowwow"
    elif "yudora" in text:
        scope = " Yudora"

    if ("командные метрики" in text or "jira" in text) and ("ии" in text or "кодекс" in text or "ai" in text):
        return "Метрики Jira и AI"

    if "грейдирован" in text and ("реорганизац" in text or "реструктуризац" in text):
        return "Реорганизация и грейдирование"

    if "реструктуризация и передача команд" in text or ("передача команд" in text and "интеграц" in text):
        return "Передача команд и интеграций"

    if "планирование следующего спринта" in text and ("чат" in text or "бот" in text):
        return "Планирование чатов"

    if "дейлик" in text or "daily" in text or "стендап" in text or "standup" in text:
        return normalize_meeting_title(f"Дейлик{scope or ' команды'}")

    planning_markers = ["план", "цели", "roadmap", "роадмап", "q2", "q3", "реорганизац", "реструктуризац"]
    if any(marker in text for marker in planning_markers):
        return normalize_meeting_title(f"Планы команд{scope}")

    reporting_markers = ["отчет", "статус", "ключевые темы", "решения", "задачи"]
    if any(marker in text for marker in reporting_markers) or text.count("команда") >= 3:
        return normalize_meeting_title(f"Отчет команд{scope}")

    topic_match = re.search(r"\*\*([^:*\\n]{4,50})", content)
    if topic_match:
        return normalize_meeting_title(topic_match.group(1))

    return "Встреча"

async def main(existing_audio_path: str = None, force_setup: bool = False, mode: str = None):
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

    # 2.5. Mode selection
    if mode is None:
        try:
            mode = select_mode_interactive()
        except KeyboardInterrupt:
            print("\n\n[!] Mode selection cancelled. Exiting.")
            return
    else:
        # Validate provided mode
        try:
            PromptManager.get_prompt(mode)  # This will raise ValueError if invalid
            mode_names = {
                "meeting": "Meeting (Standard)",
                "english": "English Lesson",
                "interview": "Interview"
            }
            print(f"[+] Mode: {mode_names.get(mode, mode)}")
        except ValueError as e:
            print(f"[-] Invalid mode: {e}")
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
    llm_key = config.get_llm_api_key()
    
    if not deepgram_key:
        print("[-] Error: DEEPGRAM_API_KEY is missing in .env or config.json")
        return
    if not llm_key:
        print(f"[-] Error: API Key for {config.get_llm_provider_type()} is missing. Check .env or config.json")
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
        
        print("[+] Transcription processor initialized")
        
        summarizer = create_llm_provider(config)
        print(f"[+] Summarizer initialized ({config.get_llm_model_name()})")
        
    except Exception as e:
        print(f"[-] Initialization Error: {e}")
        return
    
    # 5. Prepare Session Folder
    start_datetime = datetime.now()
    
    if existing_audio_path:
        session_dir = os.path.dirname(os.path.abspath(existing_audio_path))
        should_rename_session_dir = False
    else:
        # Include seconds to avoid collisions if restarted quickly
        session_name = start_datetime.strftime("%Y_%m_%d %H:%M:%S")
        session_dir = os.path.join("output", session_name)
        os.makedirs(session_dir, exist_ok=True)
        should_rename_session_dir = True
    
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
    
    summary = None
    try:
        summary = summarizer.summarize(transcript, meeting_datetime=start_datetime, mode=mode)
        
        # Save summary with timestamp
        summary_filename = f"summary_{timestamp_str}.md"
        summary_path = os.path.join(session_dir, summary_filename)
        
        with open(summary_path, "w") as f:
            f.write(f"# Meeting Summary\n\n")
            f.write(summary)
        
        print(f"[+] Summary saved to: {summary_path}")
        
    except Exception as e:
        error_str = str(e)
        # Suppress traceback for known credit/quota errors
        is_known_error = any(msg in error_str for msg in ["402", "Insufficient Balance", "insufficient_quota", "429"])
        
        if is_known_error:
             print(f"[-] Summarization failed: LLM Quota or Balance issue.")
        else:
            print(f"[-] Summarization failed: {e}")
            import traceback
            traceback.print_exc()

    if should_rename_session_dir:
        try:
            title_content = summary or transcript
            meeting_title = derive_local_meeting_title(title_content, mode=mode)
            title_source = "summary" if summary else "transcript"

            renamed_session_dir = rename_session_dir_with_title(session_dir, meeting_title)
            if renamed_session_dir != session_dir:
                session_dir = renamed_session_dir
                audio_path = os.path.join(session_dir, os.path.basename(audio_path))
                print(f"[+] Session renamed to: {session_dir} ({title_source})")
            else:
                print(f"[+] Session title: {meeting_title} ({title_source})")
        except Exception as e:
            print(f"[!] Could not rename session folder: {e}")
    
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
    parser.add_argument(
        "--mode",
        type=str,
        choices=["meeting", "english", "interview"],
        help="Summarization mode: 'meeting' (standard), 'english' (lesson), or 'interview'"
    )
    args = parser.parse_args()
    
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main(existing_audio_path=args.file, force_setup=args.setup, mode=args.mode))
    except KeyboardInterrupt:
        print("\n\n[!] Program stopped by user.")
        sys.exit(0)
