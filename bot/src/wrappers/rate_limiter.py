from aiolimiter import AsyncLimiter
from functools import wraps
from telethon.types import MessageEntityBotCommand
from bot.src.tools.other_tools import get_id

limiters = {}

def rate_limit_handler(limit: int, interval: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            is_command = bool(event.original_update.message and event.original_update.message.entities and isinstance(event.original_update.message.entities[0], MessageEntityBotCommand))

            if is_command:
                user_id = await get_id(event)
                limiter_key = f"{user_id}_{event.original_update.message.message.split()[0]}"
                limiter = limiters.get(limiter_key, AsyncLimiter(limit, interval))
                limiters[limiter_key] = limiter
                if not limiter.has_capacity():
                    return

                async with limiter:
                    await func(event, *args, **kwargs)
            else:
                await func(event, *args, **kwargs)
        return wrapper
    return decorator