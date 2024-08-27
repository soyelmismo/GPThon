from telethon import events
from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.handlers.commands.userclass import UserPrepare
import bot.src.constants as constants
from bot.src.tools.tg_lib.mini_tools import get_id, is_bot_mentioned
from bot.src.logs import logger
from gc import collect
from hashlib import sha1
from io import BytesIO


@rate_limit_handler(5, 60)
async def ask(event, user_id) -> None:
    logger.debug(event)

    if str(event.message.message).lower().startswith("penis"):
        return await event.reply("🤡")
    return await constants.index_user_instances[user_id].request_wrap(event)

#@rate_limit_handler(5, 60)
#sync def roleplay(event, user_id) -> None:

#    if not constants.index_user_instances[user_id].roleplaying:
#        constants.index_user_instances[user_id].roleplaying = True

#    return await constants.index_user_instances[user_id].request_wrap(event)

@rate_limit_handler(3, 60)
async def retry(event, user_id) -> None:
    return await constants.index_user_instances[user_id].retry_wrap(event)

def max_value_param(pmin, pmax, value):
    return min(max(value, pmin), pmax)

        
avail_args = ["streaming", "model", "memory", "sprompt",
"temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens",
"status", "randomizer", "seed", "dump", "answer_stt"]

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
            if not value and arg not in ["status", "dump"]:
                return await quickres()

            match arg:
                case "temperature" | "top_p" | "frequency_penalty" | "presence_penalty" | "max_tokens":
                    try:
                        value = float(value)
                    except ValueError:
                        return await event.reply("🤡")
                    if arg in ["temperature", "top_p"]:
                        pmin, pmax = 0, 2
                    elif arg in ["presence_penalty", "presence_penalty"]:
                        pmin, pmax = -2, 2
                    else:
                        pmin, pmax = 1, 32768

                    value = max_value_param(pmin, pmax, value)
                    setattr(constants.index_user_instances[user_id], arg, value)

                case "streaming" | "memory" | "randomizer" | "answer_stt":
                    setattr(constants.index_user_instances[user_id], arg, value.lower() == 'true')
                case "model" | "img_model":
                    models_dict = constants.models_dict if arg == "model" else constants.img_models
                    
                    if models_dict and value not in models_dict:
                        return await event.reply(file=constants.models_txt if arg == "model" else constants.img_models_txt, force_document=True)
                    
                    setattr(constants.index_user_instances[user_id], arg, str(value))

                case "dump":
                    t_convo = ""
                    for item in constants.index_user_instances[user_id].conversation:
                        role = item.get("role", " ")
                        content = item.get("content", "")
                        t_convo += f"*{role[0].upper()}*: {content}\n\n"
                    convo = BytesIO()
                    convo.name = '🖨️.txt'
                    convo.write(t_convo.encode('utf-8'))
                    convo.seek(0)
                    return await event.reply(file=convo, force_document=True)
                case "sprompt":
                    if value == "None":
                        constants.index_user_instances[user_id].sprompt = None
                    else:
                        constants.index_user_instances[user_id].sprompt = {"role": "system", "content": str(value)}
                    await constants.index_user_instances[user_id].delete_conversation()
                case "status":
                    return await event.reply(f'```\n{constants.index_user_instances[user_id].to_string()}```')
                case "seed":
                    if value == "None":
                        value = None
                    else:
                        try:
                            value = int(value)
                        except:
                            value = int(sha1(str(value).encode()).hexdigest(), 16)
                    constants.index_user_instances[user_id].seed = value
                case _:
                    await quickres()
                    break

            notification += f'{arg}: {value} ✅\n'

    if notification:
        return await event.reply(notification)

@rate_limit_handler(3, 60)
async def reset_conversation(event, user_id) -> None:

    await constants.index_user_instances[user_id].delete_conversation()
    if len(constants.index_user_instances[user_id].conversation) == 1:
        return await event.reply("✅")

@rate_limit_handler(2, 60)
async def burnme(event, user_id) -> None:
    if user_id in constants.index_user_instances:
        del constants.index_user_instances[user_id]
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

    if not constants.index_user_instances.get(user_id):
        constants.index_user_instances[user_id] = UserPrepare()
    elif constants.index_user_instances[user_id].pending and command != "/select":
        if constants.index_user_instances[user_id].command_used in ["/img"] and constants.index_user_instances[user_id].img_pending:
            await event.reply("🫵🤬, 🖐️⏳... 🖕.")
        elif event.chat_id == user_id or mentioned:
            await event.reply("🫸🫨🫷")
        return None
    constants.index_user_instances[user_id].command_used = command
    return user_id


indexer = {
    "/ask": ask,
    #"/rol": roleplay if roleplay_enabled else False,
    "/reset": reset_conversation,
    "/select": select,
    "/retry": retry,
    "/burnme": burnme,
    "/stt": ask,
    "/vision": ask,
    "/img": ask,
}

async def gateway(event) -> None:
    user_id = await process_check(event)
    if not user_id: return
    logger.debug("Mentioned or working.")
    callingTo = indexer.get(constants.index_user_instances[user_id].command_used)
    logger.debug(f'calling {constants.index_user_instances[user_id].command_used}')
    if callingTo:
        await callingTo(event, user_id = user_id)
        constants.index_user_instances[user_id].command_used = None
    raise events.StopPropagation
