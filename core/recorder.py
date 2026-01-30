import sounddevice as sd
import soundfile as sf
import numpy as np
import os
from datetime import datetime
import sys

class AudioRecorder:
    """Логика захвата звука"""
    def __init__(self, device_name="Unit", samplerate=48000, channels=3):
        self.device_name = device_name
        self.samplerate = samplerate
        self.channels = channels
        self.device_index = self._find_device_index()

    def _find_device_index(self):
        """Finds the index of the audio device by name."""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if self.device_name in device['name']:
                return i
        
        # Fallback guidance if not found
        print(f"Warning: Device '{self.device_name}' not found. Available devices:")
        print(sd.query_devices())
        raise ValueError(f"Device '{self.device_name}' not found. Please create Aggregate Device with this name.")

    def record(self, output_dir="output", filename=None):
        """Records audio until KeyboardInterrupt (Ctrl+C)."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        
        filepath = os.path.join(output_dir, filename)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        print(f"Recording to {filepath} using device '{self.device_name}'...")
        print("Press Ctrl+C to stop recording.")

        try:
            with sf.SoundFile(filepath, mode='w', samplerate=self.samplerate, 
                              channels=self.channels, subtype='PCM_16') as file:
                def callback(indata, frames, time, status):
                    if status:
                        print(status, file=sys.stderr)
                    file.write(indata)

                with sd.InputStream(samplerate=self.samplerate, device=self.device_index,
                                    channels=self.channels, callback=callback):
                    # Keep the stream active until interrupted
                    while True:
                        sd.sleep(100)
                        
        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
        except Exception as e:
            print(f"\nError during recording: {e}")
            raise
        
        print(f"File saved: {filepath}")
        return filepath 
