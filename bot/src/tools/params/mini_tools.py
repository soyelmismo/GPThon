import bot.src.handlers.database as rdb
from bot.src import constants as c
from bot.src.config import bot_prompts, max_input_tokens
from random import choice
from bot.src.logs import logger
from bot.src.tools.api_utils import apis_frontend as oai
import bot.src.tools.api_utils.api_selector as api_datas
from hashlib import sha1
from re import compile, findall, split


from bot.src.tools.params.longAssDicts import shortened_args, img_ratios, iso_639_codes, iso_639_codes_txt
from sys import _getframe

#pattern = compile(r"(\s*\.|\n*\.)([a-zA-Z0-9]+(?:\s+[a-zA-Z0-9]+)*)") OK
pattern = compile(r"(\s+\.[a-zA-Z0-9]+(\s+[^\s.\/]|[\S])*)") #OK OK GOOOOD

async def extract_prompt_args(this):
    try:
        splat = findall(pattern, this)
        finds = [arg[0].strip()[1:] for arg in splat]
        return split(r'(?<!["\'`])[\s\n]\.(?!["\'`])', this)[0].strip(), finds
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        return this, None
    

async def extract_arg_value(item):
    arg, value = "", ""
    try:
        arg = str(item.split(" ")[0]).strip()
        arg = shortened_args.get(arg, arg)
        value = " ".join(item.split(" ")[1:]).strip()
        
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
    finally:
        return arg, value

async def manage_style(thisShit, style_name):
    style_prompt = None
    try:
        if style_name in ["r", "random", "a", "any"]:
            style_name = choice([e for e in c.img_styles.keys() if e not in ["general", "raw"]])
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
            

photos_err = f"👎🫵 `.photos` `1` - `4`"
async def p_photos(thisShit, value, arg):
    
    try:
        value = int(value)
        if value not in range(1, 5):
            value = photos_err

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = photos_err
    finally:
        thisShit.photos = value

ratios_err = f"👎🫵 {', '.join(f'`.r {ratio}`' for ratio in img_ratios.keys())}"

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

        if value:
            promptr = f'"{thisShit.prompt}"\n\nimportant feedback to implement: {value}'
        else:
            promptr = thisShit.prompt
        thisShit.conversation = [
            {"role": "system", "content": bot_prompts["img_improve"]},
            {"role": "user", "content": promptr}
            ]
        improved_prompt = await oai.quick_chat_completion(thisShit, user_id, thisShit.improve_model)

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
        value = await max_value_param(arg, float(value))
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = "🤡"
    finally:
        setattr(thisShit, arg, value)

async def max_value_param(arg, value):
    try:
        if arg in ["temperature"]:
            pmin, pmax = 0, 2
        elif arg in ["top_p"]:
            pmin, pmax = 0, 1
        elif arg in ["presence_penalty", "frequency_penalty"]:
            pmin, pmax = -2, 2
        else:
            pmin, pmax = 1024, max_input_tokens
        value = min(max(value, pmin), pmax)
    except Exception as e:
        e = f"{_getframe().f_code.co_name}: {str(e)}"
        logger.error(e)
        raise e
    finally:
        return abs(int(value)) if arg == "max_tokens" else value

async def p_auto_bool(thisShit, arg, value, just_return = None):
    try:
        if not value:
            value = not getattr(thisShit, arg)
        else:
            value = value.lower() == 'true'
    except Exception as e:
        e = f"{_getframe().f_code.co_name}: {str(e)}"
        logger.error(e)
        raise e
    finally:
        if not just_return:
            setattr(thisShit, arg, value)
        else:
            return value

model_types = ["chat_model", "vision_model", "improve_model", "embedding_model", "tool_model", "tts_voice"]

forbidden = {"text": "🚫🔞🚫"}
async def p_models(thisShit, arg, value):
    try:
        if not thisShit.roleplaying:
            models_dict = (
                            c.img_models if arg in ["img_model"]
                            else c.embed_models if arg in ["embedding_model"]
                            else c.speech_voices if arg in ["tts_voice"]
                            else c.chat_models
                            )
            if models_dict:
                if value in ["r", "random", "a", "any"]:
                    models_list = list(models_dict.keys())
                    while True:
                        selected_model = choice(models_list)
                        if len(models_dict[selected_model]) == 1 and models_dict[selected_model][0] == "fresed" and "fresed" in api_datas.rate_limited:
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
                    if not value:
                        text = "😒"
                    else:
                        text = f"⚠️**{value}**⚠️\n\n😒"

                    value = {"text": text, "file": models_file, "force_document": True, "disable_delete": True}

        else:
            value = forbidden
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
        value = forbidden
    finally:
        setattr(thisShit, arg, value)


async def p_sysprompt(cls, thisShit, value, event, user_id):
    try:
        if thisShit.roleplaying:
            thisShit.warning = "🫵🤡🤣"
            return
        elif value:
            if value == "reset":
                value = ""
                thisShit.sysprompt = str(value)
            else:
                thisShit.sysprompt = str(value)
            cls.sysprompt = thisShit.sysprompt
        else:
            value = cls.sysprompt

        await cls.delete_conversation(event, user_id, 0, notify = 1)
        return value
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")


async def p_seed(thisShit, value):
    try:
        if value == "None":
            value = None
        else:
            try:
                value = int(value)
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
async def p_group(thisShit, arg, value, chat_id, user_id):
    try:
        if chat_id == user_id:
            return {"text": "🤡 🫂❓", "delete_user_message":True}
        if not (await is_integer_string(value)):
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
                        return {"text": f"🤣🫵🤣🫵🤣🫵💩💩💩"}
            else:
                return {"text": "🫂🔥 🚫", "delete_user_message": True}
        elif arg == "group_mode" and value:
            grClass = await rdb.db.grab_class(chat_id = chat_id, user_id = user_id, make_group = True)
            if user_id in grClass.owners:
                async with rdb.db.lock:
                    rdb.db.index[user_id].groups.add(chat_id)
                return {"text": "🫂", "delete_user_message": True}
            else:
                return {"text": "🫂❌😔", "delete_user_message": True}

    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")

async def p_language(thisShit, value):
    try:
        if value == "None":
            value = None
        else:
            value = str(value).lower()
            if value and value not in iso_639_codes:
                value = {"text": f"⚠️**{value}**⚠️\n\n🧛", "file": iso_639_codes_txt, "disable_delete": True}
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")
    finally:
        thisShit.stt_language = value
