from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.tools.other_tools import select_instance
from bot.src.tools.tg_tools import send_msg

@rate_limit_handler(3, 60)
async def retry(event, user_id, chat_id, command) -> None:
    class_to_edit = await select_instance(chat_id, user_id)
    if len(class_to_edit.conversation) > 1:
        return await class_to_edit.request_wrap(event, command)
    await send_msg(event, "🙄", delete_user_message = True)
