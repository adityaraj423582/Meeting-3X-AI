# ============================================================
#  audio_capture.py  —  Captures system audio via WASAPI Loopback
#  No VoiceMeeter or VB-Cable needed — uses Windows built-in API
# ============================================================

import pyaudiowpatch as pyaudio
import numpy as np
import threading
import queue
import config


class AudioCapture:
    """
    Uses WASAPI Loopback to capture whatever is playing on your speakers.
    This captures meeting audio (what you hear) with zero extra software.
    """

    def __init__(self):
        self.sample_rate  = config.SAMPLE_RATE
        self.chunk_size   = 1024
        self.audio_queue  = queue.Queue(maxsize=10)
        self.running      = False
        self._thread      = None

        # Find the default loopback device (what you hear)
        p = pyaudio.PyAudio()
        self.device_index  = None
        self.device_rate   = None
        self.device_ch     = None

        print("\n[AudioCapture] Looking for loopback device...")
        try:
            # Get default output device (speakers/headphones)
            default_out = p.get_default_wasapi_loopback()
            self.device_index = default_out["index"]
            self.device_rate  = int(default_out["defaultSampleRate"])
            self.device_ch    = default_out["maxInputChannels"]
            print(f"[AudioCapture] ✓ Loopback device: {default_out['name']}")
            print(f"[AudioCapture]   Sample rate: {self.device_rate} Hz, Channels: {self.device_ch}")
        except Exception as e:
            print(f"[AudioCapture] ✗ Could not find loopback device: {e}")
            print("[AudioCapture]   Make sure audio is playing and try again.")
            p.terminate()
            raise RuntimeError("WASAPI loopback device not found.")

        p.terminate()

    # ----------------------------------------------------------
    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[AudioCapture] Started — capturing system audio.")

    def stop(self):
        self.running = False
        print("[AudioCapture] Stopped.")

    # ----------------------------------------------------------
    def _loop(self):
        p      = pyaudio.PyAudio()
        stream = p.open(
            format               = pyaudio.paInt16,
            channels             = self.device_ch,
            rate                 = self.device_rate,
            input                = True,
            input_device_index   = self.device_index,
            frames_per_buffer    = self.chunk_size,
        )

        frames_per_segment = int(
            self.device_rate * config.CHUNK_SECONDS / self.chunk_size
        )
        overlap_frames = int(frames_per_segment * config.OVERLAP_RATIO)
        buffer = []

        while self.running:
            raw = stream.read(self.chunk_size, exception_on_overflow=False)
            pcm = np.frombuffer(raw, dtype=np.int16)

            # Mix stereo to mono if needed
            if self.device_ch == 2:
                pcm = pcm.reshape(-1, 2).mean(axis=1).astype(np.int16)

            # Resample to 16000 Hz if device rate is different
            if self.device_rate != 16000:
                ratio  = 16000 / self.device_rate
                new_len = int(len(pcm) * ratio)
                indices = np.linspace(0, len(pcm) - 1, new_len).astype(int)
                pcm     = pcm[indices]

            buffer.append(pcm)

            if len(buffer) >= frames_per_segment:
                segment = np.concatenate(buffer).astype(np.float32) / 32768.0
                if self.audio_queue.full():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.audio_queue.put(segment)
                buffer = buffer[frames_per_segment - overlap_frames:]

        stream.stop_stream()
        stream.close()
        p.terminate()