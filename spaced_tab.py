"""Tab Spaced Repetition — sessioni di ripasso con algoritmo SM-2."""

from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

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
        self.spaced_container = ttk.Frame(self.parent_frame, padding="15")
        self.spaced_container.pack(fill=tk.BOTH, expand=True)

        # 1. Start Frame
        self.spaced_start_frame = ttk.Frame(self.spaced_container)

        self.lbl_spaced_title = ttk.Label(self.spaced_start_frame, text="Spaced Repetition (SM-2)", font=("System", 18, "bold"))
        self.lbl_spaced_title.pack(pady=(0, 20))

        self.lbl_spaced_summary = ttk.Label(self.spaced_start_frame, text="Calcolo elementi in corso...", font=("System", 14))
        self.lbl_spaced_summary.pack(pady=(0, 20))

        self.btn_start_spaced = ttk.Button(self.spaced_start_frame, text="Inizia Ripasso", command=self.start_session)
        self.btn_start_spaced.pack(pady=10)

        # 2. Session Frame
        self.spaced_session_frame = ttk.Frame(self.spaced_container)

        self.spaced_nav_frame = ttk.Frame(self.spaced_session_frame)
        self.spaced_nav_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.btn_exit_spaced = ttk.Button(self.spaced_nav_frame, text="Termina Sessione ❌", command=self.exit_session)
        self.btn_exit_spaced.pack(side=tk.RIGHT)

        self.lbl_spaced_progress = ttk.Label(self.spaced_session_frame, text="Elemento 0 di 0", font=("System", 12, "italic"))
        self.lbl_spaced_progress.pack(anchor=tk.W, pady=(0, 5))

        # Card Front
        self.card_front_frame = ttk.LabelFrame(self.spaced_session_frame, text="Fronte della Carta", padding="15")
        self.card_front_frame.pack(fill=tk.X, pady=5)

        f_card_title = ttk.Frame(self.card_front_frame)
        f_card_title.pack(pady=10)

        self.lbl_card_word = ttk.Label(f_card_title, text="Parola", font=("System", 22, "bold"))
        self.lbl_card_word.pack(side=tk.LEFT)

        self.btn_card_speak = ttk.Button(f_card_title, text="🔊", width=3, command=self._speak_card_word)
        self.btn_card_speak.pack(side=tk.LEFT, padx=10)

        self.lbl_card_type = ttk.Label(self.card_front_frame, text="Tipo: parola", font=("System", 11, "italic"))
        self.lbl_card_type.pack()

        self.btn_show_answer = ttk.Button(self.card_front_frame, text="Mostra Significato", command=self._show_answer)
        self.btn_show_answer.pack(pady=10)

        # Card Back
        self.card_back_frame = ttk.LabelFrame(self.spaced_session_frame, text="Significato ed Etimologia", padding="15")

        self.txt_card_back = tk.Text(self.card_back_frame, wrap=tk.WORD, font=("System", 13), height=6, state=tk.DISABLED)
        self.txt_card_back.pack(fill=tk.BOTH, expand=True, pady=5)

        # Evaluation Frame (Likert)
        self.spaced_eval_frame = ttk.Frame(self.spaced_session_frame)

        self.lbl_eval_title = ttk.Label(self.spaced_eval_frame, text="Come hai ricordato questo termine? (Scala Likert)", font=("System", 12, "bold"))
        self.lbl_eval_title.pack(anchor=tk.W, pady=(0, 5))

        self.eval_buttons_frame = ttk.Frame(self.spaced_eval_frame)
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

        colors = [
            "#ffdddd",  # 0: Buio (Rosso)
            "#ffe6cc",  # 1: Quasi (Arancione)
            "#fffae6",  # 2: Errato (Giallo)
            "#e6f9ff",  # 3: Fatica (Azzurro)
            "#eafaf1",  # 4: Bene (Verde chiaro)
            "#d5f5e3"   # 5: Ottimo (Verde brillante)
        ]

        self.spaced_eval_buttons = []
        for i, (grade, desc) in enumerate(eval_grades):
            btn = tk.Button(
                self.eval_buttons_frame,
                text=f"{grade}\n{desc}",
                font=("System", 10, "bold"),
                padx=5,
                pady=5,
                bg=colors[i],
                fg="#212529",
                highlightbackground=colors[i],
                command=lambda g=i: self._submit_grade(g)
            )
            btn.grid(row=0, column=i, sticky="nsew", padx=2, pady=2)
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
            self.lbl_spaced_summary.config(text="Ottimo lavoro! Non ci sono elementi da ripassare per oggi. 🎉")
            self.btn_start_spaced.config(state=tk.DISABLED)
        else:
            self.lbl_spaced_summary.config(text=f"Elementi da ripassare oggi: {n_due}")
            self.btn_start_spaced.config(state=tk.NORMAL)

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
        self.lbl_spaced_progress.config(text=f"Elemento {self.current_due_idx + 1} di {len(self.due_items)}")

        prefix = "Parola" if item_type == "word" else "Detto"
        self.lbl_card_word.config(text=name)
        self.lbl_card_type.config(text=f"Tipo: {prefix}")

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

        self.txt_card_back.config(state=tk.NORMAL)
        self.txt_card_back.delete(1.0, tk.END)
        self.txt_card_back.insert(tk.END, back_text)
        self.txt_card_back.config(state=tk.DISABLED)

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
