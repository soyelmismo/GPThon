import bot.src.config as c
from bot.src.constants import *
from bot.src.logs import logger
from bot.src.wrappers.rate_limiter import rate_limit_handler


from bot.src.tools.tg_tools import *
from bot.src.tools.other_tools import *
from bot.src.handlers.commands.select import select
from bot.src.handlers.commands.ask import ask_gateway
from bot.src.handlers.commands.reset import reset_conversation
from bot.src.handlers.commands.retry import retry
from bot.src.handlers.tasks import cancel_task

indexer = {
    c.command_chat: ask_gateway,
    c.command_stt: ask_gateway,
    c.command_transcribe: ask_gateway,
    c.command_tts: ask_gateway,
    "/vision": ask_gateway,
    "/embed": ask_gateway,
    c.command_image: ask_gateway,
    "/rol": ask_gateway,
    "/reset": reset_conversation,
    "/select": select,
    "/retry": retry
}

async def gateway(event) -> None:
    if c.bot_data.id == event.sender_id: return
    mentioned, command = await is_bot_mentioned(event)
    if not mentioned:
        return
    logger.debug("Bot mentioned. Continuing.")
    if not await whitelist_check(event):
        return

    user_id = await get_id(event)
    logger.debug(f"Mentioned by {user_id} using command {command}")
    if not user_id:
        return
    elif command == "/help":
        return await help(event)
    chat_id = str(event.chat_id)

    callingTo = indexer.get(command)
    if command and callingTo:
        logger.debug(f'calling {command}')
        return await callingTo(event, user_id = user_id, chat_id=chat_id, command = command)

@rate_limit_handler(3, 60)
async def help(event):
    return await event.reply("https://telegra.ph/GPThon-Guide-09-05")


async def cancel_callback(event):
    try:
        _, c_type, c_tik = str(event.data.decode('utf-8')).split("|")
        user_id = await select_instance(event = event, task_id=c_tik)
        logger.debug(event)
        logger.debug(f'{c_type} {user_id} {c_tik}')
        message = await cancel_task(c_type, user_id, c_tik)
        if message:
            await event.answer(message, alert=False)
            
    except Exception as e:
        logger.error(str(e))
