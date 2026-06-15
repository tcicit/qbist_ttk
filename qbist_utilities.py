import os
import toml
import gettext
import locale

# --- Global Constants for Utilities ---
CONFIG_FILE_PATH = "config.toml"
DEFAULT_IMAGE_DIR = os.path.join(os.getcwd(), "qbist_images")
DEFAULT_PATTERN_DIR = os.path.join(os.getcwd(), "qbist_patterns")
ABOUT_FILE_PATH = "about.md"

APP_NAME = "qbist_app"
LOCALE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'locale')
DEFAULT_LANGUAGE = "en"

DEFAULT_GEN_IMAGE_WIDTH = 1024
DEFAULT_GEN_IMAGE_HEIGHT = 1024
DEFAULT_THEME = "darkly"
DEFAULT_GEN_PRESET = ""  # Standard-Preset für den Generierungsdialog
DEFAULT_GEN_RESOLUTION_NAME = ""  # Standard-Auflösungsname für den Generierungsdialog
DEFAULT_IMAGE_PRESETS = {
    "1:1 (Square)": [
        {"name": "Small (512x512)", "width": 512, "height": 512},
        {"name": "Medium (1024x1024)", "width": 1024, "height": 1024},
        {"name": "Large (2048x2048)", "width": 2048, "height": 2048},
        {"name": "4K (4096x4096)", "width": 4096, "height": 4096},
        {"name": "8K (8192x8192)", "width": 8192, "height": 8192},  
    ],
    "16:9 (Widescreen)": [
        {"name": "HD (1280x720)", "width": 1280, "height": 720},
        {"name": "Full HD (1920x1080)", "width": 1920, "height": 1080},
        {"name": "4K (3840x2160)", "width": 3840, "height": 2160},
        {"name": "8K (7680x4320)", "width": 7680, "height": 4320},
    ],
    "4:3 (Standard)": [
        {"name": "SVGA (800x600)", "width": 800, "height": 600},
        {"name": "XGA (1024x768)", "width": 1024, "height": 768},
        {"name": "SXGA (1280x1024)", "width": 1280, "height": 1024},
        {"name": "UXGA (1600x1200)", "width": 1600, "height": 1200},
        {"name": "WXGA (1920x1200)", "width": 1920, "height": 1200},

    ],
    "DIN A4": [
        {"name": "Print (300 DPI)", "width": 2480, "height": 3508, "supports_orientation_change": True},
        {"name": "Web (150 DPI)", "width": 1240, "height": 1754, "supports_orientation_change": True},

    ],
    "DIN A3": [
        {"name": "Print (300 DPI)", "width": 3508, "height": 4961, "supports_orientation_change": True},
        {"name": "Web (150 DPI)", "width": 1754, "height": 2480, "supports_orientation_change": True},
    ],
}

# --- Internationalization (i18n) setup ---
def get_configured_language():
    """Tries to load the language from config.toml first."""
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        return config.get('ui', {}).get('language', None)
    except (FileNotFoundError, toml.TomlDecodeError):
        return None

try:
    preferred_lang = get_configured_language()
    languages_to_try = []
    if preferred_lang:
        languages_to_try.append(preferred_lang)
    try:
        system_lang_code, _ = locale.getlocale(locale.LC_CTYPE)
        if system_lang_code:
            languages_to_try.append(system_lang_code)
            if '_' in system_lang_code:
                languages_to_try.append(system_lang_code.split('_')[0])
    except Exception:
        pass # Ignore errors from locale.getlocale
    languages_to_try.append(DEFAULT_LANGUAGE)

    lang = gettext.translation(APP_NAME, localedir=LOCALE_DIR, languages=languages_to_try, fallback=True)
except Exception: # Catch-all for safety during initial setup
    lang = gettext.NullTranslations()

lang.install() # Makes _ available in builtins
_ = lang.gettext
# --- End i18n setup ---

def load_config():
    config = {} # Initialize to empty, so defaults apply if loading fails
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        print(f"INFO: Configuration successfully loaded from '{CONFIG_FILE_PATH}'.")
    except FileNotFoundError:
        print(f"WARNING: Configuration file '{CONFIG_FILE_PATH}' not found. Using default values and attempting to create a new config file on next save.")
        # config remains {}, a new file might be created by save_config if needed
    except toml.TomlDecodeError as e:
        print(f"ERROR: Could not decode '{CONFIG_FILE_PATH}'. Invalid TOML syntax: {e}. Using default values.")
        # config remains {}
    except Exception as e:
        print(f"ERROR: Unexpected error loading configuration from '{CONFIG_FILE_PATH}': {e}. Using default values.")
        # config remains {}

    # Normalize presets into a mapping of preset_name -> list of resolution dicts
    raw_presets = config.get('presets', DEFAULT_IMAGE_PRESETS)
    normalized_presets = {}
    try:
        if isinstance(raw_presets, dict):
            for key, val in raw_presets.items():
                # Ensure key is a string and value is a list of dicts
                preset_key = str(key)
                if isinstance(val, list):
                    normalized_presets[preset_key] = val
                elif isinstance(val, dict):
                    normalized_presets[preset_key] = [val]
                else:
                    # Unknown structure: skip
                    continue
        else:
            # If the structure is unexpected (e.g. a list), fall back to defaults
            normalized_presets = DEFAULT_IMAGE_PRESETS
    except Exception:
        normalized_presets = DEFAULT_IMAGE_PRESETS

    return {
        "image_dir": config.get('paths', {}).get('image_dir', DEFAULT_IMAGE_DIR),
        "pattern_dir": config.get('paths', {}).get('pattern_dir', DEFAULT_PATTERN_DIR),
        "default_gen_image_width": config.get('defaults', {}).get('image_width', DEFAULT_GEN_IMAGE_WIDTH),
        "default_gen_image_height": config.get('defaults', {}).get('image_height', DEFAULT_GEN_IMAGE_HEIGHT),
        "theme": config.get('ui', {}).get('theme', DEFAULT_THEME),
        "language": config.get('ui', {}).get('language', get_configured_language() or DEFAULT_LANGUAGE),
        "image_presets": normalized_presets,
        "default_gen_preset": config.get('defaults', {}).get('gen_preset', DEFAULT_GEN_PRESET),
        "default_gen_resolution_name": config.get('defaults', {}).get('gen_resolution_name', DEFAULT_GEN_RESOLUTION_NAME),
    }

def save_config(image_dir, pattern_dir, default_width, default_height, theme_name, language_code,
                default_gen_preset_val, default_gen_resolution_name_val): # Neue Parameter
    current_config = {}
    try:
        with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
            current_config = toml.load(f)
        print(f"INFO: Loaded existing config for saving: '{CONFIG_FILE_PATH}'")
    except FileNotFoundError:
        print(f"INFO: '{CONFIG_FILE_PATH}' not found for saving. A new configuration file will be created.")
        # Initialize with a base structure including potentially missing sections
        current_config = {
            "paths": {},
            "defaults": {},
            "ui": {},
            "presets": DEFAULT_IMAGE_PRESETS # Add default presets if creating anew
        }
    except toml.TomlDecodeError as e:
        print(f"ERROR: Could not decode '{CONFIG_FILE_PATH}' for saving due to TOML error: {e}. Overwriting with new settings, existing structure might be lost if severely corrupted.")
        # If file is too corrupt to parse, start fresh for the parts we manage
        current_config = {"paths": {}, "defaults": {}, "ui": {}}
        # Consider adding default presets here too if strategy is to rebuild
        # current_config["presets"] = DEFAULT_IMAGE_PRESETS

    # Ensure the main sections exist using .setdefault() for conciseness
    current_config.setdefault('paths', {})
    current_config.setdefault('defaults', {})
    current_config.setdefault('ui', {})
    current_config.setdefault('presets', DEFAULT_IMAGE_PRESETS) # Ensure presets section exists

    # Aktualisiere nur die spezifischen Werte, die diese Funktion verwalten soll
    current_config['paths']['image_dir'] = image_dir
    current_config['paths']['pattern_dir'] = pattern_dir
    current_config['defaults']['image_width'] = default_width
    current_config['defaults']['image_height'] = default_height
    current_config['ui']['theme'] = theme_name
    current_config['ui']['language'] = language_code

    # Setze die neuen Standardwerte für Preset und Auflösung
    current_config['defaults']['gen_preset'] = default_gen_preset_val
    current_config['defaults']['gen_resolution_name'] = default_gen_resolution_name_val

    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            toml.dump(current_config, f)
        print(f"INFO: Configuration saved to '{CONFIG_FILE_PATH}'.")
    except Exception as e:
        print(f"ERROR: Could not write configuration to '{CONFIG_FILE_PATH}': {e}")

    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(pattern_dir, exist_ok=True)

def load_about_text():
    try:
        with open(ABOUT_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return _("About file '{path}' not found.\n\nPlease create a file named 'about.md' in the program directory.").format(path=ABOUT_FILE_PATH)
    except Exception as e:
        return _("Error loading about file '{path}': {error}").format(path=ABOUT_FILE_PATH, error=e)