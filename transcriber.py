# ============================================================
#  transcriber.py  —  Deepgram REST API (fast + reliable)
# ============================================================

import io
import wave
import httpx
import numpy as np
import config


class Transcriber:

    def __init__(self):
        self.api_key = config.DEEPGRAM_API_KEY
        self.url     = "https://api.deepgram.com/v1/listen"
        self.params  = {
            "model":        "nova-2",
            "language":     "en",
            "smart_format": "true",
            "punctuate":    "true",
        }
        self._client = httpx.Client(timeout=8.0)
        print("[Transcriber] ✓ Deepgram Nova-2 ready.")

    def transcribe(self, audio: np.ndarray) -> str:
        # Convert to mono if stereo
        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # Convert float32 → WAV bytes
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(config.SAMPLE_RATE)
            pcm = (audio * 32768).astype(np.int16)
            wf.writeframes(pcm.tobytes())
        wav_bytes = buffer.getvalue()

        try:
            response = self._client.post(
                self.url,
                params  = self.params,
                headers = {
                    "Authorization": f"Token {self.api_key}",
                    "Content-Type":  "audio/wav",
                },
                content = wav_bytes,
            )
            data = response.json()
            text = (data["results"]["channels"][0]
                       ["alternatives"][0]["transcript"].strip())
            return text
        except Exception as e:
            print(f"[Transcriber] Error: {e}")
            return ""

    # Stubs so main.py doesn't break
    def start_stream(self):
        pass

    def stop_stream(self):
        pass