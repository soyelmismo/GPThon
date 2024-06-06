from aiolimiter import AsyncLimiter
from functools import wraps
from telethon import events, types
from bot.src.tools.tg_lib.mini_tools import get_id
# Diccionario para almacenar los limitadores por user_id
limiters = {}

# Decorador para aplicar el rate-limiter por id de usuario
def rate_limit_handler(limit: int, interval: int) -> exec:
    def decorator(func):
        @wraps(func)
        async def wrapper(event: events, *args, **kwargs):

            # Verificar si el mensaje es un comando
            is_command = bool(event.original_update.message and event.original_update.message.entities and isinstance(event.original_update.message.entities[0], types.MessageEntityBotCommand))

            if is_command:
                user_id = get_id(event)
                # Obtener el limitador del diccionario o crear uno nuevo si no existe
                limiter_key = f"{user_id}_{event.original_update.message.message.split()[0]}"
                limiter = limiters.get(limiter_key, AsyncLimiter(limit, interval))
                limiters[limiter_key] = limiter

                async with limiter:
                    await func(event, *args, **kwargs)
            else:
                await func(event, *args, **kwargs)
        return wrapper
    return decorator
