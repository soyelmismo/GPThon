from bot.src.config import (
command_image, command_stt
)

from bot.src.tools.params.tempclass import gotClass
from bot.src.handlers.commands.rol import roleplay
from bot.src.tools.tg_tools import send_msg

from bot.src.tools.other_tools import get_conversation


from bot.src.tools.params.longAssDicts import (
    all_args, allowed_in_groups,
    allowed_no_value, warnings
)
from bot.src.tools.params.mini_tools import (
    p_auto_bool, p_floats, p_group, p_improve, p_language, p_models,
    p_photos, p_ratio, p_seed, p_sysprompt, manage_style, extract_arg_value,
    extract_prompt_args, final_img_step, sudo_manager
)

async def extract_arguments(cls, event, prompt, command, user_id, chat_id = None, file_meta = None):
    warning = warnings.get(command)
    prompt, args = await extract_prompt_args(f' {prompt}')
    thisShit = await gotClass(cls, command, prompt)
    if command == "/select" and not args:
        thisShit.warning = warning
    elif command == command_image and (not prompt or len(prompt) < 5):
        thisShit.warning = "🎨❓"
    elif command == command_stt and (not file_meta or file_meta["type"] not in ["audio", "transcription"]):
        thisShit.warning = '🎤❔'


    args_tried = []

    for item in args:
        arg, value = await extract_arg_value(item)
        if command in all_args and (
            (not value and arg not in allowed_no_value)
            or arg not in all_args[command]
            ):
            thisShit.warning = f'⚠️**.{arg}**⚠️\n\n{warning}'
            break
        if thisShit.group_mode and arg not in allowed_in_groups and user_id not in thisShit.owners:
            thisShit.warning = "🫂 🚫"
            break


        if arg in args_tried:
            continue

        match arg:
            case "sudo":
                thisShit.warning = await sudo_manager(chat_id, event, value)
                break
            case "download":
                if command == "/select":
                    file = await get_conversation(thisShit, user_id=user_id)
                    thisShit.warning = {"text": "🫡", "file": file, "force_document": True, "disable_delete": True}
                else:
                    thisShit.download = True
                    continue
                break
            case "status":
                thisShit.warning = {"text": f'%%\n{await cls.to_string()}%%', "disable_delete": True}
                break
            case "group_mode" | "random_names" | "authorize" | "deauthorize":
                value = await p_group(cls, event, arg, value, chat_id, user_id)
                if isinstance(value, dict):
                    thisShit.warning = value
                    break
            case "seed":
                await p_seed(thisShit, value)
            case "rol":
                await roleplay(event, user_id, chat_id, command)
                value = "🔞🔥"
            case "sysprompt":
                value = await p_sysprompt(cls, thisShit, value[:1024], event, user_id, command)
                if thisShit.warning:
                    break
            case "streaming" | "debug" | "memory" | "randomizer" | "answer_stt" | "summarize" | "transcribe" | "tool_call" | "to_tts" | "raw" | "forget":
                await p_auto_bool(thisShit, arg, value)
                if thisShit.warning:
                    break

            case "chat_model" | "img_model" | "improve_model" | "vision_model" | "embedding_model" | "tool_model" | "tts_voice":
                await p_models(thisShit, chat_id, user_id, arg, value)
                checkIt = getattr(thisShit, arg)
                if isinstance(checkIt, dict):
                    thisShit.warning = checkIt
                    break

            case "temperature" | "top_p" | "frequency_penalty" | "presence_penalty" | "max_tokens" | "timeout" | "output_tokens":
                await p_floats(thisShit, arg, value)
                checkIt = getattr(thisShit, arg)
                if isinstance(checkIt, str):
                    thisShit.warning = checkIt
                    break

            case "photos":
                await p_photos(thisShit, value)
                if not isinstance(thisShit.photos, int):
                    thisShit.warning = thisShit.photos
                    break

            case "ratio":
                await p_ratio(thisShit, value)
                if ".r" in thisShit.ratio:
                    thisShit.warning = thisShit.ratio
                    break

            case "style_name":
                await manage_style(thisShit, value)
                if isinstance(thisShit.style_name, dict):
                    thisShit.warning = thisShit.style_name
                    break
                #continue

            case "improve_prompt":
                await p_improve(thisShit, user_id, value)
                if isinstance(thisShit.prompt, list):
                    thisShit.warning = thisShit.prompt[0]
                    break
            case "stt_language":
                await p_language(thisShit, value)
                if not isinstance(thisShit.stt_language, str):
                    thisShit.warning = thisShit.stt_language

            case _:
                thisShit.warning = warning
                break

        if command == "/select":
            thisShit.notification += f'.{arg}: {getattr(thisShit, arg)} ✅\n'
        args_tried.append(arg)

    if command == command_image and not thisShit.warning:
        await final_img_step(thisShit)
    if thisShit.warning:
        if isinstance(thisShit, str):
            await send_msg(event, thisShit, disable_delete=True)
        elif isinstance(thisShit.warning, str):
            await send_msg(event, thisShit.warning, disable_delete=True)
        elif isinstance(thisShit.warning, dict):
            await send_msg(event, **thisShit.warning)
        return None
    return thisShit

