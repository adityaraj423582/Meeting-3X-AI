# ============================================================
#  main.py  —  Entry point
# ============================================================

import time
import threading
import numpy as np
import config
from audio_capture import AudioCapture
from transcriber   import Transcriber
from ai_processor  import AIProcessor
from overlay       import OverlayWindow

EXTRA_CONTEXT = """
Meeting type   : Interview
My name        : Aditya Raj Singh
My degree      : M.Tech Applied Mathematics, IIT Roorkee
My GATE rank   : AIR 820
My CodeChef    : 4-Star, Rating 1892

INTERNSHIPS:
1. Oracle Apex Intern | Beyondata | July 2023 - June 2024
   - Fabric anomaly detection using OpenCV and TensorFlow, 93% accuracy
   - SQL, PL/SQL, Oracle Cloud Infrastructure, OCR

2. SAP - ML | National University of Singapore | Aug 2022 - Sep 2022
   - Deep learning facial recognition under Prof. Dr. Tan (NUS)
   - 70% improvement in recognition accuracy

3. SDE Intern | Wissen Zentrum Technology | Jan 2022 - Apr 2022
   - FastAPI backend, GraphQL, OAuth 2.0, MongoDB

PROJECTS:
1. Multi-Stage Interpreter | Prof Pankaj Gautam
   - Symbol Table, Recursive Descent, Abstract Syntax Tree

2. ML Model for Pit Stop Prediction | Prof Millie Pant
   - 88% accuracy, cross-validation, hyperparameter tuning

3. Low-Latency HFT Agent using Offline RL | Prof Millie Pant
   - RL trading system, Sharpe Ratio, drawdown analysis

4. Forest Fire Prediction | Dr. Deepak Sharma (IIT Roorkee + OSU)
   - XGBoost on MODIS satellite data, Pauri district
   - Firebrand generation analysis, CIRE Laboratory dataset

ACHIEVEMENTS:
- GATE AIR 820
- CodeChef 4-Star (Rating 1892)
- Google Hash Code finalist
- Top 14% LeetCode worldwide
- Oracle Apex Cloud Developer Professional

SKILLS:
- ML/DL: TensorFlow, XGBoost, Scikit-learn, Reinforcement Learning
- Backend: FastAPI, GraphQL, OAuth 2.0, MongoDB
- Data: Pandas, NumPy, SQL, PL/SQL
- Cloud: Oracle Cloud Infrastructure
- Languages: Python, Kotlin, SQL, C++
"""

# ── Tuning ───────────────────────────────────────────────────
COLLECT_SECONDS = 4.0   # Collect audio for this long after mic click
CHUNK_SECONDS   = 2     # Keep small so audio arrives fast


def _worker(capture, transcriber, ai, overlay):
    print("[Main] Worker ready. Press Ctrl+Z or click mic.\n")

    while True:
        # Wait for mic
        if not overlay.mic_is_active():
            time.sleep(0.1)
            continue

        # Flush stale audio
        while not capture.audio_queue.empty():
            try:
                capture.audio_queue.get_nowait()
            except:
                break

        print("[Main] 🎙 Collecting audio...")

        # Collect multiple chunks for COLLECT_SECONDS
        collected = []
        deadline  = time.time() + COLLECT_SECONDS

        while time.time() < deadline:
            remaining = deadline - time.time()
            try:
                audio = capture.audio_queue.get(timeout=min(remaining, 0.5))
                collected.append(audio)
            except:
                continue

        if not collected:
            print("[Main] No audio received.")
            overlay.reset_mic()
            continue

        # Merge all chunks into one
        merged = np.concatenate(collected, axis=0)
        print(f"[Main] Transcribing {len(collected)} chunks...")

        text = transcriber.transcribe(merged)

        if not text:
            print("[Main] No speech detected.")
            overlay.reset_mic()
            continue

        print(f"[Transcript] {text}")

        result = ai.process(text)
        if result:
            print(f"[AI] type={result.get('question_type')}")
            overlay.show(result)
        else:
            print("[Main] No question detected.")
            overlay.reset_mic()


def main():
    print("=" * 55)
    print("   Meeting Assistant  —  Starting up")
    print("=" * 55)

    if config.GROQ_API_KEY == "your_groq_api_key_here":
        print("\n[ERROR] Set GROQ_API_KEY in config.py\n")
        return

    # 1. Overlay
    overlay = OverlayWindow()
    time.sleep(0.8)

    # 2. AI
    ai = AIProcessor()
    ai.set_meeting_context(EXTRA_CONTEXT)
    overlay.set_ai_callback(lambda q: ai.ask(q))

    # 3. Transcriber
    transcriber = Transcriber()

    # 4. Audio — keep chunk size small for fast collection
    capture = AudioCapture()
    capture.start()

    # 5. Worker
    threading.Thread(target=_worker,
                     args=(capture, transcriber, ai, overlay),
                     daemon=True).start()

    print("\n[Main] ✓ All systems running.")
    print("[Main]   Ctrl+Z = start  |  Ctrl+X = stop  |  Ctrl+H = hide\n")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        capture.stop()
        print("\n[Main] Goodbye.")


if __name__ == "__main__":
    main()