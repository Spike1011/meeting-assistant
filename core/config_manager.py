import json
import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv

class ConfigManager:
    """Manages application configuration from config.json with .env fallback for API keys."""
    
    DEFAULT_CONFIG = {
        "recording_method": "legacy",
        "legacy_settings": {
            "device_name": "Unit",
            "samplerate": 48000,
            "channels": None
        },
        "native_settings": {
            "samplerate": 48000,
            "exclude_current_process": True
        },
        "transcription": {
            "model": "nova-2",
            "language": "ru",
            "diarize": True,
            "smart_format": True,
            "timeout": 600
        }
    }
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize config manager and load configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        
        # Load .env for API key fallback
        load_dotenv()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return self._merge_with_defaults(loaded_config)
            except Exception as e:
                print(f"[!] Warning: Failed to load config from {self.config_path}: {e}")
                print("[*] Using default configuration.")
                return self.DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self._save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_with_defaults(self, loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded config with defaults to ensure all keys exist."""
        merged = self.DEFAULT_CONFIG.copy()
        
        # Deep merge
        for key, value in loaded.items():
            if isinstance(value, dict) and key in merged:
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        
        return merged
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"[!] Warning: Failed to save config to {self.config_path}: {e}")
    
    def save(self) -> None:
        """Save current configuration to file."""
        self._save_config(self.config)
    
    # Recording Settings
    def get_recording_method(self) -> str:
        """Get recording method: 'native' or 'legacy'."""
        return self.config.get("recording_method", "legacy")
    
    def set_recording_method(self, method: str) -> None:
        """Set recording method."""
        if method not in ["native", "legacy", "dual"]:
            raise ValueError("Recording method must be 'native', 'legacy', or 'dual'")
        self.config["recording_method"] = method
        self.save()
    
    def get_legacy_settings(self) -> Dict[str, Any]:
        """Get legacy recorder settings."""
        return self.config.get("legacy_settings", self.DEFAULT_CONFIG["legacy_settings"])
    
    def get_native_settings(self) -> Dict[str, Any]:
        """Get native recorder settings."""
        return self.config.get("native_settings", self.DEFAULT_CONFIG["native_settings"])
    
    def set_legacy_device_name(self, device_name: str) -> None:
        """Set legacy recorder device name."""
        if "legacy_settings" not in self.config:
            self.config["legacy_settings"] = self.DEFAULT_CONFIG["legacy_settings"].copy()
        self.config["legacy_settings"]["device_name"] = device_name
        self.save()
    
    # API Keys (only from environment)
    def get_deepgram_api_key(self) -> Optional[str]:
        """Get Deepgram API key from .env."""
        return os.getenv("DEEPGRAM_API_KEY")
    
    def get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from .env."""
        return os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
    
    # Transcription Settings
    def get_transcription_settings(self) -> Dict[str, Any]:
        """Get transcription settings."""
        return self.config.get("transcription", self.DEFAULT_CONFIG["transcription"])
    
    def get_transcription_model(self) -> str:
        """Get transcription model name."""
        return self.get_transcription_settings().get("model", "nova-2")
    
    def get_transcription_language(self) -> str:
        """Get transcription language."""
        return self.get_transcription_settings().get("language", "ru")
    
    def get_transcription_timeout(self) -> int:
        """Get transcription timeout in seconds."""
        return self.get_transcription_settings().get("timeout", 600)
