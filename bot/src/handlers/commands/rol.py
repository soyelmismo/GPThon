from bot.src.tools.other_tools import select_instance
from bot.src.config import default_roleplay_model, bot_prompts
from bot.src.wrappers.rate_limiter import rate_limit_handler

@rate_limit_handler(5, 60)
async def roleplay(event, user_id, chat_id, command) -> None:
    class_to_edit = await select_instance(chat_id, user_id)
    if not class_to_edit.roleplaying:
        class_to_edit.roleplaying = True
        class_to_edit.chat_model = default_roleplay_model
        class_to_edit.temperature = 0.7
        class_to_edit.top_p = 0.97
        class_to_edit.sysprompt = {"role": "system", "content": bot_prompts.get("roleplay", "")}
        await class_to_edit.delete_conversation(event, user_id, rol = 1)
    if command == "/rol":
        return await class_to_edit.request_wrap(event, command = command)
