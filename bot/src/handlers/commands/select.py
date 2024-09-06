import bot.src.constants as constants
from bot.src.config import max_input_tokens
from bot.src.handlers.userclass import UserPrepare
from bot.src.handlers.commands.rol import roleplay
from bot.src.logs import logger
from io import BytesIO
from hashlib import sha1
from bot.src.wrappers.rate_limiter import rate_limit_handler
from bot.src.tools.other_tools import select_instance
from bot.src.tools.tg_tools import send_msg

avail_args = ["streaming", "chat_model", "img_model", "memory", "sysprompt",
"temperature", "top_p", "frequency_penalty", "presence_penalty", "max_tokens",
"status", "randomizer", "seed", "download", "answer_stt", "group_mode", "random_names",
"rol", "improve_model"]

shortened_args = {
    "rt": "streaming", #realtime
    "m": "chat_model",
    "cm": "chat_model",
    "im": "img_model",
    "mem": "memory",
    "sys": "sysprompt",
    "t": "temperature",
    "tp": "top_p",
    "fp": "frequency_penalty",
    "pp": "presence_penalty",
    "tk": "max_tokens", #tokens
    "s": "status",
    "r": "randomizer",
    "se": "seed",
    "dl": "download", #download
    "stt": "answer_stt",
    "g": "group_mode",
    "group": "group_mode",
    "rn": "random_names",
    "18": "rol",
    "tim": "improve_model"
}


warning = f"👎🫵 {', '.join(f'`.{arg}`' for arg in avail_args)}"

@rate_limit_handler(3, 60)
async def select(event, user_id, chat_id, command) -> None:

    text = (event.message.message).split(" .")[1:]
    logger.debug(f'Select text: `{text}`')
    notification = ""

    

    
    if not text:
        await send_msg(event, warning)
    else:
        args_tried = []
        chat_id = str(event.chat_id)
        
        for item in text:
            class_to_edit = await select_instance(chat_id, user_id)
            arg = str(item.split(" ")[0]).strip()
            logger.debug(f'Selected arg: `{arg}`')
            arg = shortened_args.get(arg, arg)
            if arg in args_tried:
                continue
            value = " ".join(item.split(" ")[1:]).strip()
            logger.debug(f'Selected value: `{value}`')
            if class_to_edit.group_mode and arg not in ["status", "download", "answer_stt"]:
                if class_to_edit.user_id != user_id:
                    return await send_msg(event, "🫂 🚫")

            if not value and arg not in ["rol", "status", "download", "sysprompt", "chat_model",
                                         "img_model", "group_mode", "random_names", "streaming",
                                         "memory", "randomizer", "answer_stt"]:
                return await send_msg(event, warning)

            match arg:
                case "temperature" | "top_p" | "frequency_penalty" | "presence_penalty" | "max_tokens":
                    try:
                        value = float(value)
                    except ValueError:
                        return await send_msg(event, "🤡")
                    value = await max_value_param(arg, value)
                    setattr(class_to_edit, arg, value)

                case "streaming" | "memory" | "randomizer" | "answer_stt":
                    if not value:
                        value = not getattr(class_to_edit, arg)
                    else:
                        value = value.lower() == 'true'
                    setattr(class_to_edit, arg, value)

                case "chat_model" | "img_model" | "improve_model" | "vision_model":
                    if not class_to_edit.roleplaying:
                        models_dict = constants.chat_models if arg == "chat_model" else constants.img_models
                        if models_dict and (not value or value not in models_dict):
                            models_file = constants.models_txt if arg == "chat_model" else constants.img_models_txt
                            models_file.seek(0)
                            return await send_msg(event, text = "😒", file=models_file, force_document=True, disable_delete=True)

                        setattr(class_to_edit, arg, str(value))

                    else:
                        return await send_msg(event, "🚫🔞🚫")

                case "download":
                    file = await get_conversation(class_to_edit)
                    return await send_msg(event, text = "🫡", file=file, force_document=True, disable_delete=True)
                case "sysprompt":
                    if value == "None":
                        class_to_edit.sysprompt = None
                    elif not value:
                        if class_to_edit.sysprompt and not class_to_edit.roleplaying:
                            sysprompt = str(class_to_edit.sysprompt["content"])
                            return await send_msg(event, sysprompt)
                        else:
                            return await send_msg(event, "🫵🤡🤣")
                    else:
                        class_to_edit.sysprompt = {"role": "system", "content": str(value)}

                    if class_to_edit.roleplaying:
                        rol = 1
                    else:
                        rol = 0

                    await class_to_edit.delete_conversation(event, user_id, rol)

                case "status":
                    return await send_msg(event, f'```\n{await class_to_edit.to_string()}```', disable_delete=True)

                case "seed":
                    if value == "None":
                        value = None
                    else:
                        try:
                            value = int(value)
                        except:
                            value = await hash_to_8_digits(value)

                    class_to_edit.seed = value
                
                case "group_mode" | "random_names":

                    if not value:
                        value = not bool(getattr(class_to_edit, arg))
                    else:
                        value = value.lower() == 'true'

                    if not constants.index_group_instances.get(chat_id):
                        if arg == "group_mode" and value:
                            constants.index_group_instances[chat_id] = UserPrepare()
                            constants.index_group_instances[chat_id].user_id = user_id
                            constants.index_group_instances[chat_id].group_mode = True
                            value = "🫂"
                        else:
                            return await send_msg(event, "🤡 🫂❓")
                    elif constants.index_group_instances[chat_id].user_id == user_id:

                        if arg == "group_mode" and not value:
                            del constants.index_group_instances[chat_id]
                            return await send_msg(event, "🫂🔥 ✅")
                        elif arg == "random_names":
                            constants.index_group_instances[chat_id].random_names = value
                    else:
                        return await send_msg(event, "🫂🔥 🚫")

                case "rol":
                    await roleplay(event, user_id, chat_id, "/select")
                    value = "🔞🔥"
                    
                case _:
                    await send_msg(event, warning)
                    break

            notification += f'.{arg}: {value} ✅\n'
            args_tried.append(arg)

    if notification:
        return await send_msg(event, notification)
    

### Mini tools for /select

async def max_value_param(arg, value):
    if arg in ["temperature", "top_p"]:
        pmin, pmax = 0, 2
    elif arg in ["presence_penalty", "presence_penalty"]:
        pmin, pmax = -2, 2
    else:
        pmin, pmax = 16, max_input_tokens
    value = min(max(value, pmin), pmax)

    return abs(int(value)) if arg == "max_tokens" else value

async def get_conversation(class_to_fetch):
    t_convo = ""
    for item in class_to_fetch.conversation:
        role = item.get("role", " ")
        if class_to_fetch.roleplaying and role == "system":
            content = "*Roleplay*"
        else:
            content = item.get("content", "")
        t_convo += f"*{role[0].upper()}*: {content}\n\n\n\n"
    convo = BytesIO()
    convo.name = '🖨️.txt'
    convo.write(t_convo.encode('utf-8'))
    convo.seek(0)
    return convo

async def hash_to_8_digits(value):
    hash_value = sha1(str(value).encode()).hexdigest()
    int_value = int(hash_value, 16)
    result = int_value % 10**8
    return result
