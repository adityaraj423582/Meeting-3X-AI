# Meeting Assistant — Setup Guide

A private, real-time AI meeting assistant for Google Meet, Zoom, and Teams.
Runs on your ROG laptop using Whisper (GPU) + Groq AI.
The overlay window is **invisible during screen sharing**.

---

## Step 1 — Install Virtual Audio Driver

1. Download **VB-Audio Virtual Cable** → https://vb-audio.com/Cable/
2. Run `VBCABLE_Setup_x64.exe` as Administrator → Install → **Restart PC**
3. (Optional but recommended) Download **VoiceMeeter Banana** from the same site
   - Lets you hear the meeting AND capture it simultaneously

---

## Step 2 — Configure Windows Audio

**Simple setup (you'll hear audio through VoiceMeeter):**
```
Right-click speaker icon → Sound Settings
  Playback → Set "VoiceMeeter Input" or "CABLE Input" as default
  
In VoiceMeeter Banana:
  Hardware Out A1 → your real headphones/speakers
```

**Or test quickly with just VB-Cable:**
```
Set meeting app output → "CABLE Input"
You can still hear via your mic/headphones on your phone to test
```

---

## Step 3 — Python Environment

Open terminal in PyCharm and run:

```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install PyTorch with CUDA (for RTX 3050)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install all other dependencies
pip install -r requirements.txt
```

**Verify GPU is working:**
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# Should print: True  NVIDIA GeForce RTX 3050 Laptop GPU
```

---

## Step 4 — Get Free Groq API Key

1. Go to https://console.groq.com
2. Sign up (free, no credit card)
3. Create API Key
4. Paste it into `config.py` → `GROQ_API_KEY`

---

## Step 5 — Find Your Audio Device Name

```bash
python utils/list_audio_devices.py
```

Copy the exact device name and paste it into `config.py` → `VIRTUAL_AUDIO_DEVICE`

---

## Step 6 — Configure for Your Meeting

Edit `main.py` → update the `MEETING_CONTEXT` block at the top with:
- Meeting type and your role
- Topics you're prepared on
- Likely questions and your answers
- Names of people in the meeting

The more detail here, the better the suggestions.

---

## Step 7 — Test Before Your Meeting

**Test the overlay alone (no audio needed):**
```bash
python utils/test_overlay.py
```

**Test with a YouTube video playing:**
- Route YouTube audio through your virtual cable
- Run `main.py` and check transcription appears in terminal

**Test with a self-call:**
- Open Google Meet on your phone
- Join the same link on your laptop
- Speak on the phone, see suggestions on laptop

---

## Step 8 — Run During a Meeting

```bash
python main.py
```

The overlay appears in the bottom-right corner when suggestions are ready.

| Shortcut | Action |
|----------|--------|
| `Ctrl+H` | Hide / show overlay |
| `Ctrl+Q` | Close overlay |
| Drag header | Move overlay anywhere |

---

## Indicator colours

| Colour | Meaning |
|--------|---------|
| 🔴 Red | Direct question to you — respond now |
| 🟡 Yellow | Relevant topic — good to comment |
| 🟢 Green | Background info / key point noted |

---

## Troubleshooting

**"Virtual audio device not found"**
→ Run `python utils/list_audio_devices.py` and check the exact name

**No transcription appearing**
→ Verify audio is routing: play audio on your PC and check VoiceMeeter/CABLE shows signal

**Slow suggestions (>5 seconds)**
→ Check CUDA is active: `python -c "import torch; print(torch.cuda.is_available())"`
→ Enable Performance mode in Armoury Crate (Fn+F5)
→ Force Python to use RTX 3050: NVIDIA Control Panel → Program Settings → python.exe → High-performance GPU

**Overlay visible in screen share**
→ Requires Windows 10 version 2004 (Build 19041) or later
→ Check: Settings → System → About → OS Build

---

## Project Structure

```
meeting_assistant/
├── main.py                  ← Run this
├── config.py                ← Your settings and API key
├── audio_capture.py         ← Reads virtual audio device
├── transcriber.py           ← Whisper on GPU
├── ai_processor.py          ← Groq AI analysis
├── overlay.py               ← Transparent window
├── requirements.txt
└── utils/
    ├── list_audio_devices.py  ← Find your device name
    └── test_overlay.py        ← Preview the overlay
```
