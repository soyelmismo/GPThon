chat_models: dict[str, list] = dict()
chat_models_txt = str()
embed_models: dict[str, list] = dict()
embed_models_txt = str()
img_models: dict[str, list] = dict()
img_models_txt = str()
whisper_models: dict[str, list] = dict()


speech_models: dict[dict[str, list]] = dict()
speech_voices: dict[str, str] = dict()
speech_voices_txt = str()

not_yet_ready = 1

img_styles: dict[str, str] = dict()
img_styles_txt = str()
styles_str: str = str()

session_default_chat_model = str()
session_default_img_model = str()
session_default_tts_model = str()


ERRFUNC = "Error retrieving function."
FUNCNOARG = "Search arguments not found. Ask the user what he want to search."

tools_loaded = []

colors = {
    'r': '\033[0m',        # Reset (elimina los colores)
    'b': '\033[1m',         # Texto en negrita
    'u': '\033[4m',    # Texto subrayado
    'black': '\033[30m',       # Negro
    'red': '\033[31m',         # Rojo
    'green': '\033[32m',       # Verde
    'yellow': '\033[33m',      # Amarillo
    'blue': '\033[34m',        # Azul
    'magenta': '\033[35m',     # Magenta
    'cyan': '\033[36m',        # Cyan
    'white': '\033[37m',       # Blanco
    'orange': '\033[38;5;208m',              # Naranja
    'bright_orange': '\033[38;5;216m',        # Naranja claro
    'bright_black': '\033[90m',       # Negro claro
    'bright_red': '\033[91m',         # Rojo claro
    'bright_green': '\033[92m',       # Verde claro
    'bright_yellow': '\033[93m',      # Amarillo claro
    'bright_blue': '\033[94m',        # Azul claro
    'bright_magenta': '\033[95m',     # Magenta claro
    'bright_cyan': '\033[96m',        # Cyan claro
    'bright_white': '\033[97m',       # Blanco claro
    'bg_black': '\033[40m',    # Fondo Negro
    'bg_red': '\033[41m',      # Fondo Rojo
    'bg_green': '\033[42m',    # Fondo Verde
    'bg_yellow': '\033[43m',   # Fondo Amarillo
    'bg_blue': '\033[44m',     # Fondo Azul
    'bg_magenta': '\033[45m',  # Fondo Magenta
    'bg_cyan': '\033[46m',     # Fondo Cyan
    'bg_white': '\033[47m',    # Fondo Blanco
    'bg_bright_black': '\033[100m',    # Fondo Negro claro
    'bg_bright_red': '\033[101m',      # Fondo Rojo claro
    'bg_bright_green': '\033[102m',    # Fondo Verde claro
    'bg_bright_yellow': '\033[103m',   # Fondo Amarillo claro
    'bg_bright_blue': '\033[104m',     # Fondo Azul claro
    'bg_bright_magenta': '\033[105m',  # Fondo Magenta claro
    'bg_bright_cyan': '\033[106m',     # Fondo Cyan claro
    'bg_bright_white': '\033[107m'     # Fondo Blanco claro
}

print("\n\nCOLORS!\n")
for color in colors.keys():
    print(f"{colors[color]}{color} ◀ ◁ ◂ ◃ ◄ ◅ ◆ ◇ ◈ ◉ ◊ ○ ◌ ◍ ◎ ●{colors["r"]}")
print("\n\n")