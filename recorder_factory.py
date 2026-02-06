"""Factory for creating appropriate audio recorder based on configuration."""
import platform
from core.config_manager import ConfigManager
from core.recorders.base_recorder import BaseRecorder
from core.recorders.legacy_recorder import LegacyRecorder
from core.recorders.native_recorder import NativeRecorder


class RecorderFactory:
    """Factory pattern for creating audio recorders."""
    
    @staticmethod
    def create_recorder(config_manager: ConfigManager) -> BaseRecorder:
        """
        Create and return the appropriate recorder based on configuration.
        """
        method = config_manager.get_recording_method()
        
        if method == "legacy":
            return RecorderFactory._create_legacy_recorder(config_manager)
        elif method == "native":
            return RecorderFactory._create_native_recorder(config_manager)
        elif method == "dual":
            from core.recorders.multi_recorder import MultiRecorder
            
            # Create both recorders
            native = RecorderFactory._create_native_recorder(config_manager)
            legacy = RecorderFactory._create_legacy_recorder(config_manager)
            
            print("[*] Initializing DUAL Recording Mode (Native + Legacy)")
            return MultiRecorder([native, legacy])
        else:
            raise ValueError(
                f"Invalid recording method: {method}. Must be 'legacy', 'native', or 'dual'."
            )
    
    @staticmethod
    def _create_legacy_recorder(config_manager: ConfigManager) -> LegacyRecorder:
        """Create legacy recorder with configuration."""
        settings = config_manager.get_legacy_settings()
        
        return LegacyRecorder(
            device_name=settings.get("device_name", "Unit"),
            samplerate=settings.get("samplerate", 48000),
            channels=settings.get("channels", None)
        )
    
    @staticmethod
    def _create_native_recorder(config_manager: ConfigManager) -> BaseRecorder:
        """Create native macOS recorder with configuration."""
        # Check if running on macOS
        if platform.system() != "Darwin":
            raise RuntimeError(
                "Native recorder is only available on macOS. "
                "Please set recording_method to 'legacy' in config.json."
            )
        
        # Check macOS version (ScreenCaptureKit requires Ventura+)
        version = platform.mac_ver()[0]
        if version:
            major_version = int(version.split('.')[0])
            if major_version < 13:
                raise RuntimeError(
                    f"Native recorder requires macOS 13.0+ (Ventura), but you have {version}. "
                    "Please use 'legacy' mode or upgrade macOS."
                )
        
        settings = config_manager.get_native_settings()
        
        try:
            # Our updated NativeRecorder now uses AVAssetWriter for robust capture without BlackHole
            print("[*] Using Native macOS Recorder (ScreenCaptureKit + AVAssetWriter)")
            return NativeRecorder(
                samplerate=settings.get("samplerate", 48000),
                exclude_current_process=settings.get("exclude_current_process", True)
            )
        except Exception as e:
            print(f"\n[!] Native recorder error: {e}")
            print("\n[*] Falling back to legacy recorder (requires BlackHole)...")
            
            # Final fallback to legacy recorder
            return RecorderFactory._create_legacy_recorder(config_manager)
    
    @staticmethod
    def list_available_methods() -> list:
        """
        List available recording methods on this system.
        """
        methods = ['legacy', 'dual']  # Legacy and dual (with fallback) always available
        
        # Check if native is available
        if platform.system() == "Darwin":
            try:
                version = platform.mac_ver()[0]
                if version:
                    major_version = int(version.split('.')[0])
                    if major_version >= 13:
                        # Try importing native dependencies
                        try:
                            from core.recorders.native_recorder import NATIVE_AVAILABLE
                            if NATIVE_AVAILABLE:
                                methods.append('native')
                        except:
                            pass
            except:
                pass
        
        return methods
