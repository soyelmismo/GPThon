from bot.src import constants
from bot.src.handlers import userclass
from bot.src.tools.tg_tools import get_id

async def select_instance(chat_id = None, user_id = None, event = None):
    i = None
    ruid = None
    if event and not chat_id or not user_id:
        
        user_id = await get_id(event)
        chat_id = str(event.chat_id)
        ruid = user_id

    if constants.index_group_instances.get(chat_id):
        i = constants.index_group_instances[chat_id]
    else:
        if not constants.index_user_instances.get(user_id):
            constants.index_user_instances[user_id] = userclass.UserPrepare()
            constants.index_user_instances[user_id].user_id = user_id
        i = constants.index_user_instances[user_id]
    return ruid if ruid else i