"""Tab condiviso per Parole e Detti — UI + logica CRUD con CustomTkinter."""

import os
import re
import sqlite3
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from constants import BASE_DIR, debug_log
from tts import TTS


class SuggestionDialog(ctk.CTkToplevel):
    def __init__(self, parent, suggestions):
        super().__init__(parent)
        self.title("Suggerimenti")
        self.geometry("380x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # Centra la finestra rispetto al genitore
        self.update_idletasks()
        p_width = parent.winfo_width()
        p_height = parent.winfo_height()
        p_x = parent.winfo_x()
        p_y = parent.winfo_y()
        w = 380
        h = 320
        x = p_x + (p_width - w) // 2
        y = p_y + (p_height - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.selected_word = None

        # Widgets
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        lbl = ctk.CTkLabel(main_frame, text="Parola non trovata. Forse cercavi:", font=ctk.CTkFont(family="System", size=13, weight="bold"))
        lbl.pack(anchor=tk.W, pady=(0, 10))

        list_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        list_frame.pack(fill=tk.BOTH, expand=True)

        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#1c1c1e" if is_dark else "#ffffff"
        fg_color = "#ffffff" if is_dark else "#000000"
        border_color = "#2c2c2e" if is_dark else "#e5e5ea"

        self.listbox = tk.Listbox(
            list_frame,
            bg=bg_color,
            fg=fg_color,
            selectbackground="#007aff",
            selectforeground="#ffffff",
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=border_color,
            highlightcolor="#007aff",
            font=("System", 13),
            exportselection=False
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ctk.CTkScrollbar(list_frame, command=self.listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        self.listbox.config(yscrollcommand=scrollbar.set)

        for item in suggestions:
            self.listbox.insert(tk.END, item)

        self.listbox.bind("<Double-Button-1>", lambda e: self._on_select())

        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        btn_select = ctk.CTkButton(btn_frame, text="Seleziona", width=90, command=self._on_select)
        btn_select.pack(side=tk.RIGHT, padx=(5, 0))

        btn_cancel = ctk.CTkButton(
            btn_frame, 
            text="Annulla", 
            width=90, 
            fg_color="#8e8e93" if is_dark else "#c7c7cc", 
            hover_color="#636366" if is_dark else "#aeaeae", 
            text_color="#ffffff" if is_dark else "#000000",
            command=self.destroy
        )
        btn_cancel.pack(side=tk.RIGHT)

        self.listbox.focus_set()
        if suggestions:
            self.listbox.selection_set(0)

    def _on_select(self):
        sel = self.listbox.curselection()
        if sel:
            self.selected_word = self.listbox.get(sel[0])
        self.destroy()


class ItemTab:
    """Gestisce un tab (Parole o Detti) con lista, links navigabili e editor usando CustomTkinter."""

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

        # Grid-based layout per una spaziatura e allineamento perfetti
        grid_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        grid_frame.columnconfigure(0, weight=2)
        grid_frame.columnconfigure(1, weight=2)
        grid_frame.columnconfigure(2, weight=4)
        grid_frame.rowconfigure(0, weight=1)

        # Colonna 1: Lista completa
        f_list = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_list.grid(row=0, column=0, sticky="nsew", padx=5)
        
        title_list = "Tutte le Parole" if is_word else "Tutti i Detti"
        ctk.CTkLabel(f_list, text=title_list, font=ctk.CTkFont(family="System", size=14, weight="bold")).pack(anchor=tk.W, pady=(0, 5))
        
        list_container = ctk.CTkFrame(f_list, fg_color="transparent")
        list_container.pack(fill=tk.BOTH, expand=True)

        l_list = tk.Listbox(list_container, exportselection=False)
        l_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        s_list = ctk.CTkScrollbar(list_container, command=l_list.yview)
        s_list.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        l_list.config(yscrollcommand=s_list.set)
        l_list.bind('<<ListboxSelect>>', self._on_select)

        # Colonna 2: Links (Sinonimi / Detti Simili)
        f_links = ctk.CTkFrame(grid_frame, fg_color="transparent")
        f_links.grid(row=0, column=1, sticky="nsew", padx=5)
        
        title_links = "Sinonimi (Navigabili)" if is_word else "Detti Simili (Navigabili)"
        ctk.CTkLabel(f_links, text=title_links, font=ctk.CTkFont(family="System", size=14, weight="bold")).pack(anchor=tk.W, pady=(0, 5))
        
        links_container = ctk.CTkFrame(f_links, fg_color="transparent")
        links_container.pack(fill=tk.BOTH, expand=True)

        l_links = tk.Listbox(links_container, exportselection=False)
        l_links.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        s_links = ctk.CTkScrollbar(links_container, command=l_links.yview)
        s_links.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        l_links.config(yscrollcommand=s_links.set)
        l_links.bind('<<ListboxSelect>>', self._on_link_select)

        # Colonna 3: Editor
        f_edit = ctk.CTkScrollableFrame(grid_frame, label_text="Scheda Dettagli" if is_word else "Scheda Detto", label_font=ctk.CTkFont(family="System", size=14, weight="bold"))
        f_edit.grid(row=0, column=2, sticky="nsew", padx=5)

        # Titolo + audio
        f_title = ctk.CTkFrame(f_edit, fg_color="transparent")
        f_title.pack(anchor=tk.W, fill=tk.X, pady=(0, 10))

        lbl_title = ctk.CTkLabel(f_title, text="Nessun elemento", font=ctk.CTkFont(family="System", size=18, weight="bold"))
        lbl_title.pack(side=tk.LEFT)

        btn_speak = ctk.CTkButton(f_title, text="Ascolta 🔊", width=80, height=26, font=ctk.CTkFont(family="System", size=12), command=self._speak_current)
        btn_speak.pack(side=tk.LEFT, padx=10)

        ctk.CTkLabel(f_edit, text="Pronuncia (Accenti/Dizione):", font=ctk.CTkFont(family="System", size=12)).pack(anchor=tk.W, pady=(5, 2))
        e_pron = ctk.CTkEntry(f_edit, font=("System", 13))
        e_pron.pack(fill=tk.X, pady=(0, 10))

        ctk.CTkLabel(f_edit, text="Significato:", font=ctk.CTkFont(family="System", size=12)).pack(anchor=tk.W, pady=(5, 2))
        t_def = ctk.CTkTextbox(f_edit, wrap=tk.WORD, font=("System", 13), height=140)
        t_def.pack(fill=tk.X, pady=(0, 10))

        ctk.CTkLabel(f_edit, text="Etimologia:", font=ctk.CTkFont(family="System", size=12)).pack(anchor=tk.W, pady=(5, 2))
        t_ety = ctk.CTkTextbox(f_edit, wrap=tk.WORD, font=("System", 13), height=100)
        t_ety.pack(fill=tk.X, pady=(0, 10))

        lbl_links = "Sinonimi (separati da virgola):" if is_word else "Detti Simili (separati da virgola):"
        ctk.CTkLabel(f_edit, text=lbl_links, font=ctk.CTkFont(family="System", size=12)).pack(anchor=tk.W, pady=(5, 2))
        e_links = ctk.CTkEntry(f_edit, font=("System", 13))
        e_links.pack(fill=tk.X, pady=(0, 15))

        # Pulsanti CRUD posizionati in fondo all'editor
        f_btns = ctk.CTkFrame(f_edit, fg_color="transparent")
        f_btns.pack(fill=tk.X, pady=(10, 0))

        btn_save = ctk.CTkButton(f_btns, text="Salva Modifiche", fg_color="#34c759", hover_color="#28a745", text_color="#ffffff", command=self.save_current)
        btn_save.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        btn_delete = ctk.CTkButton(f_btns, text="Elimina", fg_color="#ff3b30", hover_color="#dc3545", text_color="#ffffff", command=self.delete_current)
        btn_delete.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        btn_new = ctk.CTkButton(f_btns, text="Nuovo Elemento", command=self.new_item)
        btn_new.pack(side=tk.LEFT, padx=(5, 0), expand=True, fill=tk.X)

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

    def _style_listboxes(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#1c1c1e" if is_dark else "#ffffff"
        fg_color = "#ffffff" if is_dark else "#000000"
        border_color = "#2c2c2e" if is_dark else "#e5e5ea"
        text_color_links = "#0a84ff" if is_dark else "#007aff"

        for name, listbox in [("list", self.ui["list"]), ("links", self.ui["links"])]:
            listbox.config(
                bg=bg_color,
                fg=text_color_links if name == "links" else fg_color,
                selectbackground="#007aff",
                selectforeground="#ffffff",
                relief=tk.FLAT,
                borderwidth=0,
                highlightthickness=1,
                highlightbackground=border_color,
                highlightcolor="#007aff",
                font=("System", 13)
            )

    # ── Refresh lista ──────────────────────────────────────────────

    def refresh(self, select_item=None):
        self._style_listboxes()
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
        self.ui["title"].configure(text=item_name)

        if info:
            self.ui["def"].delete("1.0", tk.END)
            self.ui["def"].insert(tk.END, info['definition'])
            self.ui["ety"].delete("1.0", tk.END)
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
                self.ui["title"].configure(text=syn)
                self.ui["def"].focus_set()
                self.ui["list"].selection_clear(0, tk.END)

    # ── CRUD ───────────────────────────────────────────────────────

    def save_current(self):
        if not self.current_item:
            return
        n_def = self.ui["def"].get("1.0", tk.END).strip()
        n_ety = self.ui["ety"].get("1.0", tk.END).strip()
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
            self.ui["title"].configure(text="Nessun elemento")
            self._clear_editor()
            self.refresh()

    def new_item(self):
        label = "Nuova Parola" if self.item_type == "word" else "Nuovo Detto"
        prompt = "Nome della parola:" if self.item_type == "word" else "Titolo del detto:"
        
        # CTkInputDialog moderno al posto di simpledialog
        dialog = ctk.CTkInputDialog(text=prompt, title=label)
        name = dialog.get_input()
        
        if not name:
            return
        name = name.strip()

        if name in self._target_dict:
            self.refresh(select_item=name)
            self.load_details(name)
            return

        self.current_item = name.capitalize() if self.item_type == "word" else name
        self._clear_editor()
        self.ui["title"].configure(text=self.current_item)
        self.ui["list"].selection_clear(0, tk.END)

        if self.item_type == "word":
            self._dictionary_lookup(name)

        self.ui["def"].focus_set()

    # ── Utility ────────────────────────────────────────────────────

    def _clear_editor(self):
        self.ui["def"].delete("1.0", tk.END)
        self.ui["ety"].delete("1.0", tk.END)
        self.ui["pron"].delete(0, tk.END)
        self.ui["entry_links"].delete(0, tk.END)
        self.ui["links"].delete(0, tk.END)

    def _speak_current(self):
        if self.current_item:
            pron = self.ui["pron"].get().strip()
            TTS.speak(pron if pron else self.current_item)

    def _dictionary_lookup(self, word):
        candidates = [
            os.path.join(BASE_DIR, "dictionary.db"),
            os.path.join(BASE_DIR, "dist", "dictionary.db"),
        ]
        db_path = next((p for p in candidates if os.path.exists(p)), None)
        if not db_path:
            return
        
        word_lower = word.lower().strip()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 1. Ricerca esatta
            cursor.execute("SELECT definition, etymology FROM dictionary WHERE word=?", (word_lower,))
            row = cursor.fetchone()
            if row:
                self.ui["def"].insert(tk.END, row[0] if row[0] else "")
                self.ui["ety"].insert(tk.END, row[1] if row[1] else "")
                conn.close()
                return

            # 2. Ricerca varianti singolare/plurale (regole di flessione italiane)
            parent = self.parent_frame.winfo_toplevel()
            stem_candidates = []
            if word_lower.endswith('i'):
                stem_candidates.extend([word_lower[:-1] + 'o', word_lower[:-1] + 'a', word_lower[:-1] + 'e'])
            elif word_lower.endswith('e'):
                stem_candidates.append(word_lower[:-1] + 'a')
            elif word_lower.endswith('o'):
                stem_candidates.append(word_lower[:-1] + 'i')
            elif word_lower.endswith('a'):
                stem_candidates.extend([word_lower[:-1] + 'e', word_lower[:-1] + 'i'])

            found_variants = []
            for cand in stem_candidates:
                cursor.execute("SELECT word FROM dictionary WHERE word=?", (cand,))
                r = cursor.fetchone()
                if r:
                    found_variants.append(r[0])

            # 3. Ricerca parziale LIKE (ricerca indicizzata tramite prefisso)
            like_pattern = word_lower + "%"
            cursor.execute("SELECT word FROM dictionary WHERE word LIKE ? LIMIT 15", (like_pattern,))
            like_results = [r[0] for r in cursor.fetchall()]

            # Ricerca parziale con tolleranza d'errore (rimuovendo l'ultimo carattere)
            if len(word_lower) > 3:
                like_pattern_short = word_lower[:-1] + "%"
                cursor.execute("SELECT word FROM dictionary WHERE word LIKE ? LIMIT 15", (like_pattern_short,))
                like_results.extend([r[0] for r in cursor.fetchall()])

            conn.close()

            # Unisci i suggerimenti eliminando i duplicati e preservando l'ordine
            suggestions = []
            seen = set()
            for w in found_variants + like_results:
                w_cap = w.capitalize()
                if w_cap not in seen and w.lower() != word_lower:
                    seen.add(w_cap)
                    suggestions.append(w_cap)

            if not suggestions:
                return

            # Mostra la finestra di dialogo dei suggerimenti
            dialog = SuggestionDialog(parent, suggestions)
            self.parent_frame.wait_window(dialog)

            if dialog.selected_word:
                selected = dialog.selected_word
                self.current_item = selected
                self.ui["title"].configure(text=selected)
                self._clear_editor()
                
                # Carica i dettagli della parola selezionata
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT definition, etymology FROM dictionary WHERE word=?", (selected.lower(),))
                row = cursor.fetchone()
                conn.close()
                if row:
                    self.ui["def"].insert(tk.END, row[0] if row[0] else "")
                    self.ui["ety"].insert(tk.END, row[1] if row[1] else "")
        except Exception as e:
            debug_log(f"Dictionary lookup error: {e}")
