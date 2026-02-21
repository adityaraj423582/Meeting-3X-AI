# ============================================================
#  ai_processor.py  —  Groq AI analysis + question detection
# ============================================================

import re
import json
import config
from groq import Groq


# Quick regex pre-filter to avoid unnecessary API calls
_QUESTION_PATTERNS = [
    r'\b(what do you think|your thoughts|would you say|can you explain|what about you)\b',
    r'\b(do you|have you|are you|did you|will you|could you|can you)\b',
    r'\b(what|why|how|when|where|who)\b.{3,60}\?',
    r'\?',
]


def _quick_question_check(text: str) -> bool:
    tl = text.lower()
    # Direct name mention is always relevant
    if config.YOUR_NAME.lower() in tl:
        return True
    for pat in _QUESTION_PATTERNS:
        if re.search(pat, tl):
            return True
    return False


# ----------------------------------------------------------
class AIProcessor:
    """
    Sends transcribed text to Groq (Llama 3.1 8B) and returns
    structured suggestions for the overlay.
    """

    def __init__(self):
        self.client       = Groq(api_key=config.GROQ_API_KEY)
        self.history      = []          # Rolling transcript history
        self.max_history  = 12          # Keep last ~60 seconds of context
        self.meeting_ctx  = ""
        print("[AIProcessor] ✓ Groq client ready.")

    # ----------------------------------------------------------
    def set_meeting_context(self, context: str):
        """
        Call this before the meeting with agenda, your role, key points.
        The richer this is, the better the suggestions.
        """
        self.meeting_ctx = context.strip()
        print("[AIProcessor] Meeting context set.")

    # ----------------------------------------------------------
    def process(self, transcript: str) -> dict | None:
        """
        Returns a dict with keys:
          is_question  : bool
          question     : str | None
          key_point    : str | None
          suggestion   : str | None
          urgency      : "high" | "medium" | "low"
        Returns None if the text is not worth showing.
        """
        self.history.append(transcript)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Skip API call if clearly not a question and history is short
        if len(self.history) > 2 and not _quick_question_check(transcript):
            return None

        recent = " ".join(self.history[-8:])

        prompt = f"""You are a silent, private meeting assistant helping {config.YOUR_NAME} during a live video call.

MEETING CONTEXT:
{self.meeting_ctx if self.meeting_ctx else "No context provided."}

RECENT CONVERSATION (last ~40 seconds):
{recent}

LATEST SEGMENT JUST SPOKEN:
{transcript}

Your job: analyse the latest segment and respond ONLY with a single valid JSON object.
Fields:
  "is_question": true if someone asked a question (to {config.YOUR_NAME} or the group), else false
  "question": the EXACT question asked, copied or closely paraphrased from the transcript, or null
  "answer": a direct, confident, conversational answer that {config.YOUR_NAME} can say out loud immediately (2-4 sentences). Start directly with the answer, no filler like "Great question". Use the meeting context to make it specific and accurate. null if no question.
  "key_point": the single most important fact/decision just mentioned (max 10 words), or null if a question was asked
  "urgency": "high" if directly asked to {config.YOUR_NAME}, "medium" if relevant topic, "low" otherwise

Rules:
- answer must sound natural and spoken, not written
- Be specific — use names, numbers, facts from the meeting context
- If nothing important happened, set answer and key_point to null
- Reply ONLY with the JSON, no other text"""

        try:
            response = self.client.chat.completions.create(
                model       = "llama-3.1-8b-instant",
                messages    = [{"role": "user", "content": prompt}],
                max_tokens  = 320,
                temperature = 0.2,
            )
            raw = response.choices[0].message.content.strip()

            # Strip markdown fences if model adds them
            raw = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)

            # Only return if there's something useful to show
            if data.get("answer") or data.get("key_point") or data.get("is_question"):
                return data
            return None

        except json.JSONDecodeError:
            print(f"[AIProcessor] JSON parse error on: {raw[:80]}")
            return None
        except Exception as e:
            print(f"[AIProcessor] API error: {e}")
            return None