from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.handlers.tasks import index_tasks
from bot.src import constants

@rate_limit_handler(2, 60)
async def burnme(event, user_id) -> None:
    if user_id in constants.index_user_instances:
        if constants.index_group_instances:
            for group in dict(constants.index_group_instances).items():
                if group[1].user_id == user_id:
                    del constants.index_group_instances[group[0]]
        index_tasks.pop(user_id, None)
        constants.index_user_instances.pop(user_id, None)
        mess = "🔥"
    else:
        mess = "🤣🤣🤣🫵🫵🫵"
    return await event.reply(mess)
