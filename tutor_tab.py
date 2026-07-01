"""Tab Tutor AI — chat, quiz, integrazione NotebookLM con CustomTkinter."""

import json
import os
import re
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox

from constants import BASE_DIR, NOTEBOOKLM_CLI, debug_log, get_notebooklm_env


class TutorTab:
    """Gestisce il tab Tutor AI: chat, quiz generation, NotebookLM CLI usando CustomTkinter."""

    def __init__(self, parent_frame, db, enqueue_ui):
        self.parent_frame = parent_frame
        self.db = db
        self._enqueue_ui = enqueue_ui  # callback thread-safe dal main app

        self._nb_lock = threading.Lock()
        self._notebooklm_id = None

        self._setup_layout()


    @property
    def notebooklm_id(self):
        with self._nb_lock:
            return self._notebooklm_id

    @notebooklm_id.setter
    def notebooklm_id(self, value):
        with self._nb_lock:
            self._notebooklm_id = value
        self.quiz_data = None
        self.quiz_current_index = 0
        self.quiz_score = 0
        self.quiz_answers_checked = False

        # Reset visual state safely on the main thread
        def reset_ui():
            try:
                self.quiz_container_frame.pack_forget()
                self.chat_container_frame.pack(fill=tk.BOTH, expand=True)
            except Exception:
                pass
        self._enqueue_ui(reset_ui)

    # ── Layout ─────────────────────────────────────────────────────

    def _setup_layout(self):
        top_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        top_frame.pack(fill=tk.X, pady=10, padx=10)

        self.btn_prep = ctk.CTkButton(top_frame, text="Prepara Sessione (Invia Vocabolario a NotebookLM)", command=self.prepare_session)
        self.btn_prep.pack(side=tk.LEFT)

        self.btn_quiz_def = ctk.CTkButton(top_frame, text="Quiz Definizioni", command=lambda: self.start_quiz_generation("definitions"), state=tk.DISABLED)
        self.btn_quiz_def.pack(side=tk.LEFT, padx=5)

        self.btn_quiz_fill = ctk.CTkButton(top_frame, text="Quiz Completamento", command=lambda: self.start_quiz_generation("fill_blank"), state=tk.DISABLED)
        self.btn_quiz_fill.pack(side=tk.LEFT, padx=5)

        # 1. Contenitore Chat
        self.chat_container_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        self.chat_container_frame.pack(fill=tk.BOTH, expand=True)

        chat_frame = ctk.CTkFrame(self.chat_container_frame, fg_color="transparent")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # CTkTextbox ha le scrollbar integrate ed è molto più pulito
        self.tutor_chat = ctk.CTkTextbox(chat_frame, wrap=tk.WORD, font=("Helvetica", 14), state=tk.DISABLED)
        self.tutor_chat.pack(fill=tk.BOTH, expand=True)

        bottom_frame = ctk.CTkFrame(self.chat_container_frame, fg_color="transparent")
        bottom_frame.pack(fill=tk.X, pady=10, padx=10)

        self.tutor_input = ctk.CTkEntry(bottom_frame, font=("Helvetica", 14), placeholder_text="Scrivi al Tutor...")
        self.tutor_input.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.tutor_input.bind("<Return>", lambda e: self.send_tutor_msg())

        self.btn_send = ctk.CTkButton(bottom_frame, text="Invia Risposta", width=120, command=self.send_tutor_msg, state=tk.DISABLED)
        self.btn_send.pack(side=tk.RIGHT, padx=(10, 0))

        # 2. Contenitore Quiz (nascosto all'inizio)
        self.quiz_container_frame = ctk.CTkFrame(self.parent_frame, fg_color="transparent")

        self.quiz_header_frame = ctk.CTkFrame(self.quiz_container_frame, fg_color="transparent")
        self.quiz_header_frame.pack(fill=tk.X, pady=(10, 5), padx=15)
        self.quiz_progress_lbl = ctk.CTkLabel(self.quiz_header_frame, text="Domanda 0 di 0 | Punteggio: 0/0", font=ctk.CTkFont(family="Helvetica", size=14, weight="bold"))
        self.quiz_progress_lbl.pack(side=tk.LEFT)

        self.quiz_question_lbl = ctk.CTkLabel(self.quiz_container_frame, text="Domanda...", font=ctk.CTkFont(family="Helvetica", size=16), justify=tk.LEFT, anchor=tk.W)
        self.quiz_question_lbl.pack(fill=tk.X, pady=15, padx=15)

        self.quiz_options_frame = ctk.CTkFrame(self.quiz_container_frame, fg_color="transparent")
        self.quiz_options_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.quiz_opt_buttons = []
        for i in range(4):
            btn = ctk.CTkButton(
                self.quiz_options_frame,
                text=f"Opzione {i+1}",
                font=ctk.CTkFont(family="Helvetica", size=13),
                anchor="w",
                height=45,
                command=lambda idx=i: self.select_quiz_option(idx)
            )
            btn.pack(fill=tk.X, pady=5)
            self.quiz_opt_buttons.append(btn)
        
        self._reset_opt_buttons_style()

        self.quiz_feedback_frame = ctk.CTkFrame(self.quiz_container_frame)
        self.quiz_feedback_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.quiz_rationale_lbl = ctk.CTkLabel(self.quiz_feedback_frame, text="Spiegazione:", font=ctk.CTkFont(family="Helvetica", size=12, weight="bold"))
        self.quiz_rationale_lbl.pack(anchor=tk.W, padx=10, pady=(5, 2))
        self.quiz_rationale_txt = ctk.CTkTextbox(self.quiz_feedback_frame, wrap=tk.WORD, font=("Helvetica", 13), height=100, state=tk.DISABLED)
        self.quiz_rationale_txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.quiz_nav_frame = ctk.CTkFrame(self.quiz_container_frame, fg_color="transparent")
        self.quiz_nav_frame.pack(fill=tk.X, pady=15, padx=15)

        self.btn_quiz_hint = ctk.CTkButton(self.quiz_nav_frame, text="Suggerimento 💡", width=120, command=self.show_quiz_hint)
        self.btn_quiz_hint.pack(side=tk.LEFT)

        self.btn_quiz_exit = ctk.CTkButton(self.quiz_nav_frame, text="Esci dal Quiz ❌", fg_color="#ff3b30", hover_color="#dc3545", text_color="#ffffff", width=120, command=self.exit_quiz_view)
        self.btn_quiz_exit.pack(side=tk.RIGHT)

        self.btn_quiz_next = ctk.CTkButton(self.quiz_nav_frame, text="Avanti ➡️", width=120, command=self.next_quiz_question, state=tk.DISABLED)
        self.btn_quiz_next.pack(side=tk.RIGHT, padx=10)

    def _get_opt_btn_colors(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        return {
            "fg_color": "#2c2c2e" if is_dark else "#e5e5ea",
            "hover_color": "#3a3a3c" if is_dark else "#d1d1d6",
            "text_color": "#ffffff" if is_dark else "#000000"
        }

    def _reset_opt_buttons_style(self):
        colors = self._get_opt_btn_colors()
        for btn in self.quiz_opt_buttons:
            btn.configure(
                fg_color=colors["fg_color"],
                hover_color=colors["hover_color"],
                text_color=colors["text_color"],
                state=tk.NORMAL
            )

    # ── Chat ───────────────────────────────────────────────────────

    def append_chat(self, text, is_user=False):
        self.tutor_chat.configure(state=tk.NORMAL)
        prefix = "TU: " if is_user else "TUTOR: "
        self.tutor_chat.insert(tk.END, f"{prefix}{text}\n\n")
        self.tutor_chat.see(tk.END)
        self.tutor_chat.configure(state=tk.DISABLED)

    # ── NotebookLM CLI runner ──────────────────────────────────────

    def _run_cli(self, args, success_callback=None):
        def task():
            try:
                cmd = [NOTEBOOKLM_CLI] + args
                debug_log(f"Running notebooklm cmd: {cmd}")
                import subprocess
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=30
                )
                debug_log(f"Notebooklm cmd success: {result.stdout.strip()[:100]}")
                if success_callback:
                    self._enqueue_ui(success_callback, result.stdout.strip())
            except subprocess.TimeoutExpired as e:
                debug_log(f"Notebooklm cmd timeout: {e}")
                self._enqueue_ui(lambda: messagebox.showerror("Errore NotebookLM", "Timeout della richiesta a NotebookLM (30 secondi superati)."))
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr or e.stdout or str(e)
                debug_log(f"Notebooklm cmd error: {err_msg}")
                self._enqueue_ui(lambda: messagebox.showerror("Errore NotebookLM", f"Errore:\n{err_msg}"))
            except Exception as e:
                debug_log(f"Notebooklm cmd unexpected error: {e}")
                self._enqueue_ui(lambda: messagebox.showerror("Errore", str(e)))
        threading.Thread(target=task, daemon=True).start()

    # ── Detect existing notebook ───────────────────────────────────

    def detect_existing_notebook_async(self):
        def task():
            try:
                import subprocess
                cmd_list = [NOTEBOOKLM_CLI, "list", "--json"]
                debug_log(f"detect_existing_notebook_async: running {cmd_list}")
                list_res = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=15
                )
                debug_log("detect_existing_notebook_async: success")
                notebooks_data = json.loads(list_res.stdout)

                for nb in notebooks_data.get("notebooks", []):
                    if nb.get("title") == "Vocabolario Tutor Session":
                        nid = nb.get("id")
                        self.notebooklm_id = nid
                        debug_log(f"detect_existing_notebook_async: found notebook {nid}")
                        self._enqueue_ui(lambda: self._on_notebook_detected(nid))
                        break
            except Exception as e:
                debug_log(f"detect_existing_notebook_async error: {e}")

        threading.Thread(target=task, daemon=True).start()

    def _on_notebook_detected(self, notebook_id):
        self.btn_prep.configure(text="Sessione Pronta! (Aggiorna)")
        self.btn_quiz_def.configure(state=tk.NORMAL)
        self.btn_quiz_fill.configure(state=tk.NORMAL)
        self.btn_send.configure(state=tk.NORMAL)
        self.append_chat(f"📂 Rilevato Notebook esistente ({notebook_id}).\nLa chat e i quiz sono abilitati! Se hai aggiunto nuove parole, clicca su \"Sessione Pronta! (Aggiorna)\" per inviarle.")

    # ── Prepare session ────────────────────────────────────────────

    def prepare_session(self):
        self.btn_prep.configure(state=tk.DISABLED, text="Preparazione...")
        self.append_chat("Compilando il database locale per NotebookLM...")
        debug_log("prepare_session triggered")

        def task():
            import subprocess
            filepath = os.path.join(BASE_DIR, "vocab_session.txt")
            n_words = len(self.db.words)
            n_sayings = len(self.db.sayings)
            debug_log(f"prepare_session: exporting {n_words} words and {n_sayings} sayings to {filepath}")
            try:
                debug_log("prepare_session: setting language to IT")
                subprocess.run(
                    [NOTEBOOKLM_CLI, "language", "set", "it"],
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=10
                )

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("VOCABOLARIO PERSONALE DELL'UTENTE\n")
                    f.write("=" * 40 + "\n\n")

                    if self.db.words:
                        f.write(f"--- PAROLE ({n_words}) ---\n\n")
                        for w, info in self.db.words.items():
                            f.write(f"PAROLA: {w}\n")
                            f.write(f"SIGNIFICATO: {info['definition']}\n")
                            if info.get('etymology'):
                                f.write(f"ETIMOLOGIA: {info['etymology']}\n")
                            if info.get('synonyms'):
                                f.write(f"SINONIMI: {', '.join(info['synonyms'])}\n")
                            f.write("\n")

                    if self.db.sayings:
                        f.write(f"--- DETTI E PROVERBI ({n_sayings}) ---\n\n")
                        for s, info in self.db.sayings.items():
                            f.write(f"DETTO: {s}\n")
                            f.write(f"SIGNIFICATO: {info['definition']}\n")
                            if info.get('etymology'):
                                f.write(f"ORIGINE: {info['etymology']}\n")
                            if info.get('synonyms'):
                                f.write(f"DETTI SIMILI: {', '.join(info['synonyms'])}\n")
                            f.write("\n")

                debug_log("prepare_session: file exported successfully")
                self._enqueue_ui(lambda: self.append_chat(f"✅ File esportato: {n_words} parole, {n_sayings} detti → {filepath}"))
            except Exception as e:
                debug_log(f"prepare_session: file export failed: {e}")
                self._enqueue_ui(lambda: messagebox.showerror("Errore", f"Impossibile creare il file: {e}"))
                self._enqueue_ui(lambda: self.btn_prep.configure(state=tk.NORMAL, text="Prepara Sessione (Invia Vocabolario a NotebookLM)"))
                return

            try:
                self._enqueue_ui(lambda: self.append_chat("🔍 Ricerca di Notebook esistenti..."))

                cmd_list = [NOTEBOOKLM_CLI, "list", "--json"]
                debug_log(f"prepare_session: running list {cmd_list}")
                list_res = subprocess.run(
                    cmd_list,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=20
                )
                debug_log("prepare_session: list success")
                notebooks_data = json.loads(list_res.stdout)
                existing_notebook_id = None

                for nb in notebooks_data.get("notebooks", []):
                    if nb.get("title") == "Vocabolario Tutor Session":
                        existing_notebook_id = nb.get("id")
                        break

                if existing_notebook_id:
                    self.notebooklm_id = existing_notebook_id
                    debug_log(f"prepare_session: found existing notebook {self.notebooklm_id}")
                    self._enqueue_ui(lambda: self.append_chat(f"✅ Trovato Notebook esistente: {self.notebooklm_id}\n🔄 Rimozione vecchie sorgenti..."))

                    cmd_del = [NOTEBOOKLM_CLI, "source", "delete-by-title", "vocab_session.txt", "-n", self.notebooklm_id, "-y"]
                    debug_log(f"prepare_session: deleting source {cmd_del}")
                    subprocess.run(
                        cmd_del,
                        capture_output=True,
                        text=True,
                        env=get_notebooklm_env(),
                        stdin=subprocess.DEVNULL,
                        timeout=20
                    )
                    debug_log("prepare_session: source deleted (or skipped if not exist)")
                else:
                    debug_log("prepare_session: creating new notebook")
                    self._enqueue_ui(lambda: self.append_chat("📓 Creazione di un nuovo Notebook..."))
                    cmd_create = [NOTEBOOKLM_CLI, "create", "Vocabolario Tutor Session"]
                    out = subprocess.run(
                        cmd_create,
                        capture_output=True,
                        text=True,
                        check=True,
                        env=get_notebooklm_env(),
                        stdin=subprocess.DEVNULL,
                        timeout=20
                    ).stdout
                    debug_log(f"prepare_session: create success: {out.strip()}")
                    self._enqueue_ui(lambda: self.append_chat(f"📓 Notebook creato: {out.strip()}"))

                    match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', out)
                    if match:
                        self.notebooklm_id = match.group(1)
                    else:
                        raise ValueError(f"ID non trovato nell'output di creazione:\n{out}")

                debug_log(f"prepare_session: uploading source to {self.notebooklm_id}")
                self._enqueue_ui(lambda: self.append_chat(f"📤 Caricamento vocabolario su NotebookLM (ID: {self.notebooklm_id})..."))
                cmd_add = [NOTEBOOKLM_CLI, "source", "add", filepath, "--follow-symlinks", "-n", self.notebooklm_id]
                res = subprocess.run(
                    cmd_add,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=45
                )
                debug_log(f"prepare_session: upload success: {res.stdout.strip()}")
                self._enqueue_ui(lambda: self.append_chat(f"📤 Caricamento completato: {res.stdout.strip()}"))

                debug_log("prepare_session: configuring persona")
                self._enqueue_ui(lambda: self.append_chat("⚙️ Configurazione ruolo del Tutor (Persona)..."))
                persona_prompt = (
                    "Sei il Tutor personale di Vocabolario dell'utente. Il tuo scopo è aiutare l'utente ad apprendere e "
                    "memorizzare le parole e i detti presenti nel suo vocabolario caricato come sorgente. "
                    "Quando l'utente ti chiede un esercizio o inizia un quiz, proponigli una domanda a scelta multipla alla volta per una parola o un detto del vocabolario. "
                    "Per ciascuna sfida:\n"
                    "1. Presenta la definizione, l'etimologia o un esempio di frase con spazio vuoto per il termine misterioso.\n"
                    "2. Fornisci SEMPRE esattamente 4 opzioni di risposta numerate o contrassegnate da lettere (A, B, C, D) tra cui scegliere. Assicurati che una sia quella corretta e le altre 3 siano plausibili (distrattori).\n"
                    "3. NON svelare la risposta esatta subito. Attendi la risposta dell'utente (es. 'A', 'B', 'C', 'D' o il nome della parola).\n"
                    "4. Una volta ricevuta la risposta, confermagli se è corretta o meno, spiega brevemente perché (collegandoti all'etimologia o curiosità se utile) e poi proponi subito la successiva sfida a scelta multipla."
                )
                cmd_config = [NOTEBOOKLM_CLI, "configure", "-n", self.notebooklm_id, "--persona", persona_prompt]
                subprocess.run(
                    cmd_config,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=20
                )
                debug_log("prepare_session: persona configured successfully")
                self._enqueue_ui(lambda: self.append_chat("⚙️ Configurazione completata!"))

                self._enqueue_ui(self._session_ready)

            except subprocess.TimeoutExpired as e:
                debug_log(f"prepare_session timeout error: {e}")
                self._enqueue_ui(lambda: self.append_chat(f"❌ Errore: timeout superato per il comando a NotebookLM ({e.cmd})"))
                self._enqueue_ui(lambda: self.btn_prep.configure(state=tk.NORMAL, text="Prepara Sessione (Invia Vocabolario a NotebookLM)"))
            except subprocess.CalledProcessError as e:
                err_msg = e.stderr or e.stdout or str(e)
                debug_log(f"prepare_session CLI error: {err_msg}")
                self._enqueue_ui(lambda: self.append_chat(f"❌ Errore CLI: {err_msg}"))
                self._enqueue_ui(lambda: self.btn_prep.configure(state=tk.NORMAL, text="Prepara Sessione (Invia Vocabolario a NotebookLM)"))
            except Exception as e:
                debug_log(f"prepare_session unexpected error: {e}")
                self._enqueue_ui(lambda: self.append_chat(f"❌ Errore imprevisto: {e}"))
                self._enqueue_ui(lambda: self.btn_prep.configure(state=tk.NORMAL, text="Prepara Sessione (Invia Vocabolario a NotebookLM)"))

        threading.Thread(target=task, daemon=True).start()

    def _session_ready(self):
        self.btn_prep.configure(text="Sessione Pronta! (Aggiorna)")
        self.btn_quiz_def.configure(state=tk.NORMAL)
        self.btn_quiz_fill.configure(state=tk.NORMAL)
        self.btn_send.configure(state=tk.NORMAL)
        self.append_chat("Il tuo vocabolario è stato caricato su NotebookLM! Clicca su 'Quiz Definizioni' o 'Quiz Completamento' per iniziare.")

    # ── Quiz generation ────────────────────────────────────────────

    def _enable_quiz_buttons(self):
        self.btn_quiz_def.configure(state=tk.NORMAL, text="Quiz Definizioni")
        self.btn_quiz_fill.configure(state=tk.NORMAL, text="Quiz Completamento")

    def _disable_quiz_buttons(self, active_text="Caricamento..."):
        self.btn_quiz_def.configure(state=tk.DISABLED, text=active_text)
        self.btn_quiz_fill.configure(state=tk.DISABLED, text=active_text)

    def start_quiz_generation(self, quiz_type="definitions"):
        if not self.notebooklm_id:
            messagebox.showwarning("Attenzione", "Devi prima preparare la sessione!")
            return

        lbl = "Definizioni" if quiz_type == "definitions" else "Completamento"
        self._disable_quiz_buttons(f"Generazione Quiz {lbl}...")
        self.append_chat(f"🔄 Invio richiesta di generazione del Quiz ({lbl}) a NotebookLM...")

        def task():
            import subprocess
            try:
                if quiz_type == "definitions":
                    query = "Genera un quiz di definizioni ed etimologie interamente in lingua italiana (domande, opzioni e spiegazioni in italiano) basato sulle parole presenti nel vocabolario. Per ogni domanda proponi 4 opzioni di risposta con un solo termine corretto."
                else:
                    query = "Genera un quiz di completamento frasi a scelta multipla, interamente in lingua italiana. Ciascuna domanda deve contenere una frase formale ed elevata in cui la parola corretta del vocabolario è omessa (sostituita da una lacuna ben evidente come '[...]') in modo da testare l'uso contestuale del termine. Le 4 opzioni di risposta devono essere singole parole del vocabolario (di cui una sola corretta). Le frasi generate devono rispecchiare fedelmente il contesto d'uso formale o elevato del termine (non usare mai un registro colloquiale o frasi banali come 'bro sei sicofante')."

                cmd_gen = [NOTEBOOKLM_CLI, "generate", "quiz", query, "-n", self.notebooklm_id, "--wait", "--json"]
                debug_log(f"start_quiz_generation: running {cmd_gen}")
                res_gen = subprocess.run(
                    cmd_gen,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=90
                )
                debug_log(f"start_quiz_generation: generate success: {res_gen.stdout.strip()}")
                self._enqueue_ui(lambda: self.append_chat("📥 Quiz generato con successo! Download in corso..."))

                dest_path = os.path.join(BASE_DIR, "current_quiz.json")
                cmd_dl = [NOTEBOOKLM_CLI, "download", "quiz", dest_path, "-n", self.notebooklm_id, "--latest", "--force", "--format", "json"]
                debug_log(f"start_quiz_generation: running {cmd_dl}")
                res_dl = subprocess.run(
                    cmd_dl,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=get_notebooklm_env(),
                    stdin=subprocess.DEVNULL,
                    timeout=45
                )
                debug_log(f"start_quiz_generation: download success: {res_dl.stdout.strip()}")

                if os.path.exists(dest_path):
                    self._enqueue_ui(self._on_quiz_downloaded, dest_path)
                else:
                    raise FileNotFoundError(f"Il file di destinazione {dest_path} non è stato creato.")

            except subprocess.TimeoutExpired as e:
                debug_log(f"start_quiz_generation timeout: {e}")
                self._enqueue_ui(lambda: self.append_chat(f"❌ Timeout durante la generazione del quiz: {e}"))
                self._enqueue_ui(self._enable_quiz_buttons)
            except Exception as e:
                debug_log(f"start_quiz_generation error: {e}")
                self._enqueue_ui(lambda: self.append_chat(f"❌ Errore nella generazione del quiz: {e}"))
                self._enqueue_ui(self._enable_quiz_buttons)

        threading.Thread(target=task, daemon=True).start()

    def _on_quiz_downloaded(self, filepath):
        self._enable_quiz_buttons()
        self.append_chat("✅ Quiz pronto! Avvio dell'interfaccia quiz...")

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                self.quiz_data = json.load(f)

            if not self.quiz_data or "questions" not in self.quiz_data or not self.quiz_data["questions"]:
                raise ValueError("Nessuna domanda trovata nel quiz generato.")

            self.quiz_current_index = 0
            self.quiz_score = 0

            self.chat_container_frame.pack_forget()
            self.quiz_container_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            self._show_quiz_question()

        except Exception as e:
            debug_log(f"on_quiz_downloaded load error: {e}")
            messagebox.showerror("Errore", f"Impossibile avviare il quiz:\n{e}")

    # ── Quiz UI ────────────────────────────────────────────────────

    def _show_quiz_question(self):
        if not self.quiz_data or self.quiz_current_index >= len(self.quiz_data["questions"]):
            self._show_quiz_results()
            return

        q_data = self.quiz_data["questions"][self.quiz_current_index]
        self.quiz_answers_checked = False

        tot = len(self.quiz_data["questions"])
        self.quiz_progress_lbl.configure(text=f"Domanda {self.quiz_current_index + 1} di {tot} | Punteggio: {self.quiz_score}/{self.quiz_current_index}")

        self.quiz_question_lbl.configure(text=q_data["question"])

        self._reset_opt_buttons_style()
        options = q_data.get("answerOptions", [])
        for i in range(4):
            btn = self.quiz_opt_buttons[i]
            if i < len(options):
                opt = options[i]
                btn.configure(
                    text=f"{chr(65+i)}) {opt['text']}",
                    state=tk.NORMAL
                )
                btn.pack(fill=tk.X, pady=5)
            else:
                btn.pack_forget()

        self.quiz_rationale_txt.configure(state=tk.NORMAL)
        self.quiz_rationale_txt.delete("1.0", tk.END)
        self.quiz_rationale_txt.configure(state=tk.DISABLED)

        self.btn_quiz_next.configure(state=tk.DISABLED)
        self.btn_quiz_hint.configure(state=tk.NORMAL if q_data.get("hint") else tk.DISABLED)

    def select_quiz_option(self, index):
        if self.quiz_answers_checked:
            return

        self.quiz_answers_checked = True
        q_data = self.quiz_data["questions"][self.quiz_current_index]
        options = q_data.get("answerOptions", [])

        correct_idx = -1
        for i, opt in enumerate(options):
            if opt.get("isCorrect"):
                correct_idx = i
                break

        for i in range(len(options)):
            btn = self.quiz_opt_buttons[i]
            prefix = f"{chr(65+i)}) "
            opt_text = options[i]['text']

            if i == correct_idx:
                btn.configure(
                    text=f"✅ {prefix}{opt_text}",
                    fg_color="#34c759",
                    hover_color="#34c759",
                    text_color="#ffffff",
                    state=tk.NORMAL
                )
            elif i == index:
                btn.configure(
                    text=f"❌ {prefix}{opt_text}",
                    fg_color="#ff3b30",
                    hover_color="#ff3b30",
                    text_color="#ffffff",
                    state=tk.NORMAL
                )
            else:
                btn.configure(state=tk.DISABLED)

        selected_correct = (index == correct_idx)
        if selected_correct:
            self.quiz_score += 1

        rationale_text = ""
        if index < len(options):
            rationale_text = f"La tua scelta: {options[index].get('rationale', '')}\n\n"
        if not selected_correct and correct_idx != -1:
            rationale_text += f"Risposta Corretta: {options[correct_idx].get('rationale', '')}"

        self.quiz_rationale_txt.configure(state=tk.NORMAL)
        self.quiz_rationale_txt.delete("1.0", tk.END)
        self.quiz_rationale_txt.insert(tk.END, rationale_text)
        self.quiz_rationale_txt.configure(state=tk.DISABLED)

        tot = len(self.quiz_data["questions"])
        self.quiz_progress_lbl.configure(text=f"Domanda {self.quiz_current_index + 1} di {tot} | Punteggio: {self.quiz_score}/{self.quiz_current_index + 1}")

        self.btn_quiz_next.configure(state=tk.NORMAL)
        self.btn_quiz_hint.configure(state=tk.DISABLED)

    def show_quiz_hint(self):
        if not self.quiz_data:
            return
        q_data = self.quiz_data["questions"][self.quiz_current_index]
        hint = q_data.get("hint")
        if hint:
            messagebox.showinfo("Suggerimento", hint)

    def next_quiz_question(self):
        self.quiz_current_index += 1
        self._show_quiz_question()

    def _show_quiz_results(self):
        tot = len(self.quiz_data["questions"])
        pct = (self.quiz_score / tot) * 100 if tot > 0 else 0

        for btn in self.quiz_opt_buttons:
            btn.pack_forget()

        self.quiz_progress_lbl.configure(text="Quiz Completato!")
        self.quiz_question_lbl.configure(
            text=f"Complimenti! Hai completato il quiz.\n\nPunteggio Finale: {self.quiz_score} su {tot} ({pct:.1f}% di risposte corrette)."
        )

        self.quiz_rationale_txt.configure(state=tk.NORMAL)
        self.quiz_rationale_txt.delete("1.0", tk.END)
        self.quiz_rationale_txt.insert(tk.END, "Puoi chiudere il quiz e ritornare alla chat, oppure generarne un altro!")
        self.quiz_rationale_txt.configure(state=tk.DISABLED)

        self.btn_quiz_next.configure(state=tk.DISABLED)
        self.btn_quiz_hint.configure(state=tk.DISABLED)

    def exit_quiz_view(self):
        self.quiz_container_frame.pack_forget()
        self.chat_container_frame.pack(fill=tk.BOTH, expand=True)

    # ── Chat messaging ─────────────────────────────────────────────

    def send_tutor_msg(self):
        msg = self.tutor_input.get().strip()
        if not msg or not self.notebooklm_id:
            return
        self.tutor_input.delete(0, tk.END)
        self.append_chat(msg, is_user=True)
        self.btn_send.configure(state=tk.DISABLED)
        self._run_cli(["ask", msg, "-n", self.notebooklm_id], self._on_tutor_response)

    def _on_tutor_response(self, text):
        self.append_chat(text)
        self.btn_send.configure(state=tk.NORMAL)
        self.btn_quiz_def.configure(state=tk.NORMAL)
        self.btn_quiz_fill.configure(state=tk.NORMAL)

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
                if getattr(self, "quiz_question_lbl", None) and str(widget) == str(self.quiz_question_lbl):
                    widget.configure(font=ctk.CTkFont(family="Helvetica", size=font_gen.cget("size") + 3))
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

