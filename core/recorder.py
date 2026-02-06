import sounddevice as sd
import soundfile as sf
import numpy as np
import os
import queue
import sys
from datetime import datetime

class AudioRecorder:
    """Логика захвата звука через одно устройство (например, агрегатное Unit)"""
    def __init__(self, device_name="Unit", samplerate=48000, channels=None):
        self.device_name = device_name
        self.samplerate = samplerate
        self.device_index = self._find_device_index()
        
        # Получаем информацию об устройстве для проверки каналов
        device_info = sd.query_devices(self.device_index)
        max_channels = device_info.get('max_input_channels', 0)
        
        if channels is None:
            self.channels = max_channels
        else:
            self.channels = channels
            if self.channels > max_channels:
                print(f"Warning: Requested {channels} channels, but device only supports {max_channels}. Using {max_channels}.")
                self.channels = max_channels

        print(f"Initialized AudioRecorder: Device='{self.device_name}' (index {self.device_index}), Samplerate={self.samplerate}, Channels={self.channels}")

    def _find_device_index(self):
        """Находит индекс аудиоустройства по имени."""
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if self.device_name in device['name']:
                return i
        
        print(f"Warning: Device '{self.device_name}' not found. Available devices:")
        print(sd.query_devices())
        raise ValueError(f"Device '{self.device_name}' not found.")

    def record(self, output_dir="output", filename=None):
        """Запись звука до прерывания (Ctrl+C)."""
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

        print(f"\nRecording to {filepath}")
        print(f"Using device: {self.device_name} (index {self.device_index})")
        print("Press Ctrl+C to stop recording.")

        data_started = False
        
        try:
            with sf.SoundFile(filepath, mode='w', samplerate=self.samplerate, 
                               channels=self.channels, subtype='PCM_16') as file:
                with sd.InputStream(samplerate=self.samplerate, device=self.device_index,
                                    channels=self.channels, callback=callback):
                    while True:
                        try:
                            data = q.get(timeout=0.2)
                            if not data_started:
                                if np.abs(data).max() > 0:
                                    print("Audio stream started (receiving signal!)...")
                                    data_started = True
                            file.write(data)
                        except queue.Empty:
                            continue
                        
        except KeyboardInterrupt:
            print("\nRecording stopped by user.")
        except Exception as e:
            print(f"\nError during recording: {e}")
            raise
        
        if not data_started:
            print("\nWARNING: No audio data was received during the session!")
        
        print(f"File saved: {filepath}")
        return filepath
