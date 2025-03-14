import bot.src.handlers.database as rdb
from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.tools.tg_tools import select_instance

@rate_limit_handler(2, 60)
async def burnme(event, user_id, chat_id, command):
    class_to_call = await select_instance(chat_id, user_id, event)
    if class_to_call.group_mode:
        if user_id not in class_to_call.owners:
            return await event.reply("🤣🤣🤣🫵🫵🫵")
        await rdb.db.burn_group(chat_id, justConfig = True)
    else:
        await rdb.db.burn_user_config(user_id)
    return await event.reply("🔥")
