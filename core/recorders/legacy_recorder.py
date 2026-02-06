import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import queue
import sys
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from .base_recorder import BaseRecorder

class LegacyRecorder(BaseRecorder):
    """Audio recorder using sounddevice (requires Aggregate Device like BlackHole + Mic)."""
    
    def __init__(self, device_name: str = "Unit", samplerate: int = 48000, channels: Optional[int] = None):
        self.device_name = device_name
        self.samplerate = samplerate
        self.device_index = self._find_device_index()
        
        # Get device info to check channels
        device_info = sd.query_devices(self.device_index)
        max_channels = device_info.get('max_input_channels', 0)
        
        if channels is None:
            self.channels = max_channels
        else:
            self.channels = channels
            if self.channels > max_channels:
                print(f"[!] Warning: Requested {channels} channels, but device only supports {max_channels}. Using {max_channels}.")
                self.channels = max_channels
        
        self._recording = False
        self._stop_event = threading.Event()
        
        print(f"[*] Initialized LegacyRecorder: Device='{self.device_name}' (index {self.device_index}), Samplerate={self.samplerate}, Channels={self.channels}")
    
    def _find_device_index(self) -> int:
        """Find audio device index by name."""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if self.device_name in device['name']:
                return i
        
        print(f"[!] Warning: Device '{self.device_name}' not found. Available devices:")
        print(sd.query_devices())
        raise ValueError(f"Device '{self.device_name}' not found.")
    
    def record(self, output_dir: str = "output", filename: Optional[str] = None) -> str:
        """Record audio until stopped (Ctrl+C or stop() is called)."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        
        filepath = os.path.join(output_dir, filename)
        os.makedirs(output_dir, exist_ok=True)
        
        q = queue.Queue()
        
        def callback(indata, frames, time, status):
            if status:
                print(f"\nStream status: {status}", file=sys.stderr)
            q.put(indata.copy())
        
        print(f"\n[*] Recording to {filepath}")
        print(f"    Using device: {self.device_name} (index {self.device_index})")
        print("[>] RECORDING... Press Ctrl+C to stop")
        
        data_started = False
        self._recording = True
        self._stop_event.clear()
        
        try:
            with sf.SoundFile(filepath, mode='w', samplerate=self.samplerate,
                             channels=self.channels, subtype='PCM_16') as file:
                with sd.InputStream(samplerate=self.samplerate, device=self.device_index,
                                   channels=self.channels, callback=callback):
                    while not self._stop_event.is_set():
                        try:
                            data = q.get(timeout=0.2)
                            if not data_started:
                                if np.abs(data).max() > 0:
                                    print("[+] Audio stream started (receiving signal!)...")
                                    data_started = True
                            file.write(data)
                        except queue.Empty:
                            continue
        
        except KeyboardInterrupt:
            print("\n[!] Recording stopped by user.")
        except Exception as e:
            print(f"\n[-] Error during recording: {e}")
            raise
        finally:
            self._recording = False
        
        if not data_started:
            print("\n[!] WARNING: No audio data was received during the session!")
        
        print(f"[+] File saved: {filepath}")
        return filepath
    
    def stop(self) -> None:
        """Gracefully stop the recording."""
        if self._recording:
            print("\n[*] Stopping recording...")
            self._stop_event.set()
    
    def get_info(self) -> Dict[str, Any]:
        """Get recorder information."""
        return {
            "type": "legacy",
            "device_name": self.device_name,
            "device_index": self.device_index,
            "samplerate": self.samplerate,
            "channels": self.channels
        }
