from . import rate_limit_handler
from bot.src.handlers.database import db
@rate_limit_handler(2, 60)
async def burnme(event, user_id) -> None:

    data = await db.burn_me(user_id)
    if data:
        mess = "🔥"
    else:
        mess = "🤣🤣🤣🫵🫵🫵"
    return await event.reply(mess)
