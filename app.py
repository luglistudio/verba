# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
# ]
# ///

"""Vocabolario e Detti Navigabili — entry point."""

import os
import queue
import tkinter as tk
from tkinter import ttk

from constants import BASE_DIR, WIKI_DIR, debug_log
from db import WordDatabase
from item_tab import ItemTab
from tutor_tab import TutorTab
from spaced_tab import SpacedTab


class VocabolarioApp(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("Vocabolario e Detti Navigabili")
        self.geometry("1100x800")

        style = ttk.Style(self)
        if 'aqua' in style.theme_names():
            style.theme_use('aqua')
        else:
            style.theme_use('clam')

        style.configure('TButton', padding=(10, 8), font=("System", 13))

        self.bind('<Command-n>', self._handle_cmd_n)
        self.bind('<Command-s>', self._handle_cmd_s)

        try:
            icon = tk.PhotoImage(file=os.path.join(BASE_DIR, "icon.png"))
            self.iconphoto(True, icon)
        except Exception:
            pass

        self._ui_queue = queue.Queue()

        self._setup_ui()
        self.words_tab.refresh()
        self.sayings_tab.refresh()
        self._poll_ui_queue()

        # Rileva notebook esistente all'avvio
        self.tutor_tab.detect_existing_notebook_async()

    # ── Keyboard shortcuts ─────────────────────────────────────────

    def _handle_cmd_n(self, event=None):
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self.words_tab.new_item()
        elif idx == 1:
            self.sayings_tab.new_item()

    def _handle_cmd_s(self, event=None):
        idx = self.notebook.index(self.notebook.select())
        if idx == 0:
            self.words_tab.save_current()
        elif idx == 1:
            self.sayings_tab.save_current()

    # ── UI setup ───────────────────────────────────────────────────

    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 0: Parole
        tab_words = ttk.Frame(self.notebook)
        self.notebook.add(tab_words, text="Parole")
        self.words_tab = ItemTab(tab_words, self.db, item_type="word")

        # Tab 1: Detti
        tab_sayings = ttk.Frame(self.notebook)
        self.notebook.add(tab_sayings, text="Detti e Proverbi")
        self.sayings_tab = ItemTab(tab_sayings, self.db, item_type="detto")

        # Tab 2: Tutor AI
        tab_tutor = ttk.Frame(self.notebook)
        self.notebook.add(tab_tutor, text="Tutor AI (NotebookLM)")
        self.tutor_tab = TutorTab(tab_tutor, self.db, self._enqueue_ui)

        # Tab 3: Spaced Repetition
        tab_spaced = ttk.Frame(self.notebook)
        self.notebook.add(tab_spaced, text="Spaced Repetition (Ripasso)")
        self.spaced_tab = SpacedTab(tab_spaced, self.db)

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event):
        try:
            selected_tab = self.notebook.index(self.notebook.select())
            if selected_tab == 3:  # Spaced Repetition
                self.spaced_tab.show_start_screen()
        except Exception:
            pass

    # ── Thread-safe UI queue ───────────────────────────────────────

    def _enqueue_ui(self, callback, *args):
        """Thread-safe: accoda un callback da eseguire sul main thread."""
        if args:
            self._ui_queue.put(lambda: callback(*args))
        else:
            self._ui_queue.put(callback)

    def _poll_ui_queue(self):
        """Polling periodico della coda UI sul main thread."""
        try:
            while True:
                cb = self._ui_queue.get_nowait()
                try:
                    cb()
                except Exception as e:
                    debug_log(f"UI callback error: {e}")
        except queue.Empty:
            pass
        self.after(100, self._poll_ui_queue)


if __name__ == "__main__":
    db = WordDatabase(WIKI_DIR)
    app = VocabolarioApp(db)
    app.lift()
    app.attributes('-topmost', True)
    app.after_idle(app.attributes, '-topmost', False)
    app.mainloop()
