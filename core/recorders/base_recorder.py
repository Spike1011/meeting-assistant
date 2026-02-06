from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseRecorder(ABC):
    """Abstract base class for audio recorders."""

    @property
    @abstractmethod
    def is_recording(self) -> bool:
        """Return whether the recorder is currently recording."""
        pass

    @abstractmethod
    def record(self, output_dir: str = "output", filename: Optional[str] = None) -> str:
        """
        Start recording audio until stopped.
        
        Args:
            output_dir: Directory to save the recording
            filename: Optional filename for the recording
            
        Returns:
            Path to the saved audio file
        """
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """
        Gracefully stop the recording.
        This should be called before exiting to ensure proper file cleanup.
        """
        pass
    
    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """
        Get information about the recorder configuration.
        
        Returns:
            Dictionary with recorder metadata (device, samplerate, channels, etc.)
        """
        pass
