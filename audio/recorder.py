import threading
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional


class AudioRecorder:
    """
    Records audio from the default microphone.
    Provides real-time RMS level via callback for UI visualization.
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        level_callback: Optional[Callable[[float], None]] = None,
        device: Optional[int] = None,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.level_callback = level_callback
        self.device = device  # None = 系統預設麥克風
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        
        # Event handlers for main.py integration
        self.on_start: Optional[Callable[[], None]] = None
        self.on_stop: Optional[Callable[[bytes], None]] = None


    def start(self) -> None:
        """Start recording audio."""
        with self._lock:
            if self._recording:
                return
            self._frames = []
            self._recording = True

        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="int16",
            device=self.device,
        )
        self._stream.start()
        
        self._poll_thread = threading.Thread(target=self._poll_audio, daemon=True)
        self._poll_thread.start()
        
        if self.on_start:
            self.on_start()

    def _poll_audio(self) -> None:
        while self._recording and self._stream:
            try:
                # 每次讀取 0.05 秒的區塊 (16kHz * 0.05 = 800 frames)
                frames_to_read = int(self.samplerate * 0.05)
                # Ensure we only try to read if stream is active and we are still recording
                if not self._stream or not self._stream.active:
                    break
                    
                indata, overflowed = self._stream.read(frames_to_read)
                
                with self._lock:
                    if not self._recording:
                        break
                    self._frames.append(indata.copy())
                
                # 計算音量 RMS (0.0 ~ 1.0) 回傳給 UI
                if self.level_callback:
                    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2))) / 32768.0
                    self.level_callback(min(rms * 50, 1.0))

            except Exception as e:
                # 當串流被外界中止或關閉，將引發例外中斷讀取
                break

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        with self._lock:
            self._recording = False
            
        if hasattr(self, '_poll_thread') and self._poll_thread.is_alive():
            # Wait safely for the blocking read to finish (at most 0.1 ~ 0.2s) before closing the stream
            self._poll_thread.join(timeout=0.5)

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        wav_bytes = self._to_wav_bytes()
        if self.on_stop:
            self.on_stop(wav_bytes)
        return wav_bytes

    def _to_wav_bytes(self) -> bytes:
        if not self._frames:
            return b""
        audio = np.concatenate(self._frames, axis=0)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
