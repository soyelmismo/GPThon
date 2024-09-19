import bot.src.handlers.database as rdb
from bot.src.wrappers.rate_limiter import rate_limit_handler


@rate_limit_handler(2, 60)
async def burnme(event, user_id) -> None:

    data = await rdb.db.burn_me(user_id)
    if data:
        mess = "🔥"
    else:
        mess = "🤣🤣🤣🫵🫵🫵"
    return await event.reply(mess)
