"""Tab Spaced Repetition — sessioni di ripasso con algoritmo SM-2 usando CustomTkinter."""

from datetime import datetime
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from tts import TTS


class SpacedTab:
    """Gestisce il tab Spaced Repetition: card front/back, valutazione Likert."""

    def __init__(self, parent_frame, db):
        self.parent_frame = parent_frame
        self.db = db

        self.due_items = []
        self.current_due_idx = 0

        self._setup_layout()

    # ── Layout ─────────────────────────────────────────────────────

    def _setup_layout(self):
        self.spaced_container = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        self.spaced_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # 1. Start Frame
        self.spaced_start_frame = ctk.CTkFrame(self.spaced_container, fg_color="transparent")

        self.lbl_spaced_title = ctk.CTkLabel(self.spaced_start_frame, text="Spaced Repetition (SM-2)", font=ctk.CTkFont(family="Helvetica", size=20, weight="bold"))
        self.lbl_spaced_title.pack(pady=(20, 10))

        self.lbl_spaced_summary = ctk.CTkLabel(self.spaced_start_frame, text="Calcolo elementi in corso...", font=ctk.CTkFont(family="Helvetica", size=14))
        self.lbl_spaced_summary.pack(pady=(0, 20))

        self.btn_start_spaced = ctk.CTkButton(self.spaced_start_frame, text="Inizia Ripasso", command=self.start_session)
        self.btn_start_spaced.pack(pady=10)

        # 2. Session Frame
        self.spaced_session_frame = ctk.CTkFrame(self.spaced_container, fg_color="transparent")

        self.spaced_nav_frame = ctk.CTkFrame(self.spaced_session_frame, fg_color="transparent")
        self.spaced_nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(15, 0))

        self.btn_exit_spaced = ctk.CTkButton(self.spaced_nav_frame, text="Termina Sessione ❌", fg_color="#ff3b30", hover_color="#dc3545", text_color="#ffffff", command=self.exit_session)
        self.btn_exit_spaced.pack(side=tk.RIGHT)

        self.lbl_spaced_progress = ctk.CTkLabel(self.spaced_session_frame, text="Elemento 0 di 0", font=ctk.CTkFont(family="Helvetica", size=12, slant="italic"))
        self.lbl_spaced_progress.pack(anchor=tk.W, pady=(0, 5))

        # Card Front
        self.card_front_frame = ctk.CTkFrame(self.spaced_session_frame)
        self.card_front_frame.pack(fill=tk.X, pady=10, ipady=15)

        lbl_front_hdr = ctk.CTkLabel(self.card_front_frame, text="Fronte della Carta", font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"), text_color="#8e8e93")
        lbl_front_hdr.pack(anchor=tk.W, padx=15, pady=(10, 5))

        f_card_title = ctk.CTkFrame(self.card_front_frame, fg_color="transparent")
        f_card_title.pack(pady=10)

        self.lbl_card_word = ctk.CTkLabel(f_card_title, text="Parola", font=ctk.CTkFont(family="Helvetica", size=24, weight="bold"))
        self.lbl_card_word.pack(side=tk.LEFT)

        self.btn_card_speak = ctk.CTkButton(f_card_title, text="🔊", width=36, height=36, font=ctk.CTkFont(family="Helvetica", size=14), command=self._speak_card_word)
        self.btn_card_speak.pack(side=tk.LEFT, padx=15)

        self.lbl_card_type = ctk.CTkLabel(self.card_front_frame, text="Tipo: parola", font=ctk.CTkFont(family="Helvetica", size=11, slant="italic"))
        self.lbl_card_type.pack(pady=(0, 10))

        self.btn_show_answer = ctk.CTkButton(self.card_front_frame, text="Mostra Significato", command=self._show_answer)
        self.btn_show_answer.pack(pady=10)

        # Card Back (inizialmente nascosta)
        self.card_back_frame = ctk.CTkFrame(self.spaced_session_frame)

        lbl_back_hdr = ctk.CTkLabel(self.card_back_frame, text="Significato ed Etimologia", font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"), text_color="#8e8e93")
        lbl_back_hdr.pack(anchor=tk.W, padx=15, pady=(10, 5))

        self.txt_card_back = ctk.CTkTextbox(self.card_back_frame, wrap=tk.WORD, font=("Helvetica", 13), height=140)
        self.txt_card_back.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # Evaluation Frame (Likert) (inizialmente nascosto)
        self.spaced_eval_frame = ctk.CTkFrame(self.spaced_session_frame, fg_color="transparent")

        self.lbl_eval_title = ctk.CTkLabel(self.spaced_eval_frame, text="Come hai ricordato questo termine? (Scala Likert)", font=ctk.CTkFont(family="Helvetica", size=13, weight="bold"))
        self.lbl_eval_title.pack(anchor=tk.W, pady=(0, 10))

        self.eval_buttons_frame = ctk.CTkFrame(self.spaced_eval_frame, fg_color="transparent")
        self.eval_buttons_frame.pack(fill=tk.X)

        for col_idx in range(6):
            self.eval_buttons_frame.columnconfigure(col_idx, weight=1)

        eval_grades = [
            ("0", "Buio"),
            ("1", "Quasi"),
            ("2", "Errato"),
            ("3", "Fatica"),
            ("4", "Bene"),
            ("5", "Ottimo")
        ]

        # Colori coordinati ed eleganti per i bottoni di valutazione
        colors = [
            ("#ff3b30", "#dc3545", "#ffffff"),  # 0: Buio (Rosso)
            ("#ff9500", "#f57c00", "#ffffff"),  # 1: Quasi (Arancione)
            ("#ffcc00", "#fbc02d", "#000000"),  # 2: Errato (Giallo)
            ("#5ac8fa", "#0097a7", "#000000"),  # 3: Fatica (Azzurro)
            ("#34c759", "#388e3c", "#ffffff"),  # 4: Bene (Verde chiaro)
            ("#248a3d", "#1b652c", "#ffffff")   # 5: Ottimo (Verde brillante)
        ]

        self.spaced_eval_buttons = []
        for i, (grade, desc) in enumerate(eval_grades):
            bg, hover, fg = colors[i]
            btn = ctk.CTkButton(
                self.eval_buttons_frame,
                text=f"{grade}\n{desc}",
                font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"),
                fg_color=bg,
                hover_color=hover,
                text_color=fg,
                height=50,
                command=lambda g=i: self._submit_grade(g)
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=3, pady=2)
            self.spaced_eval_buttons.append(btn)

        self.show_start_screen()

    # ── Due items ──────────────────────────────────────────────────

    def _get_due_items(self):
        due = []
        today_str = datetime.now().strftime("%Y-%m-%d")

        for word, info in self.db.words.items():
            next_rev = info['metadata'].get('next_review', '')
            if not next_rev or next_rev <= today_str:
                due.append((word, "word", info))

        for saying, info in self.db.sayings.items():
            next_rev = info['metadata'].get('next_review', '')
            if not next_rev or next_rev <= today_str:
                due.append((saying, "detto", info))

        def sort_key(item):
            nr = item[2]['metadata'].get('next_review', '')
            return nr if nr else '0000-00-00'

        due.sort(key=sort_key)
        return due

    # ── Screen navigation ──────────────────────────────────────────

    def show_start_screen(self):
        self.spaced_session_frame.pack_forget()
        self.spaced_start_frame.pack(fill=tk.BOTH, expand=True)

        self.due_items = self._get_due_items()
        n_due = len(self.due_items)

        if n_due == 0:
            self.lbl_spaced_summary.configure(text="Ottimo lavoro! Non ci sono elementi da ripassare per oggi. 🎉")
            self.btn_start_spaced.configure(state=tk.DISABLED)
        else:
            self.lbl_spaced_summary.configure(text=f"Elementi da ripassare oggi: {n_due}")
            self.btn_start_spaced.configure(state=tk.NORMAL)

    def start_session(self):
        self.due_items = self._get_due_items()
        if not self.due_items:
            self.show_start_screen()
            return

        self.current_due_idx = 0
        self.spaced_start_frame.pack_forget()
        self.spaced_session_frame.pack(fill=tk.BOTH, expand=True)
        self._show_item()

    def _show_item(self):
        if self.current_due_idx >= len(self.due_items):
            messagebox.showinfo("Sessione Completata", "Hai completato tutti i ripassi previsti per oggi! Ottimo lavoro. 🎉")
            self.show_start_screen()
            return

        name, item_type, info = self.due_items[self.current_due_idx]
        self.lbl_spaced_progress.configure(text=f"Elemento {self.current_due_idx + 1} di {len(self.due_items)}")

        prefix = "Parola" if item_type == "word" else "Detto"
        self.lbl_card_word.configure(text=name)
        self.lbl_card_type.configure(text=f"Tipo: {prefix}")

        self.card_back_frame.pack_forget()
        self.spaced_eval_frame.pack_forget()
        self.btn_show_answer.pack(pady=10)

    def _show_answer(self):
        name, item_type, info = self.due_items[self.current_due_idx]
        self.btn_show_answer.pack_forget()

        back_text = f"📖 SIGNIFICATO:\n{info['definition']}\n"
        if info.get('etymology'):
            ety_lbl = "🏛️ ETIMOLOGIA:" if item_type == "word" else "🏛️ ORIGINE:"
            back_text += f"\n{ety_lbl}\n{info['etymology']}\n"
        if info.get('synonyms'):
            links_lbl = "🔗 SINONIMI:" if item_type == "word" else "🔗 DETTI SIMILI:"
            back_text += f"\n{links_lbl} {', '.join(info['synonyms'])}\n"

        self.txt_card_back.configure(state=tk.NORMAL)
        self.txt_card_back.delete("1.0", tk.END)
        self.txt_card_back.insert(tk.END, back_text)
        self.txt_card_back.configure(state=tk.DISABLED)

        self.card_back_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        self.spaced_eval_frame.pack(fill=tk.X, pady=5)

    def _submit_grade(self, grade):
        name, item_type, info = self.due_items[self.current_due_idx]
        self.db.update_spaced_repetition(name, item_type, grade)
        self.current_due_idx += 1
        self._show_item()

    def exit_session(self):
        if messagebox.askyesno("Termina Sessione", "Sei sicuro di voler interrompere la sessione di ripasso corrente?"):
            self.show_start_screen()

    def _speak_card_word(self):
        if self.due_items and self.current_due_idx < len(self.due_items):
            name, item_type, info = self.due_items[self.current_due_idx]
            pron = info['metadata'].get('pronuncia', '').strip()
            TTS.speak(pron if pron else name)

    def update_fonts(self):
        f_gen = self.db.settings.get("font_size_general", 13)
        f_mean = self.db.settings.get("font_size_meaning", 18)

        font_gen = ctk.CTkFont(family="Helvetica", size=f_gen)
        font_bold = ctk.CTkFont(family="Helvetica", size=f_gen + 1, weight="bold")
        font_mean = ctk.CTkFont(family="Helvetica", size=f_mean)

        self._apply_fonts_recursive(self.parent_frame, font_gen, font_bold, font_mean)

    def _apply_fonts_recursive(self, widget, font_gen, font_bold, font_mean):
        try:
            w_class = widget.__class__.__name__
            if w_class == "CTkLabel":
                if getattr(self, "lbl_card_word", None) and str(widget) == str(self.lbl_card_word):
                    widget.configure(font=ctk.CTkFont(family="Helvetica", size=font_gen.cget("size") + 11, weight="bold"))
                else:
                    widget.configure(font=font_gen)
            elif w_class == "CTkButton":
                widget.configure(font=font_gen)
            elif w_class == "CTkEntry":
                widget.configure(font=font_gen)
            elif w_class == "CTkTextbox":
                widget.configure(font=font_mean)
        except Exception:
            pass

        for child in widget.winfo_children():
            self._apply_fonts_recursive(child, font_gen, font_bold, font_mean)

