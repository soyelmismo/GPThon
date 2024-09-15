from .mini_tools import *

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
            case "download":
                file = await get_conversation(thisShit, user_id=user_id)
                thisShit.warning = {"text": "🫡", "file": file, "force_document": True, "disable_delete": True}
                break
            case "status":
                thisShit.warning = {"text": f'```\n{cls.to_string()}```', "disable_delete": True}
                break
            case "group_mode" | "random_names":
                value = await p_group(cls, arg, value, chat_id, user_id)
                if isinstance(value, dict):
                    thisShit.warning = value
                    break
            case "seed":
                await p_seed(thisShit, value)
            case "rol":
                await roleplay(event, user_id, chat_id, command)
                value = "🔞🔥"
            case "sysprompt":
                value = await p_sysprompt(cls, thisShit, value, event, user_id)
                if thisShit.warning:
                    break
            case "streaming" | "debug" | "memory" | "randomizer" | "answer_stt" | "summarize" | "transcribe" | "tool_call" | "to_tts" | "raw":
                await p_auto_bool(thisShit, arg, value)

            case "chat_model" | "img_model" | "improve_model" | "vision_model" | "embedding_model" | "tool_model" | "tts_voice":
                await p_models(thisShit, arg, value)
                checkIt = getattr(thisShit, arg)
                if isinstance(checkIt, dict):
                    thisShit.warning = checkIt
                    break

            case "temperature" | "top_p" | "frequency_penalty" | "presence_penalty" | "max_tokens":
                await p_floats(thisShit, arg, value)
                checkIt = getattr(thisShit, arg)
                if isinstance(checkIt, str):
                    thisShit.warning = checkIt
                    break

            case "photos":
                await p_photos(thisShit, value, arg)
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
                await p_improve(thisShit, user_id)
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

