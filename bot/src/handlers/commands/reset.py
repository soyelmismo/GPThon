from bot.src.tools.tg_tools import send_msg, select_instance
from bot.src.wrappers.rate_limiter import rate_limit_handler

@rate_limit_handler(3, 60)
async def reset_conversation(event, user_id, chat_id, command) -> None:
    class_to_edit = await select_instance(chat_id, user_id)
    await class_to_edit.delete_conversation(event, user_id, notify = 1)
    if len(class_to_edit.conversation) in [0,1,3]:
        await send_msg(event, "✅", delete_user_message = True)
