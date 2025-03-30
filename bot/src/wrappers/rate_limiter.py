from aiolimiter import AsyncLimiter
from functools import wraps
from bot.src.tools.tg_tools import command_list
from bot.src.logs import logger

limiters = {}

def rate_limit_handler(limit: int, interval: int):
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            try:
                is_command = kwargs.get("command", "").startswith("/")

                if is_command and kwargs.get("command", "") in command_list:
                    limiter_key = f'{kwargs["user_id"]}_{kwargs["command"]}'
                    limiter = limiters.get(limiter_key)

                    if not limiter:
                        limiter = AsyncLimiter(limit, interval)
                        limiters[limiter_key] = limiter
                    if not limiter.has_capacity():
                        return

                    async with limiter:
                        await func(event, *args, **kwargs)
                else:
                    await func(event, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in rate_limit_handler: {e}")
        return wrapper
    return decorator