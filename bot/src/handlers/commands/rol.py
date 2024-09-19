from bot.src.config import default_roleplay_model, bot_prompts
from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.tools.tg_tools import select_instance

@rate_limit_handler(5, 60)
async def roleplay(event, user_id, chat_id, command) -> None:
    urClass = await select_instance(chat_id, user_id)
    if not urClass.roleplaying:
        urClass.roleplaying = True
        urClass.chat_model = default_roleplay_model
        urClass.temperature = 0.7
        urClass.top_p = 0.97
        urClass.sysprompt = bot_prompts.get("roleplay", "")
        await urClass.delete_conversation(event, user_id, rol = 1, notify = 1)
    if command == "/rol":
        return await urClass.request_wrap(event, user_id, command = command)
