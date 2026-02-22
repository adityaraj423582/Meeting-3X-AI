# ============================================================
#  overlay.py  —  Professional interview overlay
# ============================================================

import tkinter as tk
import threading
import queue
import ctypes
import config

WDA_EXCLUDEFROMCAPTURE = 0x00000011

BG       = "#0a0e1a"
BG_CARD  = "#111827"
BORDER   = "#1f2937"
ACCENT   = "#6366f1"
ACCENT2  = "#818cf8"
TEXT     = "#f1f5f9"
MUTED    = "#64748b"
SUCCESS  = "#22c55e"
WARNING  = "#f59e0b"
DANGER   = "#ef4444"
MIC_ON   = "#ef4444"
MIC_OFF  = "#22c55e"

TYPE_COLORS = {
    "hr":              ("#fbbf24", "👤 HR"),
    "behavioral":      ("#a78bfa", "📖 Behavioral"),
    "technical_ml":    ("#34d399", "🤖 ML / AI"),
    "technical_dsa":   ("#60a5fa", "💻 DSA"),
    "technical_quant": ("#f472b6", "📈 Quant"),
    "research":        ("#fb923c", "🔬 Research"),
    "general":         ("#94a3b8", "💬 General"),
}

PLACEHOLDER = "Ask anything..."


class OverlayWindow:

    def __init__(self):
        self._queue        = queue.Queue()
        self._visible      = True
        self._stop_flag    = False
        self._ai_callback  = None
        self._mic_callback = None
        self._mic_active   = False
        self._thread       = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_ai_callback(self, fn):
        self._ai_callback = fn

    def set_mic_callback(self, fn):
        self._mic_callback = fn

    def _run(self):
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()
        self.root.after(500, self._exclude_from_capture)
        self.root.after(100, self._poll_queue)
        self.root.mainloop()

    def _setup_window(self):
        r = self.root
        r.title("Meeting Assistant")
        r.overrideredirect(True)
        r.attributes("-topmost", True)
        r.attributes("-alpha", config.OVERLAY_ALPHA)
        sw = r.winfo_screenwidth()
        sh = r.winfo_screenheight()
        w, h = config.OVERLAY_WIDTH, config.OVERLAY_HEIGHT
        r.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build_ui(self):
        self.root.configure(bg=BG)

        outer = tk.Frame(self.root, bg=BG, highlightbackground=ACCENT,
                         highlightthickness=1)
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        # ── Header (fixed top) ───────────────────────────────
        hdr = tk.Frame(outer, bg=ACCENT, height=36)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚡  Meeting Assistant",
                 bg=ACCENT, fg="white",
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=12)
        self._pulse_dot = tk.Label(hdr, text="●  LIVE",
                                   bg=ACCENT, fg=SUCCESS,
                                   font=("Segoe UI", 9, "bold"))
        self._pulse_dot.pack(side=tk.RIGHT, padx=12)

        # ── Bottom bar (fixed bottom) ─────────────────────────
        # Built BEFORE scroll area so it anchors to bottom
        bottom_frame = tk.Frame(outer, bg=BG)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(4, 8))

        self._mic_btn = tk.Button(
            bottom_frame, text="🎙  START LISTENING",
            bg=MIC_OFF, fg="white",
            font=("Segoe UI", 10, "bold"),
            bd=0, padx=14, pady=6,
            cursor="hand2",
            activebackground="#16a34a",
            command=self._toggle_mic)
        self._mic_btn.pack(side=tk.LEFT)

        tk.Label(bottom_frame,
                 text="Ctrl+Z start  ·  Ctrl+X stop  ·  Ctrl+H hide",
                 bg=BG, fg=MUTED,
                 font=("Segoe UI", 7)).pack(side=tk.LEFT, padx=8)

        tk.Button(bottom_frame, text="⏹  STOP",
                  bg=DANGER, fg="white",
                  font=("Segoe UI", 10, "bold"),
                  bd=0, padx=14, pady=6,
                  cursor="hand2",
                  activebackground="#dc2626",
                  command=self._stop_everything).pack(side=tk.RIGHT)

        # ── Search bar (fixed above bottom) ──────────────────
        sf = tk.Frame(outer, bg=BG)
        sf.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0, 4))

        tk.Frame(outer, bg=BORDER, height=1).pack(
            fill=tk.X, side=tk.BOTTOM, padx=10, pady=(2, 0))

        tk.Label(sf, text="🔍", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=(0, 4))

        self._entry = tk.Entry(sf,
                               bg=BG_CARD, fg=MUTED,
                               insertbackground=TEXT,
                               font=("Segoe UI", 10),
                               bd=0, relief=tk.FLAT,
                               highlightbackground=BORDER,
                               highlightthickness=1)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5)
        self._show_placeholder()
        self._entry.bind("<FocusIn>",  self._focus_in)
        self._entry.bind("<FocusOut>", self._focus_out)
        self._entry.bind("<Return>",   self._on_search)

        tk.Button(sf, text="Ask",
                  bg=ACCENT, fg="white",
                  font=("Segoe UI", 10, "bold"),
                  bd=0, padx=10, pady=4,
                  cursor="hand2",
                  activebackground=ACCENT2,
                  command=self._on_search).pack(side=tk.LEFT, padx=(6, 0))

        # ── Scrollable content area (middle) ─────────────────
        scroll_outer = tk.Frame(outer, bg=BG)
        scroll_outer.pack(fill=tk.BOTH, expand=True,
                          side=tk.TOP, padx=10, pady=(6, 2))

        # Canvas + scrollbar for scrollable content
        self._canvas = tk.Canvas(scroll_outer, bg=BG, bd=0,
                                 highlightthickness=0)
        scrollbar = tk.Scrollbar(scroll_outer, orient=tk.VERTICAL,
                                 command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Inner frame inside canvas
        self._content = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._content, anchor="nw")

        self._content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>",  self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Badge row
        badge_row = tk.Frame(self._content, bg=BG)
        badge_row.pack(fill=tk.X, pady=(0, 4))
        self._badge = tk.Label(badge_row, text="💬 General",
                               bg=BG_CARD, fg=MUTED,
                               font=("Segoe UI", 9, "bold"),
                               padx=8, pady=2)
        self._badge.pack(side=tk.LEFT)
        self._followup_label = tk.Label(badge_row, text="",
                                        bg=BG, fg=WARNING,
                                        font=("Segoe UI", 9, "italic"))
        self._followup_label.pack(side=tk.LEFT, padx=8)

        # Question card
        q_frame = tk.Frame(self._content, bg=BG_CARD,
                           highlightbackground=BORDER, highlightthickness=1)
        q_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(q_frame, text="❓  QUESTION",
                 bg=BG_CARD, fg=ACCENT2,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self._q_text = tk.Label(q_frame,
                                text="Click 🎙 or Ctrl+Z to start listening...",
                                bg=BG_CARD, fg=TEXT,
                                font=("Segoe UI", 11),
                                wraplength=560, justify=tk.LEFT)
        self._q_text.pack(anchor="w", padx=8, pady=(2, 6))

        # Hint card
        h_frame = tk.Frame(self._content, bg=BG_CARD,
                           highlightbackground=BORDER, highlightthickness=1)
        h_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(h_frame, text="💡  HINT",
                 bg=BG_CARD, fg=WARNING,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self._hint_text = tk.Label(h_frame, text="—",
                                   bg=BG_CARD, fg="#fde68a",
                                   font=("Segoe UI", 10, "italic"),
                                   wraplength=560, justify=tk.LEFT)
        self._hint_text.pack(anchor="w", padx=8, pady=(2, 6))

        # Answer card — scrollable Text widget
        a_frame = tk.Frame(self._content, bg=BG_CARD,
                           highlightbackground=BORDER, highlightthickness=1)
        a_frame.pack(fill=tk.X, pady=(0, 4))
        tk.Label(a_frame, text="🗣  WHAT TO SAY",
                 bg=BG_CARD, fg=SUCCESS,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=8, pady=(4, 0))
        self._answer_text = tk.Text(
            a_frame, bg=BG_CARD, fg=TEXT,
            font=("Segoe UI", 11), wrap=tk.WORD,
            bd=0, padx=8, pady=6,
            insertwidth=0, cursor="arrow",
            height=5)
        self._answer_text.pack(fill=tk.X, padx=0)
        self._answer_text.config(state=tk.DISABLED)

        # Confidence tip
        self._tip_label = tk.Label(self._content, text="",
                                   bg=BG, fg=MUTED,
                                   font=("Segoe UI", 9, "italic"))
        self._tip_label.pack(anchor="w", padx=4, pady=(0, 4))

        # ── Keyboard shortcuts ───────────────────────────────
        self.root.bind("<Control-z>", lambda e: self._start_listening())
        self.root.bind("<Control-x>", lambda e: self._stop_listening())
        self.root.bind("<Control-h>", self._toggle)
        self.root.bind("<Control-q>", lambda e: self._stop_everything())

        for w in (outer, hdr):
            w.bind("<Button-1>",  self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

    # ── Scroll helpers ───────────────────────────────────────
    def _on_content_configure(self, e):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._canvas_window, width=e.width)

    def _on_mousewheel(self, e):
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    # ── Placeholder ──────────────────────────────────────────
    def _show_placeholder(self):
        self._entry.delete(0, tk.END)
        self._entry.insert(0, PLACEHOLDER)
        self._entry.config(fg=MUTED)
        self._is_placeholder = True

    def _focus_in(self, e):
        if self._is_placeholder:
            self._entry.delete(0, tk.END)
            self._entry.config(fg=TEXT)
            self._is_placeholder = False

    def _focus_out(self, e):
        if not self._entry.get().strip():
            self._show_placeholder()

    def _get_search_text(self) -> str:
        if self._is_placeholder:
            return ""
        return self._entry.get().strip()

    # ── Search ───────────────────────────────────────────────
    def _on_search(self, e=None):
        q = self._get_search_text()
        if not q:
            return
        self._set_answer("⏳ Getting answer...")
        self._q_text.config(text=q)
        self.root.deiconify()
        self.root.lift()
        self._show_placeholder()

        def _ask():
            if self._ai_callback:
                result = self._ai_callback(q)
                self._queue.put(result if result else {
                    "is_question": True,
                    "question": q,
                    "hint": "",
                    "answer": "Could not get answer. Try rephrasing.",
                    "question_type": "general",
                })
        threading.Thread(target=_ask, daemon=True).start()

    # ── Mic controls ─────────────────────────────────────────
    def _start_listening(self):
        if not self._mic_active:
            self._toggle_mic()

    def _stop_listening(self):
        if self._mic_active:
            self._toggle_mic()

    def _toggle_mic(self):
        self._mic_active = not self._mic_active
        if self._mic_active:
            self._mic_btn.config(text="🔴  LISTENING...",
                                 bg=MIC_ON, activebackground="#b91c1c")
            self._pulse_dot.config(text="● LISTENING", fg=DANGER)
            self._q_text.config(text="🎙 Listening...")
            self._hint_text.config(text="—")
            self._set_answer("")
            self._tip_label.config(text="")
        else:
            self._mic_btn.config(text="🎙  START LISTENING",
                                 bg=MIC_OFF, activebackground="#16a34a")
            self._pulse_dot.config(text="●  LIVE", fg=SUCCESS)
        if self._mic_callback:
            self._mic_callback(self._mic_active)

    def mic_is_active(self) -> bool:
        return self._mic_active

    def reset_mic(self):
        self._mic_active = False
        self._mic_btn.config(text="🎙  START LISTENING",
                             bg=MIC_OFF, activebackground="#16a34a")
        self._pulse_dot.config(text="● ANSWER READY", fg=DANGER)
        self.root.after(3000, lambda: self._pulse_dot.config(
            text="●  LIVE", fg=SUCCESS))

    # ── Stop all ─────────────────────────────────────────────
    def _stop_everything(self):
        print("\n[Overlay] Stopping assistant...")
        self._stop_flag = True
        try:
            self.root.destroy()
        except:
            pass
        import os, signal
        os.kill(os.getpid(), signal.SIGINT)

    @property
    def stopped(self):
        return self._stop_flag

    def _exclude_from_capture(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()
            r = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if not r:
                ctypes.windll.user32.SetWindowDisplayAffinity(
                    self.root.winfo_id(), WDA_EXCLUDEFROMCAPTURE)
            print("[Overlay] ✓ Screen-capture exclusion active.")
        except Exception as e:
            print(f"[Overlay] Capture exclusion error: {e}")

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _toggle(self, e=None):
        self._visible = not self._visible
        self.root.deiconify() if self._visible else self.root.withdraw()

    def _poll_queue(self):
        try:
            while True:
                self._render(self._queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def _set_answer(self, text: str):
        self._answer_text.config(state=tk.NORMAL)
        self._answer_text.delete("1.0", tk.END)
        self._answer_text.insert(tk.END, text)
        self._answer_text.config(state=tk.DISABLED)

    def _render(self, data: dict):
        if not data:
            return
        q_type      = data.get("question_type", "general")
        question    = data.get("question", "")
        hint        = data.get("hint", "")
        answer      = data.get("answer", "")
        tip         = data.get("confidence_tip", "")
        is_followup = data.get("is_followup", False)

        color, label = TYPE_COLORS.get(q_type, ("#94a3b8", "💬 General"))
        self._badge.config(text=label, fg=color)
        self._followup_label.config(text="↩ Follow-up" if is_followup else "")
        self._q_text.config(text=question or "—")
        self._hint_text.config(text=hint or "—")
        self._set_answer(answer or "—")
        self._tip_label.config(text=f"✨  {tip}" if tip else "")

        # Scroll back to top when new answer arrives
        self._canvas.yview_moveto(0)

        self.reset_mic()
        self.root.deiconify()
        self.root.lift()

    def show(self, data: dict):
        self._queue.put(data)