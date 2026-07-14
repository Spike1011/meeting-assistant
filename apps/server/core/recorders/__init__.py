"""Recorder modules for audio capture."""
from .base_recorder import BaseRecorder
from .legacy_recorder import LegacyRecorder

__all__ = ['BaseRecorder', 'LegacyRecorder']

# Native recorder only available on macOS
try:
    from .native_recorder import NativeRecorder
    __all__.append('NativeRecorder')
except ImportError:
    NativeRecorder = None
