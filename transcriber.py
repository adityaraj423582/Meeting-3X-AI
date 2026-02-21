# ============================================================
#  transcriber.py  —  Whisper transcription (GPU accelerated)
# ============================================================

import whisper
import torch
import numpy as np
import config


class Transcriber:
    """
    Loads Whisper model onto RTX 3050 via CUDA.
    Falls back to CPU if CUDA is not available.
    """

    def __init__(self):
        self.device   = "cuda" if torch.cuda.is_available() else "cpu"
        self.fp16     = (self.device == "cuda")

        print(f"\n[Transcriber] Device  : {self.device.upper()}")
        if self.device == "cuda":
            print(f"[Transcriber] GPU     : {torch.cuda.get_device_name(0)}")
        print(f"[Transcriber] Model   : whisper-{config.WHISPER_MODEL}")
        print(f"[Transcriber] Loading model (first run downloads it)...")

        self.model = whisper.load_model(config.WHISPER_MODEL, device=self.device)
        print("[Transcriber] ✓ Model ready.")

    # ----------------------------------------------------------
    def transcribe(self, audio: np.ndarray) -> str:
        """
        audio : float32 numpy array at 16 kHz
        returns: transcribed text, or empty string if silence/noise
        """
        result = self.model.transcribe(
            audio,
            language                   = "en",
            fp16                       = self.fp16,
            condition_on_previous_text = True,
            temperature                = 0.0,         # Deterministic
            no_speech_threshold        = 0.6,         # Skip silent chunks
            compression_ratio_threshold= 2.4,
        )
        text = result["text"].strip()

        # Filter very short or repetitive noise transcriptions
        if len(text) < 8:
            return ""
        return text
