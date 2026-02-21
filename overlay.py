# ============================================================
#  overlay.py  —  Transparent always-on-top private overlay
# ============================================================

import tkinter as tk
import threading
import queue
import ctypes
import config


# Windows API constant: excludes window from screen capture APIs
# Used by Zoom, Meet, Teams — they all call Windows Graphics Capture
WDA_EXCLUDEFROMCAPTURE = 0x00000011


class OverlayWindow:
    """
    A frameless, semi-transparent, always-on-top window that:
      - Only shows when a suggestion is available
      - Is excluded from screen sharing (Windows 10 2004+)
      - Can be dragged, hidden with Ctrl+H, closed with Ctrl+Q
    """

    def __init__(self):
        self._queue   = queue.Queue()
        self._visible = True
        self._thread  = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    # ----------------------------------------------------------
    def _run(self):
        self.root = tk.Tk()
        self._setup_window()
        self._build_ui()
        # Must call AFTER window is fully rendered, not before
        self.root.after(500, self._exclude_from_capture)
        self.root.after(100, self._poll_queue)
        self.root.mainloop()

    # ----------------------------------------------------------
    def _setup_window(self):
        root = self.root
        root.title("Meeting Assistant")
        root.overrideredirect(True)                        # No title bar / border
        root.attributes("-topmost", True)                  # Always on top
        root.attributes("-alpha", config.OVERLAY_ALPHA)    # Transparency

        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        w  = config.OVERLAY_WIDTH
        h  = config.OVERLAY_HEIGHT
        # Center of screen
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        # Start hidden — only appear when there's a suggestion
        root.withdraw()

    # ----------------------------------------------------------
    def _build_ui(self):
        BG       = "#0d1117"
        ACCENT   = "#58a6ff"
        TEXT_FG  = "#e6edf3"
        MUTED    = "#8b949e"

        # Outer container
        outer = tk.Frame(self.root, bg=BG, highlightbackground="#30363d",
                         highlightthickness=1)
        outer.pack(fill=tk.BOTH, expand=True)

        # Header row
        header = tk.Frame(outer, bg=BG)
        header.pack(fill=tk.X, padx=10, pady=(8, 2))

        tk.Label(header, text="⚡ Meeting Assistant",
                 bg=BG, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(side=tk.LEFT)

        self._status = tk.Label(header, text="",
                                bg=BG, fg=MUTED,
                                font=("Segoe UI", 8))
        self._status.pack(side=tk.RIGHT)

        # Divider
        tk.Frame(outer, bg="#21262d", height=1).pack(fill=tk.X, padx=10)

        # Main text area
        self._text = tk.Text(
            outer,
            bg=BG, fg=TEXT_FG,
            font=("Segoe UI", 12),
            wrap=tk.WORD,
            bd=0, padx=14, pady=10,
            insertwidth=0,
            height=8,
            cursor="arrow",
        )
        self._text.pack(fill=tk.BOTH, expand=True)
        self._text.config(state=tk.DISABLED)

        # Footer hint
        tk.Label(outer,
                 text="Ctrl+H hide  ·  Ctrl+Q quit  ·  drag to move",
                 bg=BG, fg="#484f58",
                 font=("Segoe UI", 7)).pack(pady=(0, 4))

        # Keyboard shortcuts
        self.root.bind("<Control-h>", self._toggle)
        self.root.bind("<Control-q>", lambda e: self.root.destroy())

        # Drag support
        outer.bind("<Button-1>",  self._drag_start)
        outer.bind("<B1-Motion>", self._drag_move)
        header.bind("<Button-1>",  self._drag_start)
        header.bind("<B1-Motion>", self._drag_move)

        # Tag colours
        self._text.tag_config("high",    foreground="#ff7b72")
        self._text.tag_config("medium",  foreground="#ffa657")
        self._text.tag_config("low",     foreground="#7ee787")
        self._text.tag_config("label",   foreground="#58a6ff", font=("Segoe UI", 11, "bold"))
        self._text.tag_config("body",    foreground="#e6edf3")

    # ----------------------------------------------------------
    def _exclude_from_capture(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0:
                hwnd = self.root.winfo_id()

            WDA_EXCLUDEFROMCAPTURE = 0x00000011
            result = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            if result:
                print("[Overlay] ✓ Screen-capture exclusion active.")
            else:
                hwnd2 = self.root.winfo_id()
                result2 = ctypes.windll.user32.SetWindowDisplayAffinity(hwnd2, WDA_EXCLUDEFROMCAPTURE)
                if result2:
                    print("[Overlay] ✓ Screen-capture exclusion active (direct HWND).")
                else:
                    print("[Overlay] ✗ Exclusion failed. Requires Windows 10 Build 19041+")
        except Exception as e:
            print(f"[Overlay] Capture exclusion error: {e}")

    # ----------------------------------------------------------
    def _drag_start(self, event):
        self._dx = event.x
        self._dy = event.y

    def _drag_move(self, event):
        x = self.root.winfo_x() + event.x - self._dx
        y = self.root.winfo_y() + event.y - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _toggle(self, event=None):
        self._visible = not self._visible
        if self._visible:
            self.root.deiconify()
        else:
            self.root.withdraw()

    # ----------------------------------------------------------
    def _poll_queue(self):
        try:
            while True:
                data = self._queue.get_nowait()
                self._render(data)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    # ----------------------------------------------------------
    def _render(self, data: dict):
        urgency   = data.get("urgency", "low")
        is_q      = data.get("is_question", False)
        question  = data.get("question")
        answer    = data.get("answer")
        key_point = data.get("key_point")

        lines = []

        if is_q and question:
            lines.append(("label", "❓ They asked:\n"))
            lines.append(("high" if urgency == "high" else "medium",
                          f"{question}\n\n"))

        if answer:
            lines.append(("label", "🗣 Your answer:\n"))
            lines.append(("body", f"{answer}\n"))
        elif key_point:
            lines.append(("label", "📌 Key point:\n"))
            lines.append((urgency, f"{key_point}\n"))

        if not lines:
            return

        self._text.config(state=tk.NORMAL)
        self._text.delete("1.0", tk.END)
        for tag, content in lines:
            self._text.insert(tk.END, content, tag)
        self._text.config(state=tk.DISABLED)

        urgency_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        self._status.config(text=urgency_icons.get(urgency, ""))

        if not self._visible:
            self._visible = True
        self.root.deiconify()
        self.root.lift()

    # ----------------------------------------------------------
    def show(self, data: dict):
        """Thread-safe method to push a suggestion to the overlay."""
        self._queue.put(data)