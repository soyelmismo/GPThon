from bot.src import constants as c
from bot.src import config as conf
from random import choice
from bot.src.logs import logger
from bot.src.tools.api_utils import apis_frontend as oai
import bot.src.tools.api_utils.api_selector as api_datas
from bot.src.tools.tg_tools import command_list
from hashlib import sha1
from re import compile, findall, split

from bot.src.tools.params.tempclass import gotClass

from bot.src.tools.params.longAssDicts import shortened_args, img_ratios, iso_639_codes, iso_639_codes_txt, warnings, all_args, allowed_no_value

from sys import _getframe

pattern = compile(r"(\s+\.[a-zA-Z0-9]+(\s+[^\s.]|[\S])*)") #OK OK GOOOOD

async def extract_prompt_args(cls, prompt, command):
    thisShit = await gotClass(cls, command, prompt)
    args = {}
    try:
        matches = list(pattern.finditer(prompt))

        prompt_parts = []
        start = 0
        for match in matches:
            arg = match.group()
            new_arg, value = await extract_arg_value(arg.strip())
            if new_arg in all_args[command]:
                args[new_arg] = value
                prompt_parts.append(prompt[start:match.start()])
                start = match.end()
            else:
                if not value and new_arg not in allowed_no_value:
                    thisShit.warning = f'⚠️**.{arg}**⚠️\n\n{warnings.get(command)}'
                    break
                elif thisShit.params_warning:
                    thisShit.warning = f'⚠️**.{arg}**⚠️\n\n{warnings.get(command)}'
                    break
        prompt_parts.append(prompt[start:])
        cleaned_prompt = ''.join(part for part in prompt_parts if part).strip()
        thisShit.prompt = cleaned_prompt
        return thisShit, cleaned_prompt, args
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        thisShit.prompt = prompt
        return thisShit. prompt, {}

async def extract_arg_value(item):
    arg, value = "", ""
    try:
        arg = str(item.split(" ")[0]).strip().replace(".", "")
        arg = shortened_args.get(arg, arg)
        value = " ".join(item.split(" ")[1:]).strip()
        return arg, value
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")

async def manage_style(thisShit, style_name):
    style_prompt = None
    try:
        if style_name in ["r", "random", "a", "any"]:
            style_name = choice([e for e in c.img_styles if e not in ["general", "raw"]])
        style_prompt = c.img_styles.get(style_name, None)

        if not style_prompt:
            style_name = {"text": f"⚠️**{style_name}**⚠️\n\n😒", "file": c.img_styles_txt, "force_document": True, "disable_delete": True}
        else:
            style_prompt = str(style_prompt).replace("{p}", thisShit.prompt).strip()

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
    finally:
        thisShit.style_data = [style_name, style_prompt]
        thisShit.style_name = style_name

async def final_img_step(thisShit):
    try:
        if len(thisShit.prompt) > 999:
            thisShit.prompt = thisShit.prompt[:999]
        await manage_style(thisShit, thisShit.style_name)

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
            

photos_err = "👎🫵 `.photos` `1` - `4`"
async def p_photos(thisShit, value):
    
    try:
        value = int(value)
        if value not in range(1, 5):
            value = photos_err

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = photos_err
    finally:
        thisShit.photos = value

ratios_err = f"👎🫵 {', '.join(f'`.r {ratio}`' for ratio in img_ratios)}"

async def p_ratio(thisShit, value):
    try:
        grab = img_ratios.get(value)
        if grab:
            value = grab
        else:
            value = ratios_err
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = ratios_err
    finally:
        thisShit.ratio = value

improve_err = ["❌😔"]
async def p_improve(thisShit, user_id, value):
    try:
        if await thisShit.check_some_limits(conf.command_chat, skip={"1", "returnOnlyChatLimit"}):
            thisShit.prompt = [f"{improve_err}... You can't use .improve when you run out of tokens."]
            return
        if value:
            promptr = f'"{thisShit.prompt}"\n\nimportant feedback to implement: {value}'
        else:
            promptr = thisShit.prompt
        thisShit.conversation = [
            {"role": "system", "content": conf.bot_prompts["img_improve"]},
            {"role": "user", "content": promptr}
            ]
        improved_prompt = await oai.quick_chat_completion(thisShit, user_id, thisShit.chat_model)

        if improved_prompt == "Cancelled":
            return [None]
        elif not isinstance(improved_prompt, str):
            improved_prompt = improve_err
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        improved_prompt = improve_err
    finally:
        thisShit.prompt = improved_prompt
        
async def p_floats(thisShit, arg, value):
    try:
        value = await max_value_param(thisShit, arg, float(value))
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = "🤡"
    finally:
        setattr(thisShit, arg, value)

async def max_value_param(thisShit, arg, value):
    try:
        if arg in ["temperature"]:
            pmin, pmax = 0, 1
        elif arg in ["timeout"]:
            pmin, pmax = 3, 600
        elif arg in ["top_p"]:
            pmin, pmax = 0, 1
        elif arg in ["presence_penalty", "frequency_penalty"]:
            pmin, pmax = -1.5, 1.5
        else:
            pmin, pmax = 32, conf.PAID_PLANS[thisShit.tier]["context_token_limit"]
        value = min(max(value, pmin), pmax)
        if arg in ["max_tokens", "output_tokens"]:
            value = abs(int(value))
            #if value < 1024: # Commented cuz i don't remember why is it here... Maybe this is the beginning of documentation in this project (maybe, idk, probably)
            #    thisShit.summarize = False

            #update: i think there will not be documentation. and this comment up here is probably cuz summarization with low token context is a piece of shit
        return value
    except Exception as e:
        e = f"{_getframe().f_code.co_name}: {str(e)}"
        logger.error(e)
        raise Exception(e)

async def p_auto_bool(thisShit, arg, value, just_return = None):
    try:
        if not value:
            value = not getattr(thisShit, arg)
        else:
            value = value.lower() == 'true'

        if arg == "tool_call" and not conf.PAID_PLANS[thisShit.tier]["tool_calls"]:
            thisShit.warning = {"text": f"🚫`{arg}`🚫\n\n1. 💲👉 {conf.donate_url} 👍💲\n2. 💬 {conf.donate_contact}", "disable_delete": True}
            return
        if not just_return:
            setattr(thisShit, arg, value)
        else:
            return value
    except Exception as e:
        e = f"{_getframe().f_code.co_name}: {str(e)}"
        logger.error(e)
        raise Exception(e)

model_types = ["chat_model", "vision_model", "embedding_model", "tts_voice"]

forbidden = {"text": "🚫🔞🚫"}

async def get_models_file(type):
    return (
            c.img_models if type in ["img_model"]
            else c.embed_models if type in ["embedding_model"]
            else c.speech_voices if type in ["tts_voice"]
            else c.chat_models
            )
async def vip_model_user(userdata, model, user_id, chat_id):
    if (
        "all" in conf.PAID_PLANS[userdata.tier]["allowed_models"]
        or model not in conf.PAID_PLANS["tier_3"]["allowed_models"]
        # or model not in conf.PAID_PLANS["tier_3"]["allowed_models"]
        or model in conf.PAID_PLANS[userdata.tier]["allowed_models"]
        or model in userdata.allowed_models
    ):
        return True
    return False

async def p_models(thisShit, chat_id, user_id, arg, value):
    try:
        if thisShit.roleplaying:
            value = forbidden
        else:
            models_dict = await get_models_file(arg)
            if value in ["r", "random", "a", "any"]:
                models_list = list(models_dict)
                while True:
                    selected_model = choice(models_list)
                    if not await vip_model_user(thisShit, selected_model, user_id, chat_id):
                        continue
                    elif len(models_dict[selected_model]) == 1 and models_dict[selected_model][0] == "fresed" and "fresed" in api_datas.rate_limited:
                        logger.warning(f'{selected_model} only supported by fresed, but fresed is rate-limited.')
                        continue
                    else:
                        value = selected_model
                        break

            elif not value or value not in models_dict:
                models_file = (
                                c.img_models_txt if arg in ["img_model"]
                                else c.embed_models_txt if arg in ["embedding_model"]
                                else c.speech_voices_txt if arg in ["tts_voice"]
                                else c.chat_models_txt
                                )
                text = f"⚠️**{value}**⚠️\n\n😒" if not value else "😒"

                value = {"text": text, "file": models_file, "force_document": True, "disable_delete": True}
            else:
                if not await vip_model_user(thisShit, value, user_id, chat_id):
                    value = {"text": f"🚫`{value}`🚫\n\n1. 💲👉 {conf.donate_url} 👍💲\n2. 💬 {conf.donate_contact}", "disable_delete": True}

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = forbidden
    finally:
        setattr(thisShit, arg, value)


async def p_sysprompt(cls, thisShit, value, event, user_id, command):
    try:
        if thisShit.roleplaying:
            thisShit.warning = "🫵🤡🤣"
            return
        elif value:
            thisShit.sysprompt = str(value)
            if command == "/select":
                cls.sysprompt = thisShit.sysprompt
        else:
            value = cls.sysprompt

        # await cls.delete_conversation(event, user_id, 0, notify = 1)
        await thisShit.delete_conversation(event, user_id, 0, notify = 1)
        return value
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")


async def p_seed(thisShit, value):
    try:
        try:
            value = None if value.lower() in ["none", "empty", "reset"] else int(value)
        except:
            value = await hash_to_8_digits(value)

        thisShit.seed = value
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")

async def hash_to_8_digits(value):
    hash_value = sha1(str(value).encode()).hexdigest()
    int_value = int(hash_value, 16)
    result = int_value % 10**8
    return result


async def is_integer_string(value):
    if value.lstrip('-').isdigit():
        return True
    return False


# This is not mini
async def p_group(thisShit, event, arg, value, chat_id, user_id):
    import bot.src.handlers.database as rdb
    try:
        if event.is_private:
            return {"text": "🤡 🫂❓", "delete_user_message":True}
        if not await is_integer_string(value):
            value = await p_auto_bool(thisShit, arg, value, just_return=True)

        if chat_id in rdb.db.index and rdb.db.index[chat_id].owners:
            if user_id == rdb.db.index[chat_id].user_id:
                if arg == "group_mode" and not value:
                    cb = await rdb.db.burn_group(chat_id)
                    if cb:
                        async with rdb.db.lock:
                            rdb.db.index[user_id].groups.discard(chat_id)
                        return {"text": "🫂🔥 ✅", "delete_user_message": True}
                    else:
                        return {"text": "🫂🔥 ❌", "delete_user_message": True}
                elif arg == "random_names":
                    async with rdb.db.lock:
                        rdb.db.index[chat_id].random_names = value
                    return {"text": f"{arg}: {value}", "delete_user_message": True}
                elif arg == "authorize":
                    async with rdb.db.lock:
                        rdb.db.index[chat_id].owners.add(value)
                    return {"text": f"🫡`{value}` 👌"}
                elif arg == "deauthorize":
                    if value != rdb.db.index[chat_id].user_id:
                        async with rdb.db.lock:
                            rdb.db.index[chat_id].owners.discard(value)
                        return {"text": f'🫡"`{value}` = 💩🤮"'}
                    else:
                        return {"text": "🤣🫵🤣🫵🤣🫵💩💩💩"}
            else:
                return {"text": "🫂🔥 🚫", "delete_user_message": True}
        elif arg == "group_mode" and value:
            max_groups = conf.PAID_PLANS[thisShit.tier]["max_linked_groups"]
            if len(thisShit.groups) > max_groups:
                return {"text": f"Max allowed groups reached ({max_groups}) get **VIP** for more!", "delete_user_message": True}
            grClass = await rdb.db.grab_class(chat_id = chat_id, user_id = user_id, make_group = True, private=event.is_private)
            if user_id in grClass.owners:
                async with rdb.db.lock:
                    rdb.db.index[user_id].groups.add(chat_id)
                return {"text": "🫂", "delete_user_message": True}
            else:
                return {"text": "🫂❌😔", "delete_user_message": True}

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
#/select .sudo add_models -tg_id param
async def sudo_manager(chat_id, event, value):
    try:
        if (
            not event.is_private
            or (
                event.is_private and chat_id not in conf.SUDO_LIST
                )
        ):
            return {"text": "🤐", "delete_user_message": True}

        import bot.src.handlers.database as rdb
        query_data = [vall.strip() for vall in value.split(" ")]
        if len(query_data) != 3:
            match query_data[0]:
                case "configs":
                    return {"text": conf.load_configurations(), "delete_user_message": False}
            return {"text": f"`{query_data}`\n\nIt isn't 3 parameters length...", "delete_user_message": False}
        arg = query_data[0]
        tg_id = query_data[1]
        valuables = query_data[2]

        if tg_id not in rdb.db.index:
            grClass = await rdb.db.grab_class(chat_id = tg_id, user_id = tg_id, make_group = True, private=True)
        else:
            grClass = rdb.db.index[tg_id]

        sudo_status = "LIMBO"

        match arg:
            case "add_models":
                for model in valuables.split(","):
                    grClass.allowed_models.add(model.strip())
                sudo_status = f'%%[{grClass.allowed_models}]%%'
            case "remove_models":
                if valuables.strip() in ["all"]:
                    grClass.allowed_models = set()
                else:
                    for model in valuables.split(","):
                        grClass.allowed_models.discard(model.strip())
                sudo_status = f'%%[{grClass.allowed_models}]%%'
            case "tier":
                old_tier = str(grClass.tier)
                new_tier = valuables.strip()
                grClass.tier = new_tier if new_tier in conf.PAID_PLANS else grClass.tier
                sudo_status = f"{old_tier} > {new_tier} "
                if grClass.tier == new_tier:
                    sudo_status += "🆗"
                else:
                    sudo_status += f"✖... {conf.PAID_PLANS.keys()}"
            case _:
                sudo_status = "❓"

        return {"text": sudo_status, "delete_user_message": False}
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")


async def p_language(thisShit, value):
    try:
        if value.lower() in ["none", "empty", "reset"]:
            value = None
        else:
            value = str(value).lower()
            if value and value not in iso_639_codes:
                value = {"text": f"⚠️**{value}**⚠️\n\n🧛", "file": iso_639_codes_txt, "disable_delete": True}
        thisShit.stt_language = value
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")

async def block_command(value, event, chat_id, user_id):
    import bot.src.handlers.database as rdb
    try:
        grp = None
        if chat_id not in rdb.db.index:
            grp = await rdb.db.grab_class(chat_id = chat_id, user_id = user_id, make_group = False, private=event.is_private)
        if (grp and not grp.group_mode) or (user_id not in rdb.db.index[chat_id].owners) or "select" in value:
            return {"text": "🤡", "delete_user_message": True}

        upd_comms = dict()

        for command in list(val.replace("/", "").strip() for val in value.split(" ")):
            command = f'/{command}'
            if command in upd_comms: continue
            elif command not in command_list:
                return {"text": f"{command} ⁉... 🙅‍♀️🖕", "delete_user_message": True}

            elif command in rdb.db.index[chat_id].blocked_commands:
                rdb.db.index[chat_id].blocked_commands.discard(command)
                upd = "✅"
            elif command not in rdb.db.index[chat_id].blocked_commands:
                rdb.db.index[chat_id].blocked_commands.add(command)
                upd = "🚫"

            upd_comms[command] = upd

        return {"text": "\n".join(f'- `{key}` {check}' for key, check in upd_comms.items()), "delete_user_message": True}
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
