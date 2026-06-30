"""Tab condiviso per Parole e Detti — UI + logica CRUD."""

import os
import re
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from constants import BASE_DIR, debug_log
from tts import TTS


class ItemTab:
    """Gestisce un tab (Parole o Detti) con lista, links navigabili e editor."""

    def __init__(self, parent_frame, db, item_type="word"):
        self.parent_frame = parent_frame
        self.db = db
        self.item_type = item_type  # "word" o "detto"
        self.current_item = None
        self.ui = {}

        self._setup_layout()

    # ── Configurazione ─────────────────────────────────────────────

    def _setup_layout(self):
        is_word = self.item_type == "word"

        paned = ttk.PanedWindow(self.parent_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=10)

        # Colonna 1: Lista completa
        f_list = ttk.Frame(paned)
        paned.add(f_list, weight=2)
        title_list = "Tutte le Parole" if is_word else "Tutti i Detti"
        ttk.Label(f_list, text=title_list, font=("System", 14, "bold")).pack(anchor=tk.W, pady=(0, 5))
        s_list = ttk.Scrollbar(f_list)
        s_list.pack(side=tk.RIGHT, fill=tk.Y)
        l_list = tk.Listbox(f_list, yscrollcommand=s_list.set, exportselection=False, font=("System", 13))
        l_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        s_list.config(command=l_list.yview)
        l_list.bind('<<ListboxSelect>>', self._on_select)

        # Colonna 2: Links (Sinonimi / Detti Simili)
        f_links = ttk.Frame(paned)
        paned.add(f_links, weight=2)
        title_links = "Sinonimi (Navigabili)" if is_word else "Detti Simili (Navigabili)"
        ttk.Label(f_links, text=title_links, font=("System", 14, "bold")).pack(anchor=tk.W, pady=(0, 5), padx=10)
        s_links = ttk.Scrollbar(f_links)
        s_links.pack(side=tk.RIGHT, fill=tk.Y)
        l_links = tk.Listbox(f_links, yscrollcommand=s_links.set, exportselection=False, font=("System", 13), fg="blue")
        l_links.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))
        s_links.config(command=l_links.yview)
        l_links.bind('<<ListboxSelect>>', self._on_link_select)

        # Colonna 3: Editor
        f_edit = ttk.Frame(paned)
        paned.add(f_edit, weight=4)
        inner = ttk.Frame(f_edit)
        inner.pack(fill=tk.BOTH, expand=True, padx=15)

        # Titolo + audio
        f_title = ttk.Frame(inner)
        f_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        lbl_title = ttk.Label(f_title, text="Nessun elemento", font=("System", 18, "bold"))
        lbl_title.pack(side=tk.LEFT)

        btn_speak = ttk.Button(f_title, text="Ascolta 🔊", width=10, command=self._speak_current)
        btn_speak.pack(side=tk.LEFT, padx=10)

        ttk.Label(inner, text="Pronuncia (Accenti/Dizione):", font=("System", 12)).pack(anchor=tk.W)
        e_pron = ttk.Entry(inner, font=("System", 13))
        e_pron.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(inner, text="Significato:", font=("System", 12)).pack(anchor=tk.W)
        t_def = tk.Text(inner, wrap=tk.WORD, font=("System", 13), height=5)
        t_def.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        ttk.Label(inner, text="Etimologia:", font=("System", 12)).pack(anchor=tk.W)
        t_ety = tk.Text(inner, wrap=tk.WORD, font=("System", 13), height=3)
        t_ety.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        lbl_links = "Sinonimi (separati da virgola):" if is_word else "Detti Simili (separati da virgola):"
        ttk.Label(inner, text=lbl_links, font=("System", 12)).pack(anchor=tk.W)
        e_links = ttk.Entry(inner, font=("System", 13))
        e_links.pack(fill=tk.X, pady=(0, 15))

        f_btns = ttk.Frame(inner)
        f_btns.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(f_btns, text="Salva Modifiche", command=self.save_current).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(f_btns, text="Elimina", command=self.delete_current).pack(side=tk.LEFT, padx=5)
        ttk.Button(f_btns, text="Nuovo Elemento", command=self.new_item).pack(side=tk.RIGHT)

        self.ui = {
            "list": l_list,
            "links": l_links,
            "title": lbl_title,
            "def": t_def,
            "ety": t_ety,
            "pron": e_pron,
            "entry_links": e_links,
        }

    # ── Proprietà helper ───────────────────────────────────────────

    @property
    def _target_dict(self):
        return self.db.words if self.item_type == "word" else self.db.sayings

    # ── Refresh lista ──────────────────────────────────────────────

    def refresh(self, select_item=None):
        self.ui["list"].delete(0, tk.END)
        for item in sorted(self._target_dict.keys()):
            self.ui["list"].insert(tk.END, item)
            if select_item and item == select_item:
                idx = self.ui["list"].size() - 1
                self.ui["list"].selection_set(idx)
                self.ui["list"].see(idx)

    # ── Selezione ──────────────────────────────────────────────────

    def _on_select(self, event):
        sel = self.ui["list"].curselection()
        if sel:
            self.load_details(self.ui["list"].get(sel[0]))

    def load_details(self, item_name):
        self.current_item = item_name
        info = self._target_dict.get(item_name)
        self.ui["title"].config(text=item_name)

        if info:
            self.ui["def"].delete(1.0, tk.END)
            self.ui["def"].insert(tk.END, info['definition'])
            self.ui["ety"].delete(1.0, tk.END)
            self.ui["ety"].insert(tk.END, info.get('etymology', ''))
            self.ui["pron"].delete(0, tk.END)
            self.ui["pron"].insert(0, info['metadata'].get('pronuncia', ''))
            self.ui["entry_links"].delete(0, tk.END)
            self.ui["entry_links"].insert(0, ", ".join(info['synonyms']))
            self.ui["links"].delete(0, tk.END)
            for syn in info['synonyms']:
                self.ui["links"].insert(tk.END, syn)
        else:
            self._clear_editor()

    def _on_link_select(self, event):
        sel = self.ui["links"].curselection()
        if not sel:
            return
        syn = self.ui["links"].get(sel[0])
        self.ui["links"].selection_clear(0, tk.END)

        if syn in self._target_dict:
            self.refresh(select_item=syn)
            self.load_details(syn)
        else:
            label = "La parola" if self.item_type == "word" else "Il detto"
            if messagebox.askyesno("Navigazione", f"{label} '{syn}' non esiste. Crearlo?"):
                self.current_item = syn
                self._clear_editor()
                self.ui["title"].config(text=syn)
                self.ui["def"].focus_set()
                self.ui["list"].selection_clear(0, tk.END)

    # ── CRUD ───────────────────────────────────────────────────────

    def save_current(self):
        if not self.current_item:
            return
        n_def = self.ui["def"].get(1.0, tk.END).strip()
        n_ety = self.ui["ety"].get(1.0, tk.END).strip()
        n_pron = self.ui["pron"].get().strip()
        links_str = self.ui["entry_links"].get().strip()
        links = [s.strip() for s in links_str.split(',') if s.strip()]
        self.db.save_item(self.current_item, n_def, n_ety, links, self.item_type, extra_fields={"pronuncia": n_pron})
        self.refresh(select_item=self.current_item)
        self.load_details(self.current_item)

    def delete_current(self):
        if not self.current_item:
            return
        if messagebox.askyesno("Conferma", f"Eliminare '{self.current_item}'?"):
            self.db.delete_item(self.current_item, self.item_type)
            self.current_item = None
            self.ui["title"].config(text="Nessun elemento")
            self._clear_editor()
            self.refresh()

    def new_item(self):
        label = "Nuova Parola" if self.item_type == "word" else "Nuovo Detto"
        prompt = "Nome della parola:" if self.item_type == "word" else "Titolo del detto:"
        name = simpledialog.askstring(label, prompt)
        if not name:
            return
        name = name.strip()

        if name in self._target_dict:
            self.refresh(select_item=name)
            self.load_details(name)
            return

        self.current_item = name.capitalize() if self.item_type == "word" else name
        self._clear_editor()
        self.ui["title"].config(text=self.current_item)
        self.ui["list"].selection_clear(0, tk.END)

        # Lookup automatico nel dizionario (solo per parole)
        if self.item_type == "word":
            self._dictionary_lookup(name)

        self.ui["def"].focus_set()

    # ── Utility ────────────────────────────────────────────────────

    def _clear_editor(self):
        self.ui["def"].delete(1.0, tk.END)
        self.ui["ety"].delete(1.0, tk.END)
        self.ui["pron"].delete(0, tk.END)
        self.ui["entry_links"].delete(0, tk.END)
        self.ui["links"].delete(0, tk.END)

    def _speak_current(self):
        if self.current_item:
            pron = self.ui["pron"].get().strip()
            TTS.speak(pron if pron else self.current_item)

    def _dictionary_lookup(self, word):
        # Cerca dictionary.db in più posizioni (dev, build, dist)
        candidates = [
            os.path.join(BASE_DIR, "dictionary.db"),
            os.path.join(BASE_DIR, "dist", "dictionary.db"),
        ]
        db_path = next((p for p in candidates if os.path.exists(p)), None)
        if not db_path:
            return
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT definition, etymology FROM dictionary WHERE word=?", (word.lower(),))
            row = cursor.fetchone()
            conn.close()
            if row:
                self.ui["def"].insert(tk.END, row[0] if row[0] else "")
                self.ui["ety"].insert(tk.END, row[1] if row[1] else "")
        except Exception as e:
            debug_log(f"Dictionary lookup error: {e}")
