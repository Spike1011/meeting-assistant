"""
Native macOS Audio Recorder using ScreenCaptureKit and AVAssetWriter.
This implementation captures system audio without BlackHole by using
AVFoundation's AVAssetWriter to save CMSampleBuffers directly.
"""
import os
import sys
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

try:
    import objc
    from Foundation import NSObject, NSURL, NSRunLoop, NSDefaultRunLoopMode
    from AVFoundation import (
        AVAssetWriter, AVAssetWriterInput, AVMediaTypeAudio,
        AVFormatIDKey, AVSampleRateKey, AVNumberOfChannelsKey,
        AVFileTypeWAVE, AVLinearPCMBitDepthKey, AVLinearPCMIsFloatKey,
        AVLinearPCMIsBigEndianKey, AVLinearPCMIsNonInterleaved
    )
    from ScreenCaptureKit import (
        SCStreamConfiguration, SCStream, SCContentFilter,
        SCShareableContent, SCStreamOutputTypeAudio
    )
    from CoreMedia import CMSampleBufferGetPresentationTimeStamp
    from CoreAudio import kAudioFormatLinearPCM
    
    NATIVE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Native recorder dependencies not available: {e}")
    NATIVE_AVAILABLE = False


if NATIVE_AVAILABLE:
    class SCStreamAudioWriterDelegate(NSObject):
        """Delegate to receive audio samples and write them to AVAssetWriter."""
        
        def initWithWriterInput_andRecorder_(self, writer_input, recorder):
            self = objc.super(SCStreamAudioWriterDelegate, self).init()
            if self is None: return None
            self.writer_input = writer_input
            self.recorder = recorder
            self.session_started = False
            return self
        
        def stream_didOutputSampleBuffer_ofType_(self, stream, sampleBuffer, outputType):
            """Called when audio data is available."""
            if outputType == SCStreamOutputTypeAudio:
                if not self.recorder.is_writing:
                    return

                if not self.session_started:
                    # Start session with the first sample buffer's timestamp
                    timestamp = CMSampleBufferGetPresentationTimeStamp(sampleBuffer)
                    self.recorder.writer.startSessionAtSourceTime_(timestamp)
                    self.session_started = True
                    print("[+] Audio session started")

                if self.writer_input.isReadyForMoreMediaData():
                    success = self.writer_input.appendSampleBuffer_(sampleBuffer)
                    if not success:
                        # Only print once to avoid spamming
                        if not hasattr(self, '_append_failed'):
                            print(f"[!] Failed to append audio buffer: {self.recorder.writer.error()}")
                            self._append_failed = True


class NativeRecorder:
    """
    Native macOS audio recorder using ScreenCaptureKit and AVAssetWriter.
    Doesn't require BlackHole or any virtual audio devices.
    """
    
    def __init__(self, samplerate: int = 48000, exclude_current_process: bool = True):
        if not NATIVE_AVAILABLE:
            raise RuntimeError(
                "Native recorder not available. Please install required dependencies:\n"
                "pip install pyobjc-framework-ScreenCaptureKit pyobjc-framework-AVFoundation"
            )
        
        # Check macOS version
        import platform
        version = platform.mac_ver()[0]
        major_version = int(version.split('.')[0])
        if major_version < 13:
            raise RuntimeError(
                f"Native recorder requires macOS 13.0+, but you have {version}"
            )
        
        self.samplerate = samplerate
        self.exclude_current_process = exclude_current_process
        self.is_writing = False
        self._stop_event = threading.Event()
        
        self.writer = None
        self.writer_input = None
        self.stream = None
        self.delegate = None
        
        print(f"[*] Native macOS Recorder Initialized")
        print(f"    ├─ Method: ScreenCaptureKit + AVAssetWriter")
        print(f"    ├─ Sample Rate: {self.samplerate} Hz")
        print(f"    └─ NO BlackHole required!")

    @property
    def is_recording(self) -> bool:
        """Return True if currently recording."""
        return self.is_writing
    
    def _setup_writer(self, filepath: str):
        """Setup AVAssetWriter for the output file."""
        # AVAssetWriter cannot overwrite files, so we must delete if exists
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                print(f"[!] Warning: Could not remove existing file {filepath}: {e}")

        url = NSURL.fileURLWithPath_(filepath)
        
        # Create asset writer (WAV)
        self.writer, error = AVAssetWriter.alloc().initWithURL_fileType_error_(
            url, AVFileTypeWAVE, None
        )
        
        if error:
            raise RuntimeError(f"Failed to create AVAssetWriter: {error}")
            
        # Define audio settings (Linear PCM 16-bit)
        audio_settings = {
            AVFormatIDKey: kAudioFormatLinearPCM,
            AVSampleRateKey: float(self.samplerate),
            AVNumberOfChannelsKey: 2,
            AVLinearPCMBitDepthKey: 16,
            AVLinearPCMIsFloatKey: False,
            AVLinearPCMIsBigEndianKey: False,
            AVLinearPCMIsNonInterleaved: False
        }
        
        self.writer_input = AVAssetWriterInput.assetWriterInputWithMediaType_outputSettings_(
            AVMediaTypeAudio, audio_settings
        )
        self.writer_input.setExpectsMediaDataInRealTime_(True)
        
        if self.writer.canAddInput_(self.writer_input):
            self.writer.addInput_(self.writer_input)
        else:
            raise RuntimeError("Could not add audio input to AVAssetWriter")
            
        self.writer.startWriting()
        print("[+] AVAssetWriter started")

    def _setup_stream(self):
        """Setup ScreenCaptureKit stream using completion handlers."""
        # Get shareable content using completion handler
        finished = threading.Event()
        content_container = [None, None]
        
        def handler(content, error):
            content_container[0] = content
            content_container[1] = error
            finished.set()
            
        # Call the completion handler version
        SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
            False, True, handler
        )
        
        # Wait for completion (timeout 10s)
        if not finished.wait(timeout=10):
            raise RuntimeError("Timed out waiting for shareable content")
            
        content, error = content_container
        if error:
            raise RuntimeError(f"Failed to get shareable content: {error}")
        
        if not content or not content.displays():
            raise RuntimeError("No displays found for capture")
            
        # Filter for the first display
        display = content.displays()[0]
        content_filter = SCContentFilter.alloc().initWithDisplay_excludingApplications_exceptingWindows_(
            display, [], []
        )
        
        # Configuration
        config = SCStreamConfiguration.alloc().init()
        config.setCapturesAudio_(True)
        config.setSampleRate_(self.samplerate)
        config.setChannelCount_(2)
        if hasattr(config, 'setExcludesCurrentProcessAudio_'):
            config.setExcludesCurrentProcessAudio_(self.exclude_current_process)
            
        # Create delegate
        self.delegate = SCStreamAudioWriterDelegate.alloc().initWithWriterInput_andRecorder_(
            self.writer_input, self
        )
        
        self.stream = SCStream.alloc().initWithFilter_configuration_delegate_(
            content_filter, config, None
        )
        
        # Add output
        error = None
        # Passing None for queue often works in PyObjC as it defaults to the main queue
        success, error = self.stream.addStreamOutput_type_sampleHandlerQueue_error_(
            self.delegate, SCStreamOutputTypeAudio, None, None
        )
        
        if not success:
            raise RuntimeError(f"Failed to add stream output: {error}")

    def record(self, output_dir: str = "output", filename: Optional[str] = None) -> str:
        """Record system audio until stopped."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        elif not filename.endswith(".wav"):
            filename = filename.rsplit('.', 1)[0] + ".wav"
            
        filepath = os.path.join(output_dir, filename)
        os.makedirs(output_dir, exist_ok=True)
        
        print("\n" + "-"*70)
        print("  [*] NATIVE RECORDING (без BlackHole)")
        print("-"*70)
        
        try:
            self._setup_writer(filepath)
            self._setup_stream()
            
            # Start capture
            self.is_writing = True
            
            # SCStream.startCaptureWithCompletionHandler_
            finished = threading.Event()
            def start_handler(error):
                if error:
                    print(f"[-] Failed to start capture: {error}")
                finished.set()
                
            self.stream.startCaptureWithCompletionHandler_(start_handler)
            finished.wait(timeout=5)
            
            print(f"\n[*] Output: {filepath}")
            print("[>] RECORDING... Press Ctrl+C to stop")
            
            self._stop_event.clear()
            while not self._stop_event.is_set():
                # Allow run loop to process callbacks if needed
                NSRunLoop.currentRunLoop().runMode_beforeDate_(
                    NSDefaultRunLoopMode, 
                    datetime.now()
                )
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n[!] Interrupted by user")
        except Exception as e:
            print(f"\n[-] Error during recording: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
            
        return filepath
    
    def stop(self) -> None:
        """Gracefully stop recording."""
        if not self.is_writing:
            return
            
        print("\n[*] Stopping native recorder...")
        self.is_writing = False
        self._stop_event.set()
        
        if self.stream:
            # SCStream.stopCaptureWithCompletionHandler_
            finished_stop = threading.Event()
            def stop_handler(error):
                finished_stop.set()
                
            self.stream.stopCaptureWithCompletionHandler_(stop_handler)
            finished_stop.wait(timeout=5)
            
        if self.writer:
            if self.writer_input:
                self.writer_input.markAsFinished()
            
            finished_writer = threading.Event()
            def writer_handler():
                finished_writer.set()
                
            self.writer.finishWritingWithCompletionHandler_(writer_handler)
            # Wait for finishWriting
            if not finished_writer.wait(timeout=10):
                 print("[!] Warning: finishWriting timed out")
            
            if self.writer.status() == 3: # Failed
                print(f"[-] Writer failed: {self.writer.error()}")
            else:
                print("[+] Audio file finalized")
        
        print("[+] Native recording complete")

    def get_info(self) -> Dict[str, Any]:
        """Get recorder information."""
        return {
            "type": "native",
            "method": "ScreenCaptureKit + AVAssetWriter",
            "samplerate": self.samplerate,
            "status": "active"
        }
