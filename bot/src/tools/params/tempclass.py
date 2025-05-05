from bot.src.config import command_stt
from copy import deepcopy

async def clone_class_with_attributes(base_instance):
    # Crea una nueva instancia de la clase base
    new_instance = type(base_instance)()  # Llama al constructor de la clase base

    # Copia los atributos de forma independiente
    for attr, value in vars(base_instance).items():
        if not callable(value) and not attr.startswith("__"):
            # Copiar atributos que no son métodos y no son privados
            setattr(new_instance, attr, deepcopy(value))

    return new_instance

async def gotClass(cls, command, prompt):
    thisShit = await clone_class_with_attributes(cls)

    thisShit.warning = None
    thisShit.style_data = None
    thisShit.style_name = "raw"
    thisShit.prompt = None
    thisShit.ratio = "1024x1024"
    thisShit.prompt = prompt
    thisShit.photos = 1
    thisShit.forget = False
    thisShit.download = False
    thisShit.temperature = 0.4 if command == command_stt else float(cls.temperature)
    thisShit.notification = ""
    thisShit.used_tokens = 0
    thisShit.session_tokens = 0
    thisShit.raw = False
    return thisShit
