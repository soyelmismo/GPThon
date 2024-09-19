from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.logs import logger
from bot.src.tools.tg_tools import send_msg, remove_command, select_instance
from sys import _getframe

banned_attr = [
    "warning", "style_data", "style_name", "prompt",
    "ratio", "photos", "notification", "used_tokens",
    "session_tokens", "raw"
]

@rate_limit_handler(3, 60)
async def select(event, user_id, chat_id, command) -> None:
    from bot.src.tools.params.inference_params import extract_arguments

    try:
        notShit = await select_instance(chat_id, user_id)
        prompt = await remove_command(notShit.conversation, event, command)
        thisShit = await extract_arguments(notShit, event, prompt, command, user_id, chat_id)
        if not thisShit:
            return None

        for key, value in thisShit.__dict__.items():
            if key not in banned_attr:
                setattr(notShit, key, value)

        if thisShit.notification:
            return await send_msg(event, thisShit.notification)
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
