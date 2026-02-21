# ============================================================
#  utils/test_overlay.py
#  Run this to preview the overlay without audio or AI.
# ============================================================

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from overlay import OverlayWindow

def main():
    print("Testing overlay window...")
    print("You should see the overlay appear in the bottom-right corner.")
    print("Try Ctrl+H to hide/show, drag the header to move it.")
    print("Press Ctrl+C in terminal to exit.\n")

    overlay = OverlayWindow()
    time.sleep(1)

    test_cases = [
        {
            "urgency": "high",
            "is_question": True,
            "question": "Adi, can you explain your model validation approach?",
            "key_point": None,
            "suggestion": (
                "You validated using a stratified 80/20 train-test split on the Pauri "
                "district dataset. The XGBoost model achieved 94% accuracy with strong "
                "precision on high-risk fire days."
            ),
        },
        {
            "urgency": "medium",
            "is_question": False,
            "question": None,
            "key_point": "Budget approval needed by end of Q2",
            "suggestion": (
                "Worth noting this deadline in relation to your travel grant application "
                "for the WSSCI conference."
            ),
        },
        {
            "urgency": "low",
            "is_question": False,
            "question": None,
            "key_point": "Next meeting scheduled for Friday",
            "suggestion": None,
        },
    ]

    for i, case in enumerate(test_cases):
        print(f"[Test {i+1}] Sending: urgency={case['urgency']}")
        overlay.show(case)
        time.sleep(4)

    print("\nOverlay test complete. Close terminal to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
