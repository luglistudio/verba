# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml",
#     "customtkinter",
# ]
# ///

"""Vocabolario e Detti Navigabili — entry point."""

import os
import queue
import tkinter as tk
import customtkinter as ctk

from constants import BASE_DIR, WIKI_DIR, debug_log
from db import WordDatabase
from item_tab import ItemTab
from tutor_tab import TutorTab
from spaced_tab import SpacedTab
from settings_tab import SettingsTab

# Impostazioni di stile globale CustomTkinter
ctk.set_appearance_mode("system")  # Segue il tema del sistema operativo
ctk.set_default_color_theme("blue")  # Tema base blu coordinato macOS


class VocabolarioApp(ctk.CTk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title("Verba — Vocabolario & Detti")
        self.geometry("1150x850")
        self.minsize(1000, 750)

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
        selected = self.notebook.get()
        if selected == "Parole":
            self.words_tab.new_item()
        elif selected == "Detti e Proverbi":
            self.sayings_tab.new_item()

    def _handle_cmd_s(self, event=None):
        selected = self.notebook.get()
        if selected == "Parole":
            self.words_tab.save_current()
        elif selected == "Detti e Proverbi":
            self.sayings_tab.save_current()

    # ── UI setup ───────────────────────────────────────────────────

    def _setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Tabview moderno di CustomTkinter
        self.notebook = ctk.CTkTabview(main_frame, command=self._on_tab_changed)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.notebook.add("Parole")
        self.notebook.add("Detti e Proverbi")
        self.notebook.add("Tutor AI (NotebookLM)")
        self.notebook.add("Spaced Repetition (Ripasso)")
        self.notebook.add("Impostazioni")

        # Inizializza i componenti grafici all'interno dei relativi tab
        self.words_tab = ItemTab(self.notebook.tab("Parole"), self.db, item_type="word")
        self.sayings_tab = ItemTab(self.notebook.tab("Detti e Proverbi"), self.db, item_type="detto")
        self.tutor_tab = TutorTab(self.notebook.tab("Tutor AI (NotebookLM)"), self.db, self._enqueue_ui)
        self.spaced_tab = SpacedTab(self.notebook.tab("Spaced Repetition (Ripasso)"), self.db)
        self.settings_tab = SettingsTab(self.notebook.tab("Impostazioni"), self.db, self.update_font_sizes)

        # Applica i font iniziali impostati
        self.update_font_sizes()

    def update_font_sizes(self):
        self.words_tab.update_fonts()
        self.sayings_tab.update_fonts()
        self.tutor_tab.update_fonts()
        self.spaced_tab.update_fonts()
        self.settings_tab.update_fonts()

    def _on_tab_changed(self):
        try:
            selected = self.notebook.get()
            if selected == "Spaced Repetition (Ripasso)":
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
