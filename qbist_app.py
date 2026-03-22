'''
Python Qbist GUI Application using Tkinter    

This application provides a graphical interface for creating and manipulating Qbist patterns.
It allows users to generate variations, save/load patterns, and render previews with anti-aliasing options.
ported from the original C code in GIMP's plug-ins, this version is adapted for Python with Tkinter.
by Thomas Cigolla, 29.05.2025

Orginal C-Code https://github.com/GNOME/gimp/blob/master/plug-ins/common/qbist.c
Written 1997 Jens Ch. Restemeier <jrestemeier@currantbun.com>
This program is based on an algorithm / article by Jörn Loviscach.

It appeared in c't 10/95, page 326 and is called
Ausgewürfelt - Moderne Kunst algorithmisch erzeugen"
(~modern art created with algorithms).
'''
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import datetime
import ttkbootstrap as tb # Für modernere Themes mit ttkbootstrap
import threading
import gettext # For _switch_language's direct gettext usage

# Import utilities first to set up i18n (especially _)
import qbist_utilities
from qbist_utilities import (
    load_config, save_config, load_about_text, _,
    APP_NAME, LOCALE_DIR, DEFAULT_LANGUAGE, ABOUT_FILE_PATH,
    DEFAULT_THEME, DEFAULT_IMAGE_DIR, DEFAULT_PATTERN_DIR, DEFAULT_GEN_PRESET, DEFAULT_GEN_RESOLUTION_NAME,
    DEFAULT_GEN_IMAGE_WIDTH, DEFAULT_GEN_IMAGE_HEIGHT
)

# Then import UI components which might use _ at import time or define constants
import qbist_ui_components
from qbist_ui_components import PREVIEW_SIZE_DEFAULT # Example if needed directly

import qbist_core # Requires qbist_core.py in the same directory or Python path


class QbistApp:
    def __init__(self, master, initial_config):
        self.master = master
        
        self.main_info = qbist_core.create_info()
        self.variation_infos = [qbist_core.modify_info(self.main_info) for _ in range(8)]
        self.history = [] # For undo: stores (main_info_copy, variation_infos_tuple_copy)
        self._save_history_state() # Save initial state

        self.preview_render_size = PREVIEW_SIZE_DEFAULT
        self.oversampling_var = tk.IntVar(value=1) 

        # Lade Konfiguration und initialisiere Ausgabeverzeichnisse
        self.image_output_dir = initial_config.get("image_dir")
        self.pattern_output_dir = initial_config.get("pattern_dir")
        self.default_gen_image_width = initial_config.get("default_gen_image_width")
        self.default_gen_image_height = initial_config.get("default_gen_image_height")
        self.current_theme_name = initial_config.get("theme")
        self.current_language_code = initial_config.get("language", DEFAULT_LANGUAGE)
        self.image_presets = initial_config.get("image_presets") # Loaded from qbist_utilities defaults
        
        # Standardwerte für den Generierungsdialog aus der Konfiguration
        self.default_gen_preset_from_config = initial_config.get("default_gen_preset", DEFAULT_GEN_PRESET)
        self.default_gen_resolution_name_from_config = initial_config.get("default_gen_resolution_name", DEFAULT_GEN_RESOLUTION_NAME)

        # Zuletzt verwendete Werte für den Generierungsdialog (initialisiert mit Konfigurations- oder App-Standardwerten)
        self.last_gen_preset = self.default_gen_preset_from_config
        self.last_gen_resolution_name = self.default_gen_resolution_name_from_config
        self.last_gen_orientation = "P" # Standard-Ausrichtung

        initial_width, initial_height = self._get_dimensions_for_preset(
            self.last_gen_preset,
            self.last_gen_resolution_name,
            self.last_gen_orientation
        )
        self.last_gen_width = str(initial_width if initial_width is not None else self.default_gen_image_width)
        self.last_gen_height = str(initial_height if initial_height is not None else self.default_gen_image_height)

        os.makedirs(self.image_output_dir, exist_ok=True)
        os.makedirs(self.pattern_output_dir, exist_ok=True)

        self.about_content = load_about_text()

        # For language menu access
        self.LOCALE_DIR = LOCALE_DIR
        self.DEFAULT_LANGUAGE = DEFAULT_LANGUAGE

        try:
            pil_icon = Image.open("logo.png")
            self.app_icon_tk = ImageTk.PhotoImage(pil_icon) # Store as instance attribute
            if hasattr(master, 'iconphoto'):
                master.iconphoto(True, self.app_icon_tk)
        except Exception as e:
            print(_("Could not load app icon 'logo.png': {error}").format(error=e))

        # Create main UI layout using the new module
        qbist_ui_components.create_main_layout(self, master)
        qbist_ui_components.create_menubar(self, master)

        self._update_all_previews()
        self._setup_tooltips()

    def _get_dimensions_for_preset(self, preset_key, resolution_name, orientation):
        """Ermittelt Breite und Höhe für ein gegebenes Preset, Auflösung und Ausrichtung."""
        if preset_key and resolution_name and preset_key in self.image_presets:
            preset_details_list = self.image_presets[preset_key]
            for res_detail in preset_details_list:
                if res_detail["name"] == resolution_name:
                    base_w, base_h = res_detail["width"], res_detail["height"]
                    supports_orientation = res_detail.get("supports_orientation_change", False)
                    if supports_orientation and orientation == "L":
                        return base_h, base_w
                    return base_w, base_h
        return None, None


    def _disable_ui_for_long_op(self, message=_(qbist_ui_components.UI_STATUS_PROCESSING)):
        """Deaktiviert wichtige UI-Elemente und zeigt einen Warte-Cursor."""
        self.master.config(cursor="watch")
        self.progressbar.grid(row=4, column=0, columnspan=3, pady=(5,10), sticky=tk.EW) # Progressbar anzeigen
        self.progressbar.start(10) # Animation starten (Intervall in ms)
        for widget in self.interactive_widgets_for_long_ops:
            if widget: # Sicherstellen, dass das Widget existiert
                if not isinstance(widget, tk.Canvas): # tk.Canvas hat keine 'state'-Option
                    widget.config(state=tk.DISABLED)
                # Für tk.Canvas-Objekte ist das Deaktivieren der Buttons meist ausreichend.
        self.status_label.config(text=message)
        self.master.update_idletasks() # Änderungen sofort sichtbar machen

    def _enable_ui_after_long_op(self, final_status_message=_(qbist_ui_components.UI_STATUS_READY)):
        """Aktiviert UI-Elemente und setzt den Cursor zurück."""
        self.master.config(cursor="")
        self.progressbar.stop() # Animation stoppen
        self.progressbar.grid_remove() # Progressbar ausblenden
        for widget in self.interactive_widgets_for_long_ops:
            if widget:
                if not isinstance(widget, tk.Canvas):
                    widget.config(state=tk.NORMAL)
        self.status_label.config(text=final_status_message)
        self.master.update_idletasks()


    def _save_history_state(self):
        current_main_copy = self.main_info.copy()
        current_variations_copy = tuple(v.copy() for v in self.variation_infos)
        
        if not self.history or \
           (self.history[-1][0] != current_main_copy or self.history[-1][1] != current_variations_copy):
            self.history.append((current_main_copy, current_variations_copy))
            if len(self.history) > 20: # Limit history size
                self.history.pop(0)

    def _render_preview(self, exp_info: qbist_core.ExpInfo, canvas_widget: tk.Canvas, target_size: int):
        pixel_bytes = qbist_core.generate_image_data(exp_info, target_size, target_size, oversampling=1)
        pil_image = Image.frombytes("RGBA", (target_size, target_size), pixel_bytes)
        img_tk = ImageTk.PhotoImage(pil_image)
        
        canvas_widget.delete("all") # Clear previous image
        canvas_widget.create_image(0, 0, anchor=tk.NW, image=img_tk)
        canvas_widget.image = img_tk 

    def _update_all_previews(self):
        self.status_label.config(text=_(qbist_ui_components.UI_STATUS_UPDATING_PREVIEWS))
        self.master.update_idletasks()

        center_canvas = self.preview_canvases[4]
        center_size = int(self.preview_render_size * 1.25)
        self._render_preview(self.main_info, center_canvas, center_size)

        for i in range(9): # 9 canvases
            if i == 4: continue
            canvas = self.preview_canvases[i]
            variation_info = self.variation_infos[self.gui_to_variation_map[i]]
            self._render_preview(variation_info, canvas, self.preview_render_size)
        
        self.status_label.config(text=_(qbist_ui_components.UI_STATUS_PREVIEWS_UPDATED))

    def _on_center_preview_click(self):
        self._generate_new_variations_from_main()

    def _on_variation_preview_click(self, gui_canvas_index: int):
        self._save_history_state()
        variation_idx = self.gui_to_variation_map[gui_canvas_index]
        self.main_info = self.variation_infos[variation_idx].copy()
        self._generate_new_variations_from_main(update_history=False) # History already saved

    def _generate_new_variations_from_main(self, update_history=True):
        if update_history:
            self._save_history_state()
        self.variation_infos = [qbist_core.modify_info(self.main_info) for _ in range(8)]
        self._update_all_previews()

    def _undo_selection(self):
        if len(self.history) > 1:
            self.history.pop() 
            last_main, last_variations_tuple = self.history[-1]
            
            self.main_info = last_main.copy()
            self.variation_infos = [v.copy() for v in last_variations_tuple]
            
            self._update_all_previews()
            self.status_label.config(text=_(qbist_ui_components.UI_STATUS_UNDO_SUCCESSFUL))
        else:
            self.status_label.config(text=_(qbist_ui_components.UI_STATUS_NOTHING_TO_UNDO))

    def _load_pattern(self):
        filepath = filedialog.askopenfilename(
            initialdir=self.pattern_output_dir,
            defaultextension=".qbe",
            filetypes=[(_(qbist_ui_components.UI_BTN_LOAD_PATTERN).split(" (")[0], "*.qbe"), (_("All Files"), "*.*")], # Simplified name
            parent=self.master
        )
        if filepath:
            self.status_label.config(text=_("Loading {filename}...").format(filename=os.path.basename(filepath)))
            loaded_info = qbist_core.load_qbe_data(filepath)
            if loaded_info:
                self._save_history_state()
                self.main_info = loaded_info
                self._generate_new_variations_from_main(update_history=False) # History saved before main_info change
                self.status_label.config(text=_("Loaded: {filename}").format(filename=os.path.basename(filepath)))
            else:
                messagebox.showerror(_("Load Error"), _("Could not load pattern from {path}").format(path=filepath))
                self.status_label.config(text=_("Load failed."))

    def _save_pattern(self):
        os.makedirs(self.pattern_output_dir, exist_ok=True)
        filepath = filedialog.asksaveasfilename(
            initialdir=self.pattern_output_dir,
            defaultextension=".qbe",
            filetypes=[(_(qbist_ui_components.UI_BTN_LOAD_PATTERN).split(" (")[0], "*.qbe"), (_("All Files"), "*.*")],
            initialfile="pattern.qbe",
            parent=self.master
        )
        if filepath:
            if qbist_core.save_qbe_data(filepath, self.main_info):
                self.status_label.config(text=_("Saved: {filename}").format(filename=os.path.basename(filepath)))
            else:
                messagebox.showerror(_("Save Error"), _("Could not save pattern to {path}").format(path=filepath))
                self.status_label.config(text=_("Save failed."))

    def _browse_directory(self, dir_var: tk.StringVar, parent_dialog: tk.Toplevel, default_path_attr_name: str):
        """Helper to browse for a directory."""
        current_path = dir_var.get()
        if not os.path.isdir(current_path):
            current_path = getattr(self, default_path_attr_name, os.getcwd())
        
        if not os.path.isdir(current_path): # Sicherstellen, dass der Pfad existiert
            current_path = os.getcwd()

        directory = filedialog.askdirectory(
            initialdir=current_path,
            title=_(qbist_ui_components.UI_TITLE_SELECT_DIRECTORY),
            parent=parent_dialog 
        )
        if directory:
            dir_var.set(directory)

    def _configure_output_directories(self):
        dialog = tk.Toplevel(self.master)
        dialog.title(_(qbist_ui_components.UI_DIALOG_TITLE_CONFIG_OUTPUT_DIRS))
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        
        img_dir_var = tk.StringVar(value=self.image_output_dir)
        pat_dir_var = tk.StringVar(value=self.pattern_output_dir)

        def on_save_config_dialog():
            self.image_output_dir = img_dir_var.get()
            self.pattern_output_dir = pat_dir_var.get()
            if not self.image_output_dir or not self.pattern_output_dir:
                messagebox.showwarning(_("Missing Path"), _("Both directory paths must be set."), parent=dialog)
                return
            save_config(
                self.image_output_dir, self.pattern_output_dir,
                self.default_gen_image_width, self.default_gen_image_height,
                self.current_theme_name,
                self.current_language_code,
                self.default_gen_preset_from_config,
                self.default_gen_resolution_name_from_config
            )
            self.status_label.config(text=_("Output directories configured."))
            dialog.destroy()

        qbist_ui_components.populate_output_directories_dialog_widgets(
            frame, img_dir_var, pat_dir_var,
            browse_img_command=lambda: self._browse_directory(img_dir_var, dialog, "image_output_dir"),
            browse_pat_command=lambda: self._browse_directory(pat_dir_var, dialog, "pattern_output_dir"),
            save_command=on_save_config_dialog,
            cancel_command=dialog.destroy
        )
        dialog.wait_window()

    def _configure_default_image_size(self):
        dialog = tk.Toplevel(self.master)
        dialog.title(_(qbist_ui_components.UI_DIALOG_TITLE_SET_DEFAULT_IMG_SIZE))
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        width_var = tk.StringVar(value=str(self.default_gen_image_width))
        height_var = tk.StringVar(value=str(self.default_gen_image_height))
        # StringVars für die neuen Standard-Generierungseinstellungen
        default_gen_preset_var = tk.StringVar(value=self.default_gen_preset_from_config)
        default_gen_resolution_var = tk.StringVar(value=self.default_gen_resolution_name_from_config)

        def on_save_size_config():
            try:
                new_width = int(width_var.get())
                new_height = int(height_var.get())
                if new_width <= 0 or new_height <= 0:
                    messagebox.showerror(_("Invalid Input"), _("Width and height must be positive numbers."), parent=dialog)
                    return

                new_default_gen_preset = default_gen_preset_var.get()
                new_default_gen_resolution = default_gen_resolution_var.get()

                if new_default_gen_preset:  # Wenn ein Preset gewählt wurde
                    if not new_default_gen_resolution:  # Aber keine Auflösung
                        messagebox.showerror(_("Invalid Selection"),
                                             _("Please select a resolution for the chosen default preset '{preset}'.").format(
                                                 preset=new_default_gen_preset),
                                             parent=dialog)
                        return
                    # Überprüfe, ob die Auflösung für das Preset gültig ist
                    valid_resolutions_for_preset = [res['name'] for res in self.image_presets.get(new_default_gen_preset, [])]
                    if new_default_gen_resolution not in valid_resolutions_for_preset:
                        messagebox.showerror(_("Invalid Selection"),
                                             _("The selected resolution '{res}' is not valid for preset '{preset}'.").format(
                                                 res=new_default_gen_resolution, preset=new_default_gen_preset),
                                             parent=dialog)
                        return
                else:  # Kein Preset gewählt, also sollte auch die Auflösung leer sein
                    new_default_gen_resolution = ""

                self.default_gen_image_width = new_width
                self.default_gen_image_height = new_height
                self.default_gen_preset_from_config = new_default_gen_preset
                self.default_gen_resolution_name_from_config = new_default_gen_resolution

                save_config(
                    self.image_output_dir, self.pattern_output_dir,
                    self.default_gen_image_width, self.default_gen_image_height,
                    self.current_theme_name,
                    self.current_language_code,
                    self.default_gen_preset_from_config,      # Neuer Parameter
                    self.default_gen_resolution_name_from_config # Neuer Parameter
                )
                self.status_label.config(text=_("Default image size saved."))
                dialog.destroy()
            except ValueError:
                messagebox.showerror(_("Invalid Input"), _("Width and height must be numbers."), parent=dialog)

        qbist_ui_components.populate_default_image_size_dialog_widgets(self, frame, default_gen_preset_var, default_gen_resolution_var,
            save_command=on_save_size_config,
            cancel_command=dialog.destroy
        )
        dialog.wait_window()

    def _configure_theme_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title(_(qbist_ui_components.UI_DIALOG_TITLE_SELECT_THEME))
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)
        style = tb.Style() # ttkbootstrap style
        original_theme = style.theme_use() # Get current theme
        available_themes = sorted(style.theme_names())
        theme_var = tk.StringVar(value=original_theme)

        def apply_theme():
            selected_theme = theme_var.get()
            if selected_theme and selected_theme != style.theme_use():
                try:
                    style.theme_use(selected_theme)
                    self.current_theme_name = selected_theme # Temporarily for view
                except tk.TclError as e:
                    messagebox.showerror(_("Theme Error"), _("Could not load theme '{theme}': {error}").format(theme=selected_theme, error=e), parent=dialog)

        def save_and_close():
            selected_theme = theme_var.get()
            if selected_theme:
                try:
                    style.theme_use(selected_theme) # Sicherstellen, dass es angewendet ist
                except tk.TclError:
                    # Fehler wurde bereits in apply_theme behandelt oder Theme ist schon aktiv
                    pass
                self.current_theme_name = selected_theme
                save_config(
                    self.image_output_dir, 
                    self.pattern_output_dir,
                    self.default_gen_image_width, self.default_gen_image_height,
                    self.current_theme_name,
                    self.current_language_code,
                    self.default_gen_preset_from_config,
                    self.default_gen_resolution_name_from_config
                )
                self.status_label.config(text=_("Theme '{theme}' saved.").format(theme=selected_theme))
            dialog.destroy()

        def cancel_and_close():
            if style.theme_use() != original_theme:
                style.theme_use(original_theme) # Restore original theme
                self.current_theme_name = original_theme

            dialog.destroy()

        qbist_ui_components.populate_theme_dialog_widgets(
            frame, theme_var, available_themes,
            apply_command=apply_theme,
            save_command=save_and_close,
            cancel_command=cancel_and_close
        )
        dialog.wait_window()

    def _save_pattern_for_generated_image(self, pattern_filepath):
        """Speichert die aktuelle Pattern-Definition für ein generiertes Bild."""
        if qbist_core.save_qbe_data(pattern_filepath, self.main_info):
            print(f"Pattern für generiertes Bild gespeichert: {pattern_filepath}") # Für Debugging
            return True
        else:
            messagebox.showerror(
                _("Pattern Speicherfehler"), # UI_DIALOG_TITLE_PATTERN_SAVE_ERROR
                _("Bild wurde generiert, aber das zugehörige Pattern konnte nicht unter {path} gespeichert werden.").format(path=pattern_filepath), # UI_MSG_PATTERN_SAVE_ERROR_FOR_IMAGE
                parent=self.master
            )
            return False

    def _threaded_generate_and_save(self, filepath, img_width, img_height, oversampling_val):
        """Führt die Bildgenerierung und das Speichern in einem separaten Thread aus."""
        try:
            pixel_bytes = qbist_core.generate_image_data(self.main_info, img_width, img_height, oversampling=oversampling_val)
            pil_image = Image.frombytes("RGBA", (img_width, img_height), pixel_bytes)
            pil_image.save(filepath) # Bild speichern

            # Bild erfolgreich gespeichert, jetzt Pattern speichern
            # Basisname des Bildes extrahieren und Pattern-Dateinamen erstellen
            image_filename_base, _img_ext = os.path.splitext(os.path.basename(filepath))
            pattern_filename = image_filename_base + ".qbe"
            pattern_filepath = os.path.join(self.pattern_output_dir, pattern_filename)
            os.makedirs(self.pattern_output_dir, exist_ok=True) # Stelle sicher, dass das Pattern-Verzeichnis existiert

            # Pattern-Speicherung und finale Nachrichten im Hauptthread planen
            def finalize_generation_and_saving():
                pattern_saved_successfully = self._save_pattern_for_generated_image(pattern_filepath)
                
                image_filename = os.path.basename(filepath)
                pattern_filename = os.path.basename(pattern_filepath)

                if pattern_saved_successfully:
                    final_status_message = _("Bild '{img_name}' und Pattern '{pat_name}' gespeichert.").format(
                        img_name=image_filename, pat_name=pattern_filename
                    ) # UI_STATUS_IMAGE_AND_PATTERN_SAVED
                    messagebox.showinfo(
                        _("Generierung erfolgreich"), # UI_DIALOG_TITLE_GENERATION_SUCCESSFUL
                        _("Bild gespeichert als: {img_path}\nPattern gespeichert als: {pat_path}").format(
                            img_path=filepath, pat_path=pattern_filepath
                        ), # UI_MSG_IMAGE_AND_PATTERN_SAVED_PATHS
                        parent=self.master
                    )
                else: # Pattern-Speicherung fehlgeschlagen, Bild wurde aber gespeichert
                    final_status_message = _("Bild '{img_name}' gespeichert. Pattern-Speicherung fehlgeschlagen.").format(img_name=image_filename) # UI_STATUS_IMAGE_SAVED_PATTERN_FAILED
                    # Fehlermeldung für Pattern wurde bereits von _save_pattern_for_generated_image angezeigt
                    # Zeige trotzdem eine Erfolgsmeldung für das Bild
                    messagebox.showinfo(
                         _("Bild generiert"), # UI_DIALOG_TITLE_IMAGE_GENERATED (kann gleich bleiben)
                         _("Bild gespeichert als: {path}").format(path=filepath), # UI_MSG_IMAGE_SAVED (kann gleich bleiben)
                         parent=self.master
                    )
                self._enable_ui_after_long_op(final_status_message)

            self.master.after(0, finalize_generation_and_saving)

        except Exception as e:
            # UI-Updates im Hauptthread planen
            self.master.after(0, lambda: self._enable_ui_after_long_op(_("Error during image generation.")))
            self.master.after(0, lambda: messagebox.showerror(_("Bildgenerierungsfehler"), _("Fehler beim Generieren oder Speichern des Bildes: {error}").format(error=e), parent=self.master)) # UI_DIALOG_TITLE_IMAGE_GENERATION_ERROR, UI_MSG_IMAGE_GENERATION_ERROR

    def _generate_full_image(self):
        dialog = tk.Toplevel(self.master)
        dialog.title(_(qbist_ui_components.UI_DIALOG_TITLE_GENERATE_IMAGE))
        dialog.transient(self.master) # Keep dialog on top of main window
        dialog.grab_set() # Modal
        dialog.resizable(False, False)

        dialog_frame = ttk.Frame(dialog, padding="10") # Use a frame for consistent padding
        dialog_frame.pack(expand=True, fill=tk.BOTH)

        preset_var = tk.StringVar(value=self.last_gen_preset)
        resolution_var = tk.StringVar(value=self.last_gen_resolution_name)
        orientation_var = tk.StringVar(value=self.last_gen_orientation)
        width_var = tk.StringVar(value=self.last_gen_width)
        height_var = tk.StringVar(value=self.last_gen_height)
        
        result = {"filepath": None, "width": 0, "height": 0}

        def on_ok():
            try:
                w = int(width_var.get())
                h = int(height_var.get())
                if w <= 0 or h <= 0:
                    messagebox.showerror(_("Invalid Dimensions"), _("Width and Height must be positive."), parent=dialog)
                    return

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"qbist_art_{timestamp}.png"
                
                os.makedirs(self.image_output_dir, exist_ok=True)

                filepath = filedialog.asksaveasfilename(
                    parent=dialog,
                    initialdir=self.image_output_dir,
                    defaultextension=".png",
                    filetypes=[
                        (_("PNG Image"), "*.png"), 
                        (_("JPEG Image"), "*.jpg"), 
                        (_("All Files"), "*.*")
                    ],
                    initialfile=default_filename,
                )
                if filepath:
                    result["filepath"] = filepath
                    result["width"] = w
                    result["height"] = h

                    # Zuletzt verwendete Werte speichern für die nächste Dialogöffnung
                    self.last_gen_preset = preset_var.get()
                    self.last_gen_resolution_name = resolution_var.get()
                    self.last_gen_orientation = orientation_var.get()
                    self.last_gen_width = width_var.get()
                    self.last_gen_height = height_var.get()
                    dialog.destroy()
            except ValueError:
                messagebox.showerror(_("Invalid Input"), _("Width and Height must be numbers."), parent=dialog)
        
        def on_cancel():
            dialog.destroy()

        qbist_ui_components.populate_generate_image_dialog_widgets(
            self, dialog_frame, preset_var, resolution_var, orientation_var, width_var, height_var,
            ok_command=on_ok,
            cancel_command=on_cancel
        )
        dialog.wait_window() # Wait for dialog to close

        if not result["filepath"]:
            return

        img_width, img_height = result["width"], result["height"]
        filepath = result["filepath"]
        oversampling_val = self.oversampling_var.get() # Wert vor Deaktivierung der UI holen

        self._disable_ui_for_long_op(_("Generating {w}x{h} image, please wait...").format(w=img_width, h=img_height))

        # Worker-Thread für die Bildgenerierung erstellen und starten
        thread = threading.Thread(
            target=self._threaded_generate_and_save,
            args=(filepath, img_width, img_height, oversampling_val)
        )
        thread.daemon = True  # Stellt sicher, dass der Thread mit der App beendet wird
        thread.start()
        # _enable_ui_after_long_op wird nun vom Thread über self.master.after aufgerufen

    def _show_about_dialog(self):
        dialog = tk.Toplevel(self.master)
        dialog.title(_(qbist_ui_components.UI_DIALOG_TITLE_ABOUT))
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding="10")
        frame.pack(expand=True, fill=tk.BOTH)

        text_area = tk.Text(frame, wrap=tk.WORD, height=20, width=60, relief=tk.FLAT, borderwidth=0)
        text_area.pack(padx=5, pady=5, expand=True, fill=tk.BOTH)
        qbist_ui_components.populate_about_dialog_content(text_area, self.about_content)
        ok_button = ttk.Button(frame, text=_(qbist_ui_components.UI_BTN_OK), command=dialog.destroy)
        ok_button.pack(pady=(10,0))

        dialog.wait_window()

    def _setup_tooltips(self):
        qbist_ui_components.setup_tooltips_for_app(self)

    def _populate_language_menu(self, lang_menu: tk.Menu):
        # This method is called by create_menubar in qbist_ui_components
        # The actual population logic is now in qbist_ui_components.populate_language_menu_items
        pass # Kept for structure if direct call was intended, but create_menubar handles it.

    def _retranslate_ui(self):
        qbist_ui_components.retranslate_app_ui(self)

    def _switch_language(self, lang_code: str):
        if lang_code != self.current_language_code:
            self.current_language_code = lang_code
            
            try:
                new_translation = gettext.translation(APP_NAME, localedir=LOCALE_DIR, languages=[lang_code], fallback=True)
                
                if isinstance(new_translation, gettext.NullTranslations) and lang_code != DEFAULT_LANGUAGE:
                    messagebox.showwarning(_("Language Load Warning"),
                                         _("Could not load all translations for {lang_name}. Some text may not be translated.").format(lang_name=qbist_ui_components.get_available_languages(self.LOCALE_DIR, self.DEFAULT_LANGUAGE).get(lang_code, lang_code)),
                                         parent=self.master)

                new_translation.install() 
                globals()['_'] = new_translation.gettext
                globals()['lang'] = new_translation # Update global 'lang' object if used directly

            except Exception as e:
                print(f"Error switching language to {lang_code}: {e}")
                messagebox.showerror(_("Language Error"), 
                                     _("Failed to switch language: {error}").format(error=e), parent=self.master)
                return # Abort if language loading fails critically

            save_config(self.image_output_dir, self.pattern_output_dir,
                        self.default_gen_image_width, self.default_gen_image_height,
                        self.current_theme_name, self.current_language_code,
                        self.default_gen_preset_from_config,
                        self.default_gen_resolution_name_from_config)
            
            self._retranslate_ui()
            self.language_var.set(self.current_language_code) # Update radio button selection

            lang_display_name = qbist_ui_components.get_available_languages(self.LOCALE_DIR, self.DEFAULT_LANGUAGE).get(lang_code, lang_code)
            self.status_label.config(text=_("Language changed to {lang_name}.").format(lang_name=lang_display_name))

    def _show_save_presets_info(self):
        messagebox.showinfo(_(qbist_ui_components.UI_DIALOG_TITLE_SAVE_PRESETS_INFO),
                            _(qbist_ui_components.UI_MSG_SAVE_PRESETS_INFO), parent=self.master)

if __name__ == '__main__':
    initial_config = load_config()
    # _ is now available globally from qbist_utilities
    current_theme_name = initial_config.get("theme", DEFAULT_THEME)
    
    try:
        # tb.Window is the replacement for ThemedTk or tk.Tk when using ttkbootstrap
        root = tb.Window(themename=current_theme_name)
    except tk.TclError:
        print(_("Error loading ttkbootstrap theme '{theme}'. Falling back to '{fallback_theme}'.").format(theme=current_theme_name, fallback_theme=DEFAULT_THEME))
        root = tb.Window(themename=DEFAULT_THEME)
        current_theme_name = DEFAULT_THEME # Wichtig, damit die Konfiguration konsistent bleibt
        # Speichere das Fallback-Theme in der Konfiguration, damit es beim nächsten Start geladen wird
        save_config(
            initial_config.get("image_dir", DEFAULT_IMAGE_DIR),
            initial_config.get("pattern_dir", DEFAULT_PATTERN_DIR),
            initial_config.get("default_gen_image_width", DEFAULT_GEN_IMAGE_WIDTH),
            initial_config.get("default_gen_image_height", DEFAULT_GEN_IMAGE_HEIGHT),
            current_theme_name,
            initial_config.get("language", DEFAULT_LANGUAGE),
            initial_config.get("default_gen_preset", DEFAULT_GEN_PRESET),
            initial_config.get("default_gen_resolution_name", DEFAULT_GEN_RESOLUTION_NAME)
        )
    initial_config["theme"] = current_theme_name # Stelle sicher, dass die App die korrekte Info hat

    app = QbistApp(root, initial_config)
    root.mainloop()
