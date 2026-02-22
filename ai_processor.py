# ============================================================
#  ai_processor.py  —  Interview AI with smart length + follow-up
# ============================================================

import re
import json
import config
from groq import Groq


class AIProcessor:

    def __init__(self):
        self.client        = Groq(api_key=config.GROQ_API_KEY)
        self.history       = []
        self.max_history   = 12
        self.meeting_ctx   = ""
        self.last_question = ""
        self.last_answer   = ""
        print("[AIProcessor] ✓ Groq client ready.")

    def set_meeting_context(self, context: str):
        self.meeting_ctx = context.strip()
        print("[AIProcessor] Meeting context set.")

    def _build_prompt(self, text: str, recent: str, manual: bool = False) -> str:
        return f"""You are a private real-time interview assistant for {config.YOUR_NAME}.

CANDIDATE PROFILE (use ONLY for HR/behavioral/research questions):
{self.meeting_ctx if self.meeting_ctx else "No context provided."}

RECENT CONVERSATION:
{recent}

LAST QUESTION ANSWERED: {self.last_question if self.last_question else "None"}
LAST ANSWER GIVEN: {self.last_answer[:100] if self.last_answer else "None"}

LATEST TEXT:
{text}

STEP 1 — Detect question type:
A) NEW question → answer it fresh
B) FOLLOW-UP → interviewer wants more detail on last question ("elaborate", "tell me more", "can you expand", "give example")
C) NOT A QUESTION → return {{"is_question": false}}

STEP 2 — Classify:
- "hr": about himself, introduce yourself, strengths, weaknesses → USE profile
- "behavioral": past situations, STAR format → USE profile
- "technical_ml": ML, DL concepts → general knowledge only
- "technical_dsa": DSA, algorithms → general knowledge only
- "technical_quant": probability, stats, HFT → general knowledge only
- "research": forest fire, MODIS, XGBoost → USE profile
- "general": other topics

STEP 3 — Determine answer length:
- "short": yes/no, simple fact, one concept → 1-2 sentences
- "medium": explain concept, describe experience → 3-4 sentences
- "long": system design, detailed project, STAR format → 5-6 sentences

STEP 4 — Respond with JSON:
{{
  "is_question": true,
  "is_followup": true/false,
  "question_type": one of above,
  "answer_length": "short"/"medium"/"long",
  "question": exact question or follow-up request,
  "hint": key insight in 1 sentence,
  "answer": natural spoken answer matching the length above. For technical use general knowledge. For HR/behavioral use real profile.,
  "confidence_tip": one short delivery tip
}}

Reply ONLY with valid JSON."""

    def process(self, transcript: str) -> dict | None:
        self.history.append(transcript)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        recent = " ".join(self.history[-8:])

        try:
            response = self.client.chat.completions.create(
                model = "llama-3.1-8b-instant",
                messages    = [{"role": "user", "content": self._build_prompt(transcript, recent)}],
                max_tokens  = 500,
                temperature = 0.2,
            )
            raw  = response.choices[0].message.content.strip()
            raw  = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)

            if not data.get("is_question") or not data.get("answer"):
                return None

            # Avoid duplicate questions
            q = data.get("question", "").strip()
            self.last_question = q
            self.last_answer = data.get("answer", "")
            return data

        except json.JSONDecodeError:
            print(f"[AIProcessor] JSON parse error: {raw[:80]}")
            return None
        except Exception as e:
            print(f"[AIProcessor] API error: {e}")
            return None

    def ask(self, question: str) -> dict | None:
        recent = " ".join(self.history[-8:]) if self.history else "No conversation yet."
        try:
            response = self.client.chat.completions.create(
                model = "llama-3.1-8b-instant",
                messages    = [{"role": "user", "content": self._build_prompt(question, recent, manual=True)}],
                max_tokens  = 500,
                temperature = 0.3,
            )
            raw  = response.choices[0].message.content.strip()
            raw  = re.sub(r"^```json|^```|```$", "", raw, flags=re.MULTILINE).strip()
            data = json.loads(raw)
            if not data.get("answer"):
                data["answer"]      = "Could not generate answer. Try rephrasing."
                data["is_question"] = True
                data["question"]    = question
            return data
        except Exception as e:
            print(f"[AIProcessor] Manual ask error: {e}")
            return None