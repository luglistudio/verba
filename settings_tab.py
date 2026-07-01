"""Tab Impostazioni — regolazione font e visualizzazione."""

import tkinter as tk
import customtkinter as ctk


class SettingsTab:
    def __init__(self, parent_frame, db, app_update_fonts_callback):
        self.parent_frame = parent_frame
        self.db = db
        self.app_update_fonts_callback = app_update_fonts_callback
        self.ui = {}
        self._setup_layout()

    def _setup_layout(self):
        # Master container with some padding
        container = ctk.CTkFrame(self.parent_frame, fg_color="transparent")
        container.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Title
        lbl_title = ctk.CTkLabel(
            container, 
            text="⚙️ Impostazioni Visualizzazione", 
            font=ctk.CTkFont(family="Helvetica", size=18, weight="bold")
        )
        lbl_title.pack(anchor=tk.W, pady=(0, 20))

        # Card / Frame for Settings
        card = ctk.CTkFrame(container)
        card.pack(fill=tk.X, ipady=15, padx=5, pady=5)

        # Meaning Font Size setting
        f_mean_lbl = ctk.CTkLabel(
            card, 
            text="Dimensione carattere del Significato ed Etimologia (molto grande e leggibile):", 
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        )
        f_mean_lbl.pack(anchor=tk.W, padx=20, pady=(15, 5))

        sizes_meaning = ["14", "16", "18", "20", "22", "24", "26", "28", "30"]
        current_mean = str(self.db.settings.get("font_size_meaning", 18))
        if current_mean not in sizes_meaning:
            sizes_meaning.append(current_mean)
            sizes_meaning.sort()

        self.opt_mean = ctk.CTkOptionMenu(
            card, 
            values=sizes_meaning, 
            command=self._on_mean_size_changed,
            font=("Helvetica", 13)
        )
        self.opt_mean.set(current_mean)
        self.opt_mean.pack(anchor=tk.W, padx=20, pady=(0, 15))

        # General Font Size setting
        f_gen_lbl = ctk.CTkLabel(
            card, 
            text="Dimensione carattere generale (liste, menu):", 
            font=ctk.CTkFont(family="Helvetica", size=13, weight="bold")
        )
        f_gen_lbl.pack(anchor=tk.W, padx=20, pady=(10, 5))

        sizes_general = ["11", "12", "13", "14", "15", "16", "18", "20"]
        current_gen = str(self.db.settings.get("font_size_general", 13))
        if current_gen not in sizes_general:
            sizes_general.append(current_gen)
            sizes_general.sort()

        self.opt_gen = ctk.CTkOptionMenu(
            card, 
            values=sizes_general, 
            command=self._on_gen_size_changed,
            font=("Helvetica", 13)
        )
        self.opt_gen.set(current_gen)
        self.opt_gen.pack(anchor=tk.W, padx=20, pady=(0, 15))

        self.ui = {
            "title": lbl_title,
            "mean_lbl": f_mean_lbl,
            "gen_lbl": f_gen_lbl,
            "opt_mean": self.opt_mean,
            "opt_gen": self.opt_gen,
        }

    def _on_mean_size_changed(self, val):
        self.db.save_settings({"font_size_meaning": int(val)})
        self.app_update_fonts_callback()

    def _on_gen_size_changed(self, val):
        self.db.save_settings({"font_size_general": int(val)})
        self.app_update_fonts_callback()

    def update_fonts(self):
        f_gen = self.db.settings.get("font_size_general", 13)
        
        font_gen = ctk.CTkFont(family="Helvetica", size=f_gen)
        font_bold = ctk.CTkFont(family="Helvetica", size=f_gen + 1, weight="bold")
        font_title = ctk.CTkFont(family="Helvetica", size=f_gen + 5, weight="bold")
        
        self._apply_fonts_recursive(self.parent_frame, font_gen, font_bold, font_title)

    def _apply_fonts_recursive(self, widget, font_gen, font_bold, font_title):
        try:
            w_class = widget.__class__.__name__
            if w_class == "CTkLabel":
                if self.ui.get("title") and str(widget) == str(self.ui.get("title")):
                    widget.configure(font=font_title)
                elif (self.ui.get("mean_lbl") and str(widget) == str(self.ui.get("mean_lbl"))) or (self.ui.get("gen_lbl") and str(widget) == str(self.ui.get("gen_lbl"))):
                    widget.configure(font=font_bold)
                else:
                    widget.configure(font=font_gen)
            elif w_class in ("CTkOptionMenu", "CTkButton"):
                widget.configure(font=font_gen)
        except Exception:
            pass

        for child in widget.winfo_children():
            self._apply_fonts_recursive(child, font_gen, font_bold, font_title)
