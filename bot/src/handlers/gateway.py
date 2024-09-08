from . import *


indexer = {
    command_chat: ask_gateway,
    command_stt: ask_gateway,
    "/vision": ask_gateway,
    command_image: ask_gateway,
    "/rol": roleplay if roleplay_enabled else False,
    "/reset": reset_conversation,
    "/select": select,
    "/retry": retry
}

async def gateway(event) -> None:
    mentioned, command = await is_bot_mentioned(event)
    if not mentioned:
        #logger.debug("No fue mencionado")
        return
    logger.debug("Bot mentioned. Continuing.")
    if not await whitelist_check(event):
        return

    user_id = await get_id(event)
    logger.debug(f"Mentioned by {user_id} using command {command}")
    if not user_id:
        return
    if command == "/burnme":
        return await burnme(event, user_id)
    elif command == "/help":
        return await help(event)
    chat_id = str(event.chat_id)

    callingTo = indexer.get(command)
    if command and callingTo:
        logger.debug(f'calling {command}')
        create_task(callingTo(event, user_id = user_id, chat_id=chat_id, command = command))
    # raise events.StopPropagation

@rate_limit_handler(3, 60)
async def help(event):
    return await event.reply("https://telegra.ph/GPThon-Guide-09-05")