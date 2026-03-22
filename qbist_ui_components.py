import tkinter as tk
from tkinter import ttk
import tkinter.font as tkFont
import ttkbootstrap as tb
from ttkbootstrap.tooltip import ToolTip
import re
import os # For _get_available_languages

# This module assumes qbist_utilities has been imported and lang.install() called,
# making _ globally available.

# --- UI String Constants (Source for _() function) ---
UI_APP_TITLE = "Python Qbist"
UI_LBL_PREVIEWS = "Previews"
UI_BTN_NEW_VARIATIONS = "New Variations"
UI_BTN_UNDO = "Undo"
UI_CHECK_ANTIALIASING = "Anti-aliasing (4x)"
UI_LBL_FILE_OPERATIONS = "File Operations"
UI_BTN_LOAD_PATTERN = "Load Pattern (.qbe)"
UI_BTN_SAVE_PATTERN = "Save Pattern (.qbe)"
UI_BTN_GENERATE_SAVE_IMAGE = "Generate & Save Image..."
UI_STATUS_WELCOME = "Welcome to Python Qbist!"
UI_STATUS_READY = "Ready."
UI_STATUS_PROCESSING = "Processing, please wait..."
UI_STATUS_UPDATING_PREVIEWS = "Updating previews..."
UI_STATUS_PREVIEWS_UPDATED = "Previews updated."
UI_STATUS_UNDO_SUCCESSFUL = "Undo successful."
UI_STATUS_NOTHING_TO_UNDO = "Nothing to undo."
UI_MENU_FILE = "File"
UI_MENU_SET_DEFAULT_IMG_SIZE = "Set Default Image Size..." # Moved to Configuration
UI_MENU_CONFIGURE_OUTPUT_DIRS = "Configure Output Directories..." # Moved to Configuration
UI_MENU_EXIT = "Exit" # Moved to Configuration
# UI_MENU_VIEW = "View" # Removed as the View menu itself is removed
UI_MENU_SELECT_THEME = "Select Theme..." # Moved to Configuration
UI_MENU_LANGUAGE = "Language" # Moved to Configuration as submenu
UI_MENU_HELP = "Help"
UI_MENU_ABOUT_QBIST = "About Qbist..."
UI_MENU_CONFIGURATION = "Configuration"

# File type descriptions
UI_FILETYPE_ALL_FILES = "All Files"
UI_FILETYPE_QBE_PATTERNS = "Qbist Pattern Files"
UI_FILETYPE_PNG_IMAGES = "PNG Image"
UI_FILETYPE_JPEG_IMAGES = "JPEG Image"

# Status messages (many were already covered by dialog titles/messages)
UI_STATUS_LOAD_FAILED = "Load failed."
UI_STATUS_SAVE_FAILED = "Save failed."
UI_STATUS_OUTPUT_DIRS_CONFIGURED = "Output directories configured."
UI_STATUS_DEFAULT_SIZE_SAVED = "Default image size saved."
UI_STATUS_THEME_SAVED = "Theme '{theme}' saved."
UI_STATUS_LANGUAGE_CHANGED = "Language changed to {lang_name}."
UI_STATUS_ERROR_IMAGE_GENERATION = "Error during image generation."
UI_STATUS_IMAGE_AND_PATTERN_SAVED = "Image '{img_name}' and Pattern '{pat_name}' saved."
UI_STATUS_IMAGE_SAVED_PATTERN_FAILED = "Image '{img_name}' saved. Pattern saving failed."
UI_STATUS_LOADING_FILENAME = "Loading {filename}..."
UI_STATUS_LOADED_FILENAME = "Loaded: {filename}"
UI_STATUS_SAVED_FILENAME = "Saved: {filename}"
UI_STATUS_GENERATING_IMAGE_W_H = "Generating {w}x{h} image, please wait..."

# Dialog Titles (some might be duplicates or can be consolidated)
UI_DIALOG_TITLE_CONFIG_OUTPUT_DIRS = "Configure Output Directories"
UI_LBL_IMAGE_OUTPUT_DIR = "Image Output Directory:"
UI_LBL_PATTERN_OUTPUT_DIR = "Pattern Output Directory:"
UI_BTN_BROWSE = "Browse..."
UI_BTN_SAVE = "Save"
UI_BTN_CANCEL = "Cancel"
UI_TITLE_SELECT_DIRECTORY = "Select Directory"
UI_DIALOG_TITLE_SET_DEFAULT_IMG_SIZE = "Set Default Image Size"
UI_LBL_DEFAULT_GEN_PRESET = "Default Generation Preset:"
UI_LBL_DEFAULT_GEN_RESOLUTION = "Default Generation Resolution:"
UI_DIALOG_TITLE_SELECT_THEME = "Select Theme"
UI_LBL_AVAILABLE_THEMES = "Available Themes:"
UI_BTN_APPLY = "Apply"
UI_BTN_SAVE_AND_CLOSE = "Save & Close"
UI_DIALOG_TITLE_GENERATE_IMAGE = "Generate Image"
UI_LBL_WIDTH = "Width:"
UI_LBL_HEIGHT = "Height:"
UI_BTN_OK = "OK"
UI_BTN_SAVE_AND_GENERATE_ACTION = "Save & Generate" # New constant for the dialog button
UI_DIALOG_TITLE_ABOUT = "About Python Qbist"
UI_DIALOG_TITLE_LOAD_ERROR = "Load Error"
UI_DIALOG_TITLE_SAVE_ERROR = "Save Error"
UI_DIALOG_TITLE_PATTERN_SAVE_ERROR = "Pattern Save Error"
UI_DIALOG_TITLE_GENERATION_SUCCESSFUL = "Generation Successful"
UI_DIALOG_TITLE_IMAGE_GENERATED = "Image Generated"
UI_DIALOG_TITLE_IMAGE_GENERATION_ERROR = "Image Generation Error"
UI_DIALOG_TITLE_LANGUAGE_ERROR = "Language Error"
UI_DIALOG_TITLE_LANGUAGE_LOAD_WARNING = "Language Load Warning"
UI_DIALOG_TITLE_THEME_ERROR = "Theme Error"
UI_DIALOG_TITLE_MISSING_PATH = "Missing Path"
UI_DIALOG_TITLE_INVALID_INPUT = "Invalid Input"
UI_DIALOG_TITLE_INVALID_SELECTION = "Invalid Selection"
UI_DIALOG_TITLE_INVALID_DIMENSIONS = "Invalid Dimensions"

# Dialog Messages (some might be duplicates or can be consolidated)
UI_LBL_PRESET = "Preset:"
UI_LBL_RESOLUTION = "Resolution:"
UI_LBL_ORIENTATION = "Orientation:"
UI_OPT_PORTRAIT = "Portrait"
UI_OPT_LANDSCAPE = "Landscape"
UI_DIALOG_TITLE_SAVE_PRESETS_INFO = "Image Presets Information"
UI_MSG_SAVE_PRESETS_INFO = "Image presets are defined in the 'config.toml' file and are not saved through this dialog. Please edit 'config.toml' to change presets."
UI_MSG_COULD_NOT_LOAD_PATTERN = "Could not load pattern from {path}."
UI_MSG_COULD_NOT_SAVE_PATTERN = "Could not save pattern to {path}."
UI_MSG_BOTH_DIRS_MUST_BE_SET = "Both directory paths must be set."
UI_MSG_WIDTH_HEIGHT_POSITIVE = "Width and height must be positive numbers."
UI_MSG_WIDTH_HEIGHT_NUMBERS = "Width and height must be numbers."
UI_MSG_SELECT_RESOLUTION_FOR_PRESET = "Please select a resolution for the chosen default preset '{preset}'."
UI_MSG_RESOLUTION_NOT_VALID_FOR_PRESET = "The selected resolution '{res}' is not valid for preset '{preset}'."
UI_MSG_COULD_NOT_LOAD_THEME = "Could not load theme '{theme}': {error}."
UI_MSG_PATTERN_SAVE_ERROR_FOR_IMAGE = "Image was generated, but the associated pattern could not be saved to {path}."
UI_MSG_IMAGE_AND_PATTERN_SAVED_PATHS = "Image saved as: {img_path}\nPattern saved as: {pat_path}"
UI_MSG_IMAGE_SAVED = "Image saved as: {path}"
UI_MSG_FAILED_TO_GENERATE_OR_SAVE_IMAGE = "Failed to generate or save image: {error}."
UI_MSG_DIMENSIONS_POSITIVE = "Width and Height must be positive."
UI_MSG_FAILED_TO_SWITCH_LANGUAGE = "Failed to switch language: {error}."
UI_MSG_COULD_NOT_LOAD_ALL_TRANSLATIONS = "Could not load all translations for {lang_name}. Some text may not be translated."
UI_MSG_ERROR_LOADING_THEME_FALLBACK = "Error loading ttkbootstrap theme '{theme}'. Falling back to '{fallback_theme}'."

# --- Tooltip String Constants ---
UI_TOOLTIP_NEW_VARIATIONS = "Generate new pattern variations based on the center image."
UI_TOOLTIP_UNDO = "Undo the last selection of a new main pattern."
UI_TOOLTIP_ANTIALIASING = "Enable 4x oversampling for smoother images (slower generation)."
UI_TOOLTIP_LOAD_PATTERN = "Load a Qbist pattern from a .qbe file."
UI_TOOLTIP_SAVE_PATTERN = "Save the current main pattern to a .qbe file."
UI_TOOLTIP_GENERATE_SAVE_IMAGE = "Generate a full-size image from the current main pattern and save it."
UI_TOOLTIP_PREVIEW_CANVAS = "Click to select this pattern as the main pattern."
UI_TOOLTIP_CENTER_CANVAS = "Click to generate new variations from this main pattern."

PREVIEW_SIZE_DEFAULT = 128

def create_main_layout(app, master_tk_instance):
    master_tk_instance.title(_(UI_APP_TITLE))
    main_frame = ttk.Frame(master_tk_instance, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    master_tk_instance.columnconfigure(0, weight=1)
    master_tk_instance.rowconfigure(0, weight=1)

    app.preview_frame_lf = ttk.LabelFrame(main_frame, text=_(UI_LBL_PREVIEWS))
    app.preview_frame_lf.grid(row=0, column=0, columnspan=3, pady=10, sticky=(tk.W, tk.E))
    app.preview_frame_lf.columnconfigure(0, weight=1)
    app.preview_frame_lf.rowconfigure(0, weight=1)

    actual_preview_grid_holder = ttk.Frame(app.preview_frame_lf)
    actual_preview_grid_holder.grid(row=0, column=0, sticky="")

    app.preview_canvases = []
    positions = [(0,0), (0,1), (0,2), (1,0), (1,1), (1,2), (2,0), (2,1), (2,2)]
    app.gui_to_variation_map = {}
    v_idx = 0
    for i in range(9):
        if i == 4: continue
        app.gui_to_variation_map[i] = v_idx
        v_idx += 1

    for i in range(9):
        row, col = positions[i]
        canvas_size = app.preview_render_size
        is_center = (i == 4)
        if is_center:
            canvas_size = int(app.preview_render_size * 1.25)
        frame_relief = "raised" if is_center else "sunken"
        frame = ttk.Frame(actual_preview_grid_holder, borderwidth=2, relief=frame_relief, width=canvas_size+4, height=canvas_size+4)
        frame.grid(row=row, column=col, padx=3, pady=3)
        frame.grid_propagate(False)
        canvas = tk.Canvas(frame, width=canvas_size, height=canvas_size, bg="lightgrey", highlightthickness=0)
        canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        if is_center:
            canvas.bind("<Button-1>", lambda e: app._on_center_preview_click())
        else:
            canvas.bind("<Button-1>", lambda e, gui_idx=i: app._on_variation_preview_click(gui_idx))
        app.preview_canvases.append(canvas)

    controls_frame = ttk.Frame(main_frame)
    controls_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=tk.EW)
    app.new_variations_button = ttk.Button(controls_frame, text=_(UI_BTN_NEW_VARIATIONS), command=app._generate_new_variations_from_main)
    app.new_variations_button.pack(side=tk.LEFT, padx=5)
    app.undo_button = ttk.Button(controls_frame, text=_(UI_BTN_UNDO), command=app._undo_selection)
    app.undo_button.pack(side=tk.LEFT, padx=5)
    app.aa_check = ttk.Checkbutton(controls_frame, text=_(UI_CHECK_ANTIALIASING), variable=app.oversampling_var, onvalue=4, offvalue=1)
    app.aa_check.pack(side=tk.LEFT, padx=15)

    app.file_ops_frame = ttk.LabelFrame(main_frame, text=_(UI_LBL_FILE_OPERATIONS))
    app.file_ops_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky=tk.EW)
    app.load_pattern_button = ttk.Button(app.file_ops_frame, text=_(UI_BTN_LOAD_PATTERN), command=app._load_pattern)
    app.load_pattern_button.pack(side=tk.LEFT, padx=5, pady=5)
    app.save_pattern_button = ttk.Button(app.file_ops_frame, text=_(UI_BTN_SAVE_PATTERN), command=app._save_pattern)
    app.save_pattern_button.pack(side=tk.LEFT, padx=5, pady=5)
    app.generate_image_button = ttk.Button(app.file_ops_frame, text=_(UI_BTN_GENERATE_SAVE_IMAGE), command=app._generate_full_image)
    app.generate_image_button.pack(side=tk.LEFT, padx=5, pady=5)

    app.status_label = ttk.Label(main_frame, text=_(UI_STATUS_WELCOME))
    app.status_label.grid(row=3, column=0, columnspan=3, pady=(10,0), sticky=tk.W)
    app.progressbar = ttk.Progressbar(main_frame, mode='indeterminate', length=200)

    app.interactive_widgets_for_long_ops = [
        app.new_variations_button, app.undo_button, app.load_pattern_button,
        app.save_pattern_button, app.generate_image_button
    ]
    app.interactive_widgets_for_long_ops.extend(app.preview_canvases)

def create_menubar(app, master_tk_instance):
    app.menubar = tk.Menu(master_tk_instance)

    # File menu is removed. Exit is moved to Configuration.
    # Language menu as top-level is removed. It's now a submenu in Configuration.

    app.configmenu = tk.Menu(app.menubar, tearoff=0) # Configuration menu
    app.configmenu.add_command(label=_(UI_MENU_SET_DEFAULT_IMG_SIZE), command=app._configure_default_image_size)
    app.configmenu.add_command(label=_(UI_MENU_CONFIGURE_OUTPUT_DIRS), command=app._configure_output_directories)
    app.configmenu.add_command(label=_(UI_MENU_SELECT_THEME), command=app._configure_theme_dialog) # Moved from View

    # Language submenu within Configuration
    app.config_langmenu = tk.Menu(app.configmenu, tearoff=0)
    populate_language_menu_items(app, app.config_langmenu) # Populate the submenu
    app.configmenu.add_cascade(label=_(UI_MENU_LANGUAGE), menu=app.config_langmenu)

    app.configmenu.add_separator()
    app.configmenu.add_command(label=_(UI_MENU_EXIT), command=master_tk_instance.quit) # Moved from File

    # Add Configuration menu to menubar (first position)
    app.menubar.add_cascade(label=_(UI_MENU_CONFIGURATION), menu=app.configmenu)

    # Help menu (second position)
    app.helpmenu = tk.Menu(app.menubar, tearoff=0)
    app.helpmenu.add_command(label=_(UI_MENU_ABOUT_QBIST), command=app._show_about_dialog)
    app.menubar.add_cascade(label=_(UI_MENU_HELP), menu=app.helpmenu)

    master_tk_instance.config(menu=app.menubar)

def populate_output_directories_dialog_widgets(parent_frame, img_dir_var, pat_dir_var, browse_img_command, browse_pat_command, save_command, cancel_command):
    ttk.Label(parent_frame, text=_(UI_LBL_IMAGE_OUTPUT_DIR)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(parent_frame, textvariable=img_dir_var, width=50).grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
    ttk.Button(parent_frame, text=_(UI_BTN_BROWSE), command=browse_img_command).grid(row=0, column=2, padx=5, pady=5)
    ttk.Label(parent_frame, text=_(UI_LBL_PATTERN_OUTPUT_DIR)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    ttk.Entry(parent_frame, textvariable=pat_dir_var, width=50).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
    ttk.Button(parent_frame, text=_(UI_BTN_BROWSE), command=browse_pat_command).grid(row=1, column=2, padx=5, pady=5)
    parent_frame.columnconfigure(1, weight=1)
    button_frame = ttk.Frame(parent_frame)
    button_frame.grid(row=2, column=0, columnspan=3, pady=10)
    ttk.Button(button_frame, text=_(UI_BTN_SAVE), command=save_command).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text=_(UI_BTN_CANCEL), command=cancel_command).pack(side=tk.LEFT, padx=5)

def populate_default_image_size_dialog_widgets(
    app,  # Benötigt für den Zugriff auf app.image_presets
    parent_frame,
    default_gen_preset_var, default_gen_resolution_var,  # Neue StringVars
    save_command, cancel_command
):
    # Standard-Generierungs-Preset
    ttk.Label(parent_frame, text=_(UI_LBL_DEFAULT_GEN_PRESET)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W) # Start at row 0
    preset_combo = ttk.Combobox(parent_frame, textvariable=default_gen_preset_var, state="readonly", width=30)
    preset_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
    preset_combo['values'] = [""] + list(app.image_presets.keys())  # Leere Option hinzufügen

    # Standard-Generierungs-Auflösung
    ttk.Label(parent_frame, text=_(UI_LBL_DEFAULT_GEN_RESOLUTION)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W) # Now row 1
    resolution_combo = ttk.Combobox(parent_frame, textvariable=default_gen_resolution_var, state="readonly", width=30)
    resolution_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

    parent_frame.columnconfigure(1, weight=1) # Erlaube Comboboxen sich auszudehnen

    def _on_default_gen_preset_selected(event=None):
        selected_key = default_gen_preset_var.get()
        resolution_combo['values'] = []  # Vorherige Werte löschen

        if selected_key:
            resolutions = app.image_presets.get(selected_key, [])
            resolution_names = [res["name"] for res in resolutions]
            resolution_combo['values'] = resolution_names
            current_res_val = default_gen_resolution_var.get()
            if current_res_val and current_res_val in resolution_names:
                pass  # Aktuelle Auflösung beibehalten, wenn gültig
            elif resolution_names:
                default_gen_resolution_var.set(resolution_names[0]) # Erste verfügbare Auflösung wählen
            else:
                default_gen_resolution_var.set("") # Keine Auflösungen für dieses Preset
        else:  # Kein Preset ausgewählt
            default_gen_resolution_var.set("")

    preset_combo.bind("<<ComboboxSelected>>", _on_default_gen_preset_selected)
    _on_default_gen_preset_selected() # Initiale Befüllung der Auflösungs-Combobox

    button_frame = ttk.Frame(parent_frame)
    button_frame.grid(row=2, column=0, columnspan=2, pady=10)  # Zeile angepasst (was row 4)
    ttk.Button(button_frame, text=_(UI_BTN_SAVE), command=save_command).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text=_(UI_BTN_CANCEL), command=cancel_command).pack(side=tk.LEFT, padx=5)

def populate_theme_dialog_widgets(parent_frame, theme_var, available_themes, apply_command, save_command, cancel_command):
    ttk.Label(parent_frame, text=_(UI_LBL_AVAILABLE_THEMES)).pack(pady=(0,5))
    theme_combo = ttk.Combobox(parent_frame, textvariable=theme_var, values=available_themes, state="readonly", width=30)
    theme_combo.pack(pady=5)
    button_frame = ttk.Frame(parent_frame)
    button_frame.pack(pady=10)
    ttk.Button(button_frame, text=_(UI_BTN_APPLY), command=apply_command).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text=_(UI_BTN_SAVE_AND_CLOSE), command=save_command).pack(side=tk.LEFT, padx=5)
    ttk.Button(button_frame, text=_(UI_BTN_CANCEL), command=cancel_command).pack(side=tk.LEFT, padx=5)

def populate_generate_image_dialog_widgets(app, parent_dialog_frame, preset_var, resolution_var, orientation_var, width_var, height_var, ok_command, cancel_command):
    ttk.Label(parent_dialog_frame, text=_(UI_LBL_PRESET)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
    preset_combo = ttk.Combobox(parent_dialog_frame, textvariable=preset_var, state="readonly", width=25)
    preset_combo.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
    preset_combo['values'] = [""] + list(app.image_presets.keys())
    ttk.Label(parent_dialog_frame, text=_(UI_LBL_RESOLUTION)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
    resolution_combo = ttk.Combobox(parent_dialog_frame, textvariable=resolution_var, state="readonly", width=25)
    resolution_combo.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky=tk.EW)
    ttk.Label(parent_dialog_frame, text=_(UI_LBL_ORIENTATION)).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
    orientation_frame = ttk.Frame(parent_dialog_frame)
    orientation_frame.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky=tk.W)
    portrait_rb = ttk.Radiobutton(orientation_frame, text=_(UI_OPT_PORTRAIT), variable=orientation_var, value="P")
    portrait_rb.pack(side=tk.LEFT, padx=(0, 5))
    landscape_rb = ttk.Radiobutton(orientation_frame, text=_(UI_OPT_LANDSCAPE), variable=orientation_var, value="L")
    landscape_rb.pack(side=tk.LEFT)
    orientation_var.set("P")
    ttk.Label(parent_dialog_frame, text=_(UI_LBL_WIDTH)).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
    width_entry = ttk.Entry(parent_dialog_frame, textvariable=width_var, width=10)
    width_entry.grid(row=3, column=1, padx=5, pady=5, sticky=tk.W)
    ttk.Label(parent_dialog_frame, text=_(UI_LBL_HEIGHT)).grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
    height_entry = ttk.Entry(parent_dialog_frame, textvariable=height_var, width=10)
    height_entry.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W)
    parent_dialog_frame.columnconfigure(1, weight=1)

    def _update_dimensions_from_preset():
        selected_preset_key = preset_var.get()
        selected_resolution_name = resolution_var.get()
        orient = orientation_var.get()
        if selected_preset_key and selected_resolution_name:
            preset_details = app.image_presets.get(selected_preset_key, [])
            for res_detail in preset_details:
                if res_detail["name"] == selected_resolution_name:
                    base_w, base_h = res_detail["width"], res_detail["height"]
                    supports_orientation = res_detail.get("supports_orientation_change", False)
                    if supports_orientation and orient == "L": width_var.set(str(base_h)); height_var.set(str(base_w))
                    else: width_var.set(str(base_w)); height_var.set(str(base_h))
                    return

    def _on_resolution_selected(event=None): # Added missing function definition
        _update_dimensions_from_preset()

    def _on_preset_selected(event=None):
        selected_key = preset_var.get()
        resolution_combo['values'] = []
        resolution_var.set("")
        orientation_supported = False
        if selected_key:
            resolutions = app.image_presets.get(selected_key, [])
            if resolutions and resolutions[0].get("supports_orientation_change", False): orientation_supported = True
        for widget in orientation_frame.winfo_children(): widget.config(state=tk.NORMAL if orientation_supported else tk.DISABLED)
        if not orientation_supported: orientation_var.set("P")
        if selected_key:
            resolutions = app.image_presets.get(selected_key, [])
            resolution_names = [res["name"] for res in resolutions]
            current_resolution_val = resolution_var.get() # Aktuellen Wert holen
            resolution_combo['values'] = resolution_names
            if resolution_names:
                if not current_resolution_val or current_resolution_val not in resolution_names:
                    resolution_var.set(resolution_names[0]) # Nur setzen, wenn aktuell keiner oder ungültig
        _update_dimensions_from_preset()
    def _on_manual_dimension_input(event=None):
        preset_var.set(""); resolution_var.set(""); resolution_combo['values'] = []
        for widget in orientation_frame.winfo_children(): widget.config(state=tk.DISABLED)
        orientation_var.set("P")

    preset_combo.bind("<<ComboboxSelected>>", _on_preset_selected)
    resolution_combo.bind("<<ComboboxSelected>>", _on_resolution_selected)
    portrait_rb.config(command=_update_dimensions_from_preset) # Use common update
    landscape_rb.config(command=_update_dimensions_from_preset) # Use common update
    width_entry.bind("<KeyRelease>", _on_manual_dimension_input)
    height_entry.bind("<KeyRelease>", _on_manual_dimension_input)
    _on_preset_selected()

    ok_button = ttk.Button(parent_dialog_frame, text=_(UI_BTN_SAVE_AND_GENERATE_ACTION), command=ok_command)
    ok_button.grid(row=5, column=0, padx=5, pady=10, sticky=tk.W)
    cancel_button = ttk.Button(parent_dialog_frame, text=_(UI_BTN_CANCEL), command=cancel_command)
    cancel_button.grid(row=5, column=1, padx=5, pady=10, sticky=tk.E)
    
def populate_about_dialog_content(text_area_widget, about_content_markdown):
    try:
        default_font_obj = tkFont.nametofont(text_area_widget.cget("font"))
        h1_font = tkFont.Font(font=default_font_obj); h1_font.configure(size=int(default_font_obj.cget("size") * 1.5), weight="bold")
        text_area_widget.tag_configure("h1", font=h1_font, spacing3=10)
        bold_font = tkFont.Font(font=default_font_obj); bold_font.configure(weight="bold")
        text_area_widget.tag_configure("bold", font=bold_font)
    except tk.TclError:
        text_area_widget.tag_configure("h1", font=("TkDefaultFont", 16, "bold"), spacing3=10)
        text_area_widget.tag_configure("bold", font=("TkDefaultFont", 10, "bold"))

    for line_content in about_content_markdown.splitlines():
        if line_content.startswith("# "):
            text_area_widget.insert(tk.END, line_content[2:] + "\n", "h1")
        else:
            current_pos = 0
            for match in re.finditer(r"\*\*(.*?)\*\*", line_content):
                text_area_widget.insert(tk.END, line_content[current_pos:match.start()])
                text_area_widget.insert(tk.END, match.group(1), "bold")
                current_pos = match.end()
            text_area_widget.insert(tk.END, line_content[current_pos:] + "\n")
    text_area_widget.config(state=tk.DISABLED)

def setup_tooltips_for_app(app):
    app.tooltip_new_var = ToolTip(app.new_variations_button, text=_(UI_TOOLTIP_NEW_VARIATIONS), bootstyle="info")
    app.tooltip_undo = ToolTip(app.undo_button, text=_(UI_TOOLTIP_UNDO), bootstyle="info")
    app.tooltip_aa = ToolTip(app.aa_check, text=_(UI_TOOLTIP_ANTIALIASING), bootstyle="info")
    app.tooltip_load_pattern = ToolTip(app.load_pattern_button, text=_(UI_TOOLTIP_LOAD_PATTERN), bootstyle="info")
    app.tooltip_save_pattern = ToolTip(app.save_pattern_button, text=_(UI_TOOLTIP_SAVE_PATTERN), bootstyle="info")
    app.tooltip_gen_save_img = ToolTip(app.generate_image_button, text=_(UI_TOOLTIP_GENERATE_SAVE_IMAGE), bootstyle="info")
    app.tooltip_previews = [None] * 9
    for i, canvas in enumerate(app.preview_canvases):
        tooltip_text = _(UI_TOOLTIP_CENTER_CANVAS) if i == 4 else _(UI_TOOLTIP_PREVIEW_CANVAS)
        try: app.tooltip_previews[i] = ToolTip(canvas, text=tooltip_text, bootstyle="info")
        except Exception: pass # Ignore if tooltip fails for canvas

def get_available_languages(locale_dir_ref, default_lang_code):
    langs = {}
    if os.path.isdir(locale_dir_ref):
        for item in os.listdir(locale_dir_ref):
            if os.path.isdir(os.path.join(locale_dir_ref, item)):
                if item == "en": langs[item] = "English"
                elif item == "de": langs[item] = "Deutsch"
                else: langs[item] = item
    if not langs: langs[default_lang_code] = "English" # Fallback
    return langs

def populate_language_menu_items(app, lang_menu_widget):
    # Uses app.current_language_code, app.LOCALE_DIR, app.DEFAULT_LANGUAGE, app._switch_language
    available_langs = get_available_languages(app.LOCALE_DIR, app.DEFAULT_LANGUAGE)
    app.language_var = tk.StringVar(value=app.current_language_code)
    for code, name in available_langs.items():
        lang_menu_widget.add_radiobutton(label=name, variable=app.language_var, value=code,
                                         command=lambda c=code: app._switch_language(c))

def retranslate_app_ui(app):
    app.master.title(_(UI_APP_TITLE))
    app.preview_frame_lf.config(text=_(UI_LBL_PREVIEWS))
    app.file_ops_frame.config(text=_(UI_LBL_FILE_OPERATIONS))
    app.new_variations_button.config(text=_(UI_BTN_NEW_VARIATIONS))
    app.undo_button.config(text=_(UI_BTN_UNDO))
    app.load_pattern_button.config(text=_(UI_BTN_LOAD_PATTERN))
    app.save_pattern_button.config(text=_(UI_BTN_SAVE_PATTERN))
    app.generate_image_button.config(text=_(UI_BTN_GENERATE_SAVE_IMAGE))
    app.aa_check.config(text=_(UI_CHECK_ANTIALIASING))

    # New Order: Configuration, Help
    app.menubar.entryconfigure(0, label=_(UI_MENU_CONFIGURATION)) # Configuration
    app.menubar.entryconfigure(1, label=_(UI_MENU_HELP))       # Help

    # File menu and top-level Language menu are removed, so no entryconfigure for them.

    app.helpmenu.entryconfigure(0, label=_(UI_MENU_ABOUT_QBIST))

    # Configuration menu items
    app.configmenu.entryconfigure(0, label=_(UI_MENU_SET_DEFAULT_IMG_SIZE))
    app.configmenu.entryconfigure(1, label=_(UI_MENU_CONFIGURE_OUTPUT_DIRS))
    app.configmenu.entryconfigure(2, label=_(UI_MENU_SELECT_THEME))
    app.configmenu.entryconfigure(3, label=_(UI_MENU_LANGUAGE)) # Cascade label for language submenu
    app.configmenu.entryconfigure(5, label=_(UI_MENU_EXIT)) # Index after separator

    setup_tooltips_for_app(app) # Update tooltips with new language
    app.master.update_idletasks()