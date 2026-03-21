import threading
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional


class AudioRecorder:
    """
    Records audio from the microphone.
    Supports device selection and configurable visual gain for level display.
    Provides real-time RMS level via callback for UI visualization.
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        level_callback: Optional[Callable[[float], None]] = None,
        device: Optional[int] = None,
        gain: int = 50,
        gain_auto: bool = True,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.level_callback = level_callback
        self.device = device        # None = 系統預設麥克風
        self.gain = gain            # 視覺感度倍率 (5~200)
        self.gain_auto = gain_auto  # 自動調整感度
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._recent_peaks: list[float] = []  # 自動增益用的近期峰值

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
            self._recent_peaks = []

        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            )
        except Exception:
            # 指定裝置不可用，fallback 至系統預設
            print(f"[recorder] Device {self.device} unavailable, falling back to system default.")
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                device=None,
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

                    # 自動增益：追蹤近期峰值，動態調整 gain 使視覺電平保持在合理範圍
                    if self.gain_auto:
                        self._recent_peaks.append(rms)
                        if len(self._recent_peaks) > 20:  # 約 1 秒的歷史
                            self._recent_peaks.pop(0)
                        if len(self._recent_peaks) >= 10:
                            peak = max(self._recent_peaks[-10:])
                            if peak > 0:
                                current_level = peak * self.gain
                                if current_level < 0.3:   # 太安靜，提高感度
                                    self.gain = min(self.gain * 1.15, 200)
                                elif current_level > 0.85: # 快要飽和，降低感度
                                    self.gain = max(self.gain * 0.88, 5)

                    self.level_callback(min(rms * self.gain, 1.0))

            except Exception:
                break

    def stop(self) -> bytes:
        """Stop recording and return WAV bytes."""
        with self._lock:
            self._recording = False

        if hasattr(self, '_poll_thread') and self._poll_thread.is_alive():
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
