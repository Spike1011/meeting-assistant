import os
import threading
import time
from typing import List, Optional, Dict, Any
from core.recorders.base_recorder import BaseRecorder
from core.utils.audio_utils import merge_audio_files

class MultiRecorder(BaseRecorder):
    """
    Orchestrates multiple recorders running in parallel.
    Useful for capturing system audio and microphone simultaneously.
    """
    
    def __init__(self, recorders: List[BaseRecorder]):
        self.recorders = recorders
        self._is_recording = False
        self.output_paths = []
        self.output_dir = "output"
        self.final_filename = "recording.wav"
        self.threads = []
        
    def record(self, output_dir: str = "output", filename: Optional[str] = None) -> str:
        """
        Record from all streams in parallel.
        This method will block until stop() is called.
        """
        if not self.recorders:
            raise ValueError("MultiRecorder initialized with no sub-recorders")
            
        self._is_recording = True
        self.output_paths = []
        self.output_dir = output_dir
        self.final_filename = filename if filename else "recording.wav"
        self.threads = []
        
        # Base filename without extension
        base_name = self.final_filename.rsplit('.', 1)[0]
        
        def record_stream(recorder, idx):
            stream_filename = f"{base_name}_part_{idx}.wav"
            # This call blocks for each recorder until stop() is called
            path = recorder.record(output_dir=output_dir, filename=stream_filename)
            self.output_paths.append(path)

        # Start all recorders in separate threads
        for i, recorder in enumerate(self.recorders):
            t = threading.Thread(target=record_stream, args=(recorder, i), daemon=True)
            self.threads.append(t)
            t.start()
            
        print(f"[>] Concurrent recording started ({len(self.recorders)} streams)")
        
        # Wait until stop() is called. individual recorders will finish their own blocking record() calls.
        while self._is_recording:
            time.sleep(0.1)
            
        # Wait for all recorder threads to finish writing their files
        for t in self.threads:
            t.join(timeout=10)
            
        # Merge files
        merged_path = os.path.join(output_dir, self.final_filename)
        print(f"\n[*] Merging {len(self.output_paths)} streams into {merged_path}...")
        
        try:
            # Filtering out non-existent or 0-byte files
            valid_paths = [p for p in self.output_paths if os.path.exists(p) and os.path.getsize(p) > 44]
            if not valid_paths:
                print("[!] No valid audio data captured in any stream.")
                return ""

            final_path = merge_audio_files(valid_paths, merged_path)
            
            # Clean up temporary part files
            for p in self.output_paths:
                if p != final_path and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception as e:
                        print(f"[!] Could not remove temp file {p}: {e}")
                        
            return final_path
        except Exception as e:
            print(f"[-] Error merging audio files: {e}")
            return self.output_paths[0] if self.output_paths else ""

    def stop(self) -> None:
        """Stop all recorders and signal record() to finish."""
        if not self._is_recording:
            return

        print("\n[*] Stopping all recording streams...")
        
        # 1. Stop each individual recorder
        for recorder in self.recorders:
            try:
                recorder.stop()
            except Exception as e:
                print(f"[!] Error stopping recorder: {e}")
        
        # 2. Set our own internal flag to False so record() continues to merge
        self._is_recording = False

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self._is_recording

    def get_info(self) -> Dict[str, Any]:
        """Get info about all recorders."""
        return {
            "type": "multi",
            "count": len(self.recorders),
            "sub_recorders": [r.get_info() for r in self.recorders]
        }
