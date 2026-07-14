import os
import numpy as np
import soundfile as sf
from typing import List

def merge_audio_files(input_files: List[str], output_file: str) -> str:
    """
    Merge multiple audio files into a single mono/stereo file.
    Weights each stream equally.
    """
    if not input_files:
        raise ValueError("No input files provided for merging")
    
    if len(input_files) == 1:
        # Just copy if single file (though shouldn't happen in dual mode)
        data, samplerate = sf.read(input_files[0])
        sf.write(output_file, data, samplerate)
        return output_file

    audio_data = []
    max_len = 0
    target_samplerate = 0
    
    for f in input_files:
        data, samplerate = sf.read(f)
        # Ensure they have the same samplerate (we assume 48k as per config)
        if target_samplerate == 0:
            target_samplerate = samplerate
        elif samplerate != target_samplerate:
            # Simple check, we could resample but our recorders are configured for the same SR
            print(f"[!] Warning: Samplerate mismatch: {samplerate} vs {target_samplerate}")

        # Convert to mono if it's stereo for easier mixing if needed
        # But actually, we prefer keeping stereo if both are stereo
        if len(data.shape) > 1 and data.shape[1] > 1:
            # Average channels to mono for mixing
            data = np.mean(data, axis=1)
            
        audio_data.append(data)
        max_len = max(max_len, len(data))

    # Pad with zeros to the same length and mix
    mixed_audio = np.zeros(max_len)
    for data in audio_data:
        # Pad at the end
        padded = np.zeros(max_len)
        padded[:len(data)] = data
        mixed_audio += padded

    # Normalize to avoid clipping
    # Since we sum N streams, divide by N or normalize by max
    if len(audio_data) > 0:
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 1.0:
            mixed_audio = mixed_audio / max_val

    # Save as mono WAV (Deepgram loves mono)
    sf.write(output_file, mixed_audio, target_samplerate)
    return output_file
