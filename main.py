# ============================================================
#  main.py  —  Entry point for the Meeting Assistant
# ============================================================

import time
import threading
import config
from audio_capture import AudioCapture
from transcriber   import Transcriber
from ai_processor  import AIProcessor
from overlay       import OverlayWindow


# ============================================================
#  EDIT THIS BEFORE EACH MEETING
#  The more detail you add, the better the AI suggestions
# ============================================================
MEETING_CONTEXT = """
Meeting type   : [e.g. PhD review / job interview / team standup]
My name        : Adi
My role        : [e.g. Presenter / Candidate / Team member]

Key topics I'm prepared on:
  - [Topic 1]
  - [Topic 2]

Questions I'm likely to be asked:
  Q: [Likely question 1]
  A: [My prepared answer]

People in the meeting:
  - [Name] — [Their role/interest]

Things I should avoid or be careful about:
  - [Any sensitive area]
"""
# ============================================================


def _transcription_worker(capture: AudioCapture,
                           transcriber: Transcriber,
                           ai: AIProcessor,
                           overlay: OverlayWindow):
    """
    Runs in a background thread.
    Pulls audio chunks → transcribes → analyses → updates overlay.
    """
    print("[Main] Worker thread started. Listening for speech...\n")
    while True:
        try:
            audio = capture.audio_queue.get(timeout=1.0)
        except Exception:
            continue

        # Step 1: Transcribe
        text = transcriber.transcribe(audio)
        if not text:
            continue
        print(f"[Transcript] {text}")

        # Step 2: AI analysis
        result = ai.process(text)
        if result is None:
            continue
        print(f"[AI]         urgency={result.get('urgency')}  "
              f"question={result.get('is_question')}  "
              f"suggestion={'yes' if result.get('suggestion') else 'no'}")

        # Step 3: Update overlay
        overlay.show(result)


def main():
    print("=" * 55)
    print("   Meeting Assistant  —  Starting up")
    print("=" * 55)

    # Validate API key
    if config.GROQ_API_KEY == "your_groq_api_key_here":
        print("\n[ERROR] Please set your GROQ_API_KEY in config.py")
        print("        Get a free key at: https://console.groq.com\n")
        return

    # 1. Overlay first (runs in its own daemon thread)
    overlay = OverlayWindow()
    time.sleep(0.8)  # Let Tk initialise

    # 2. AI processor
    ai = AIProcessor()
    ai.set_meeting_context(MEETING_CONTEXT)

    # 3. Transcriber (loads Whisper model — may take ~10s first time)
    transcriber = Transcriber()

    # 4. Audio capture
    capture = AudioCapture()
    capture.start()

    # 5. Worker thread
    worker = threading.Thread(
        target=_transcription_worker,
        args=(capture, transcriber, ai, overlay),
        daemon=True,
    )
    worker.start()

    print("\n[Main] ✓ All systems running.")
    print("[Main]   Ctrl+C to stop  |  Ctrl+H to hide overlay  |  Ctrl+Q to quit overlay\n")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
        capture.stop()
        print("[Main] Goodbye.")


if __name__ == "__main__":
    main()
