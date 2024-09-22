import bot.src.handlers.database as rdb
from bot.src.wrappers.rate_limiter import rate_limit_handler


@rate_limit_handler(2, 60)
async def burnme(event, user_id):
    if user_id in rdb.db.index:
        await rdb.db.burn_me(user_id)
        await event.reply("🔥")
    else:
        await event.reply("🤣🤣🤣🫵🫵🫵")
