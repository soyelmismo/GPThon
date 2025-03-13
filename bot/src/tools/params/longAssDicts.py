from bot.src.config import (
command_chat, command_image, command_stt
)

from io import BytesIO


img_ratios = {
    "1x1": "1024x1024",
    "16x9": "1920x1080",
    "21x9": "2560x1080",
    "3x2": "1800x1200",
    "2x3": "1200x1800",
    "4x5": "1280x1600",
    "5x4": "1600x1280",
    "9x16": "1080x1920",
    "9x21": "1080x2520"
}


all_args = {
    "all": [
        "streaming", "chat_model", "img_model", "memory", "sysprompt", "ratio",
        "temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens",
        "status", "randomizer", "seed", "download", "answer_stt", "group_mode", "random_names",
        "rol", "improve_model", "vision_model", "photos", "style_name", "improve_prompt", "improve_model",
        "stt_language", "embedding_model", "summarize", "transcribe", "tool_call", "tool_model",
        "to_tts", "tts_voice", "debug", "raw", "authorize", "deauthorize", "timeout", "forget",
        "sudo", "params_warning", "block_command" # "output_tokens"
        ],

    "/select": [
        "streaming", "memory", "randomizer", "answer_stt", "chat_model", "img_model",
        "sysprompt", "temperature", "top_p", "frequency_penalty", "presence_penalty",
        "max_tokens", "debug", "status", "seed", "download", "group_mode", "random_names",
        "summarize", "rol", "improve_model", "vision_model", "stt_language", "embedding_model",
        "transcribe", "tool_call", "tool_model", "to_tts", "tts_voice", "authorize",
        "deauthorize", "timeout", "sudo", "params_warning", "block_command" # "output_tokens"
        ],


    command_chat: [
        "streaming", "randomizer",
        "chat_model", "vision_model", "temperature", "debug", "top_p", "frequency_penalty", "presence_penalty",
        "max_tokens", "seed", "summarize", "tool_call", "to_tts", "tts_voice", "tool_model", "timeout",
        "memory", "download", "forget", "sysprompt", # "output_tokens"
        ],


    command_image: [
        "img_model", "photos", "style_name", "improve_prompt", "improve_model", "ratio", "raw"
        ],


    command_stt: [
        "temperature", "prompt", "stt_language"
    ],
    
    "/vision": [
        "temperature", "top_p", "max_tokens", "vision_model", "to_tts", "tts_voice"
    ]
    }


shortened_args = {
    "rt": "streaming", #realtime
    "m": "chat_model",
    "cm": "chat_model",
    "im": "img_model",
    "mem": "memory",
    "sys": "sysprompt",
    "t": "temperature",
    "tp": "top_p",
    "fp": "frequency_penalty",
    "pp": "presence_penalty",
    "tk": "max_tokens", #tokens
    # "otk": "output_tokens",
    "s": "status",
    "rand": "randomizer",
    "se": "seed",
    "dl": "download", #download
    "stt": "answer_stt",
    "g": "group_mode",
    "group": "group_mode",
    "rn": "random_names",
    "18": "rol",
    "vm": "vision_model",
    "vision": "vision_model",
    "p": "photos",
    "n": "photos",
    "q": "photos",
    "r": "ratio",
    "st": "style_name",
    "style": "style_name",
    "i": "improve_prompt",
    "ip": "improve_prompt",
    "improve": "improve_prompt",
    "tim": "improve_model",
    "lang": "stt_language",
    "l": "stt_language",
    "slang": "stt_language",
    "sttl": "stt_language",
    "sttlang": "stt_language",
    "emb": "embedding_model",
    "embed": "embedding_model",
    "e": "embedding_model",
    "sum": "summarize",
    "tr": "transcribe",
    "tc": "tool_call",
    "tool": "tool_call",
    "tm": "tool_model",
    "voice": "tts_voice",
    "ttts": "to_tts",
    "d": "debug",
    "auth": "authorize",
    "deauth": "deauthorize",
    "allow": "authorize",
    "disallow": "deauthorize",
    "out": "timeout",
    "f": "forget",
    "pw": "params_warning",
    "bc": "block_command"
}

allowed_no_value = [

"rol", "status", "download", "sysprompt", "chat_model",
"img_model", "random_names", "streaming",
"memory", "randomizer", "answer_stt", "improve_prompt",
"summarize", "transcribe", "tool_call", "to_tts",
"tts_voice", "debug", "raw", "embedding_model", "forget",
"params_warning"

]

allowed_in_groups = ["status", "download", "answer_stt",
                     "stt_language", "transcribe", "stt_language",
                     "raw", "improve_prompt", "style_name", "ratio", "raw",
                     "timeout", "params_warning", "photos"
                     ]

warnings = {
    "/select": f'⚙️👎🫵\n%%{"\n".join(f"'`.{arg}`'" for arg in all_args['/select'])}%%',
    command_chat: f'💬👎🫵\n%%{"\n".join(f"'`.{arg}`'" for arg in all_args[command_chat])}%%',
    command_image: f'🎨👎🫵\n%%{"\n".join(f"'`.{arg}`'" for arg in all_args[command_image])}%%',
}



iso_639_codes = [
    "aa", "ab", "ae", "af", "ak", "am", "an", "ar", "as", "av",
    "ay", "az", "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo",
    "br", "bs", "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv",
    "cy", "da", "de", "dv", "dz", "ee", "el", "en", "eo", "es",
    "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr", "fy", "ga",
    "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr",
    "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik",
    "io", "is", "it", "iu", "iw", "ja", "ka", "kg", "ki", "kj",
    "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw",
    "ky", "la", "lb", "lg", "li", "ln", "lo", "lt", "lu", "lv",
    "mg", "mh", "mi", "mk", "ml", "mn", "mo", "mr", "ms", "mt",
    "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr",
    "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl",
    "ps", "pt", "qu", "rm", "rn", "ro", "rp", "rs", "ru", "rw",
    "sa", "sc", "sd", "se", "sg", "sh", "si", "sk", "sl", "sm",
    "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta",
    "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts",
    "tt", "tw", "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo",
    "wa", "wo", "xh", "yi", "yo", "za", "zh", "zu"
]

iso_639_codes_txt = BytesIO()
iso_639_codes_txt.name = '🗺️🏴.txt'
iso_639_codes_txt.write("\n".join(f"- {valor}" for valor in sorted(iso_639_codes)).encode("utf-8"))
