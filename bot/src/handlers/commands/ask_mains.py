from telethon import events
from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.handlers.commands.userclass import UserPrepare
from bot.src.constants import index_user_instances, roleplay_enabled
from bot.src.tools.tg_lib.mini_tools import get_id
from bot.src.tools.tg_lib.bot_mention import check as is_bot_mentioned
from bot.src.logs import logger
from gc import collect


@rate_limit_handler(5, 60)
async def ask(event, user_id) -> None:
    logger.debug(event)

    if str(event.message.message).lower().startswith("penis"):
        return await event.reply("🤡")
    return await index_user_instances[user_id].request_wrap(event)

@rate_limit_handler(5, 60)
async def roleplay(event, user_id) -> None:

    if not index_user_instances[user_id].roleplaying:
        index_user_instances[user_id].roleplaying = True

    return await index_user_instances[user_id].request_wrap(event)

@rate_limit_handler(3, 60)
async def retry(event, user_id) -> None:
    return await index_user_instances[user_id].retry_wrap(event)

def max_value_param(n):
    return max(-2, min(numero, 2))
        
avail_args = ["streaming", "model", "memory", "sprompt",
"temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens",
"status", "randomizer"]

@rate_limit_handler(3, 60)
async def select(event, user_id) -> None:

    text = (event.message.message).split(" .")[1:]
    notification = ""
    async def quickres():
        await event.reply(f"👎🫵 {', '.join(f'`{arg}`' for arg in avail_args)}")
    if not text: await quickres()
    else:
        for item in text:
            arg = str(item.split(" ")[0]).strip()
            value = " ".join(item.split(" ")[1:]).strip()
            logger.debug(value)
            booleanus = value.lower() == 'true'
            if not value and arg != "status":
                return await quickres()

            match arg:
                case "temperature" | "top_p" | "frequency_penalty" | "presence_penalty" | "max_tokens" | "timeout":
                    if not isinstance(value, int) or not isinstance(value,float):
                        return await event.reply("🤡")
                    if arg == "temperature" | "top_p":
                        pmin, pmax = 0, 2
                    elif arg == "presence_penalty" | "presence_penalty":
                        pmin, pmax = -2, 2
                    elif arg == "timeout":
                        pmin, pmax = 5, 120
                    else:
                        pmin, pmax = 1, 4096

                    value = max_value_param(pmin, pmax, value)
                    setattr(index_user_instances[user_id], arg, value)

                case "streaming":
                    index_user_instances[user_id].streaming = booleanus
                    index_user_instances[user_id].timeout = 15 if booleanus else 30
                case "model":
                    index_user_instances[user_id].model = str(value)
                case "memory":
                    index_user_instances[user_id].persist_memory = booleanus
                case "randomizer":
                    index_user_instances[user_id].randomizer = booleanus
                case "sprompt":
                    index_user_instances[user_id].custom_prompt = {"role": "system", "content": str(value)}
                    await index_user_instances[user_id].delete_conversation()
                case "status":
                    return await event.reply(f'```\n{index_user_instances[user_id].to_string()}```')
                case _:
                    await quickres()
                    break

            notification += f'{arg}: {value} ✅\n'

    if notification:
        return await event.reply(notification)

@rate_limit_handler(3, 60)
async def reset_conversation(event, user_id) -> None:

    await index_user_instances[user_id].delete_conversation()
    if len(index_user_instances[user_id].conversation) == 1:
        return await event.reply("✅")

@rate_limit_handler(2, 60)
async def burnme(event, user_id) -> None:
    if user_id in index_user_instances:
        del index_user_instances[user_id]
        collect()
        mess = "🔥"
    else:
        mess = "🤣🤣🤣🫵🫵🫵"
    return await event.reply(mess)

async def process_check(event):
    mentioned, command = await is_bot_mentioned(event)
    if not mentioned:
        logger.debug("No fue mencionado")
        return None

    user_id = get_id(event)
    if command == "/burnme":
        await burnme(event, user_id)
        return None

    if not index_user_instances.get(user_id):
        index_user_instances[user_id] = UserPrepare()
    elif index_user_instances[user_id].is_pending():
        if event.chat_id == user_id:
            await event.reply("🫸🫨🫷")
        return None
    index_user_instances[user_id].command_used = command
    return user_id


indexer = {
    "/ask": ask,
    "/rol": roleplay if roleplay_enabled else False,
    "/reset": reset_conversation,
    "/select": select,
    "/retry": retry,
    "/burnme": burnme,
    "/stt": ask
}

async def gateway(event) -> None:
    user_id = await process_check(event)
    if not user_id: return
    logger.debug("Mentioned or working.")
    callingTo = indexer.get(index_user_instances[user_id].command_used)
    logger.debug(f'calling {index_user_instances[user_id].command_used}')
    if callingTo:
        await callingTo(event, user_id = user_id)
        index_user_instances[user_id].command_used = None
    raise events.StopPropagation
