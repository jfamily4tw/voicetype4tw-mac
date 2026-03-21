import threading
import numpy as np
import sounddevice as sd
import io
import wave
from typing import Callable, Optional

SILENCE_THRESHOLD = 0.003  # 放大後任一 chunk 峰值 RMS < 0.3% 才視為靜音


class AudioRecorder:
    """
    Records audio from the microphone.

    gain (int, 50-300): 使用者手動設定的基底放大倍率，100 = ×1.0（不變）。
    gain_auto (bool): 啟用 AGC，用獨立的 _agc_factor 動態微調，不覆蓋手動 gain。
    is_silent (bool): stop() 後設定，RMS 過低時為 True，main.py 可跳過 STT。
    """

    def __init__(
        self,
        samplerate: int = 16000,
        channels: int = 1,
        level_callback: Optional[Callable[[float], None]] = None,
        device: Optional[int] = None,
        gain: int = 100,
        gain_auto: bool = True,
    ):
        self.samplerate = samplerate
        self.channels = channels
        self.level_callback = level_callback
        self.device = device
        self.gain = gain            # 使用者手動設定 (50~300)
        self.gain_auto = gain_auto  # AGC 開關

        self._recording = False
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._agc_factor: float = 1.0       # AGC 動態倍率（不覆蓋 gain）
        self._recent_peaks: list[float] = []

        self.is_silent: bool = False        # 錄音結束後由 stop() 設定

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
            self._agc_factor = 1.0
            self._recent_peaks = []
            self.is_silent = False

        try:
            self._stream = sd.InputStream(
                samplerate=self.samplerate,
                channels=self.channels,
                dtype="int16",
                device=self.device,
            )
        except Exception:
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
                frames_to_read = int(self.samplerate * 0.05)
                if not self._stream or not self._stream.active:
                    break

                indata, overflowed = self._stream.read(frames_to_read)

                # 有效放大倍率 = 手動 gain × AGC 動態係數
                factor = (self.gain / 100.0) * self._agc_factor
                if factor != 1.0:
                    amplified = np.clip(
                        indata.astype(np.float32) * factor, -32768, 32767
                    ).astype(np.int16)
                else:
                    amplified = indata

                with self._lock:
                    if not self._recording:
                        break
                    self._frames.append(amplified)

                # 放大後的 RMS 傳給 UI
                rms = float(np.sqrt(np.mean(amplified.astype(np.float32) ** 2))) / 32768.0
                if self.level_callback:
                    self.level_callback(min(rms, 1.0))

                # AGC：根據近期峰值動態調整 _agc_factor，不動 self.gain
                if self.gain_auto:
                    self._recent_peaks.append(rms)
                    if len(self._recent_peaks) > 20:
                        self._recent_peaks.pop(0)
                    if len(self._recent_peaks) >= 10:
                        peak = max(self._recent_peaks[-10:])
                        if peak > 0:
                            if peak < 0.30:   # 太安靜，放大 AGC
                                self._agc_factor = min(self._agc_factor * 1.15, 8.0)
                            elif peak > 0.85: # 快飽和，縮小 AGC
                                self._agc_factor = max(self._agc_factor * 0.88, 0.1)

            except Exception:
                break


    def stop(self) -> bytes:
        """Stop recording and return WAV bytes. Sets is_silent."""
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

        # 靜音判斷：用峰值（任一 chunk 中最大的 RMS），
        # 只要有任何一段有聲音就不算靜音，避免長段錄音被平均值拉低而誤判。
        if self._frames:
            peak_rms = max(
                float(np.sqrt(np.mean(chunk.astype(np.float32) ** 2))) / 32768.0
                for chunk in self._frames
            )
            self.is_silent = peak_rms < SILENCE_THRESHOLD
            print(f"[recorder] peak_rms={peak_rms:.4f}, silent={self.is_silent}")
        else:
            self.is_silent = True

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
            wf.setsampwidth(2)
            wf.setframerate(self.samplerate)
            wf.writeframes(audio.tobytes())
        return buf.getvalue()
