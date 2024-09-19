from bot.src.config import command_stt

async def clone_class_with_attributes_old(base_instance):
    class ClonedClass:
        pass

    for attr in dir(base_instance):
        if not attr.startswith('__') and not callable(getattr(base_instance, attr)):
            setattr(ClonedClass, attr, getattr(base_instance, attr))

    return ClonedClass

async def clone_class_with_attributes(base_instance):
    attributes = {k: v for k, v in vars(base_instance).items() if not callable(v)}

    ClonedClass = type('ClonedClass', (object,), attributes)
    return ClonedClass

async def gotClass(cls, command, prompt):
    ClonedClass = await clone_class_with_attributes(cls)

    thisShit = ClonedClass()
    thisShit.warning = None
    thisShit.style_data = None
    thisShit.style_name = "raw"
    thisShit.prompt = None
    thisShit.ratio = "1024x1024"
    thisShit.prompt = prompt
    thisShit.photos = 1
    thisShit.temperature = 0.4 if command == command_stt else float(cls.temperature)
    thisShit.notification = ""
    #thisShit.summarize = bool(cls.summarize) or True
    thisShit.used_tokens = 0
    thisShit.session_tokens = 0
    #thisShit.embedding_model = cls.embedding_model or default_embedding_model
    #thisShit.tool_model = cls.tool_model or default_tool_model
    thisShit.raw = False
    return thisShit
