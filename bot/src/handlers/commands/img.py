import bot.src.tools.api_utils.gpt as gptools
from asyncio import wait_for, CancelledError
from bot.src.handlers.commands.tasks import add_task, gen_cancel_button as gcb
from bot.src.logs import logger
import bot.src.constants as c
from . import remove_command, bot_prompts
from random import choice

avail_args = {
    "img_model",
    "photos",
    "style",
    "improve_prompt",
    "improve_model",
    "ratio"

}


shortened_args = {
    "m": "img_model",
    "im": "img_model",
    "p": "photos",
    "n": "photos",
    "q": "photos",
    "r": "ratio",
    "s": "style",
    "i": "improve_prompt",
    "improve": "improve_prompt",
    "tim": "improve_model"
}

ratios = {
    "1x1": "1024x1024",
    "16x9": "1920x1080",
    "21x9": "2560x1080",
    "3x2": "1800x1200",
    "2x3": "1200x1800",
    "4x5": "1280x1600",
    "5x4": "1600x1280",
    "9x16": "1080x1920",
    "9x21": "1080x2520"
}


warning = f"👎🫵 {', '.join(f'`.{arg}`' for arg in avail_args)}"

async def manage_style(style, params_dict, prompt):
    prompt_value = c.img_styles.get(style)
    if prompt_value:
        params_dict["style"] = [style, str(prompt_value).replace("{p}", prompt)]

    else:
        if c.img_styles_txt:
            prompt = {"message": "😒", "file": c.img_styles_txt, "force_document": True}

    return params_dict, prompt

async def extract_arguments(self, prompt, new_params = {}):

    parts = prompt.split(" .")
    prompt = parts[0]
    args = parts[1:]


    args_tried = []
    selected_style = "raw"
    for item in args:
        arg = str(item.split(" ")[0]).strip()
        arg = shortened_args.get(arg, arg)
        if arg in args_tried:
            continue
        value = " ".join(item.split(" ")[1:]).strip()
        ok = False
        match arg:
            case "img_model":
                if c.img_models:
                    if value in ["r", "random", "a", "any"]:
                        value = choice(list(c.img_models.keys()))
                    elif not value or value not in c.img_models:
                        prompt = {"message": "😒", "file": c.img_models_txt, "force_document": True}
                        break
                ok = True
            case "improve_model":
                if c.chat_models and (not value or value not in c.chat_models):
                    prompt = {"message": "😒", "file": c.chat_models_txt, "force_document": True}
                    break

                self.improve_model = value
                ok = True
            case "photos":
                try:
                    value = int(value)
                    if value >= 1 or value <= 4:
                        ok = True
                except:  # noqa: E722
                    return f"👎🫵 .{arg} 1-4"

            case "ratio":
                value = ratios.get(value)
                if value:
                    ok = True
                else:
                    return f"👎🫵 {', '.join(f'`.r {ratio}`' for ratio in ratios.keys())}"
            case "style":
                if value in ["r", "random", "a", "any"]:
                    selected_style = choice([e for e in c.img_styles.keys() if e not in ["general", "raw"]])
                else:
                    selected_style = str(value)
                continue
            case "improve_prompt":
                improved_prompt = await gptools.quick_chat_completion(self, self.improve_model, [
                    {"role": "system", "content": bot_prompts["img_improve"]},
                    {"role": "user", "content": prompt}
                    ]
                    )
                if improved_prompt == "Cancelled":
                    return None
                elif improved_prompt:
                    prompt = improved_prompt
                    ok = True
            case _:
                return warning

        if ok:
            new_params[arg] = value
            args_tried.append(arg)
        else:
            return warning
    if isinstance(prompt, str):
        new_params, prompt = await manage_style(selected_style, new_params, prompt)

    if not isinstance(prompt, dict):
        if len(prompt) < 1:
            return "🎨❓"
        elif len(prompt) > 999:
            prompt = prompt[:999]
    return {"params": new_params, "prompt": prompt}


async def editmsg(event, msg, text):
    return await event.client.edit_message(entity = event.chat_id, message = msg, text = text)

async def img_wrap(self, event, user_id, command, task_id):
    prompt = await remove_command(self.conversation, event, command)

    placeholder_msg = await event.reply("🤔🎨, 🖐️⏳...", buttons = gcb(command, task_id))
    
    params = {
        "img_model": str(self.img_model),
        "ratio": "1024x1024",
        "photos": 1
        }
    new_params = await extract_arguments(self, prompt, params)
    if not new_params:
        return
    if isinstance(new_params, str):
        return await editmsg(event, placeholder_msg, new_params)
    elif isinstance(new_params["prompt"], dict):
        await placeholder_msg.delete()
        new_params["prompt"]["file"].seek(0) # type: ignore
        return await event.reply(**new_params["prompt"])


    task = do_img(self, new_params["params"]["img_model"], user_id, event, new_params, placeholder_msg, command)
    msg = await add_task(command, user_id, task, task_id)
    if msg == "CantAddMore":
        return await editmsg(event, placeholder_msg, "🫵🤬, 🖐️⏳... 🖕.")
    return

async def do_img(self, actual_model, user_id, event, prompt, placeholder_msg, command):

    models_to_check = c.img_models.keys() if not c.img_models.get(actual_model) else [actual_model]
    img_pending = True
    response = None
    while img_pending:
        for model in models_to_check:
            temp_apis = await gptools.shuffle_apis(user_id, model, command)
            logger.debug(f"apis for images {temp_apis}")
            for img_api in temp_apis:
                try:
                    responseapi = gptools.call_api(self, type = command, media = prompt, api = img_api, model = actual_model)
                    response, nprompt = await wait_for(responseapi.__anext__(), 60) # type: ignore
                    prompt["prompt"] = nprompt
                except CancelledError:
                    await placeholder_msg.delete()
                    img_pending = False
                    return
                except:  # noqa: E722
                    continue

                if isinstance(response, list):
                    async with event.client.action(entity=event.chat_id, action='photo'):
                        caption = await make_caption(prompt)
                        await event.reply(caption,
                                        file=response,
                                        force_document=False,
                                        )

                    img_pending = False
                    break
        else:
            break
    if img_pending:
        await event.reply("🎨 😔❌👍")
    await placeholder_msg.delete()
    return

async def make_caption(data):
    caption = ""
    if len(data["prompt"]) < 800:
        caption += f'✍️ `{data["prompt"]}`\n\n'
    if data["params"].get("style"):
        caption += f'👗 `{data["params"]["style"][0]}`\n'
    caption += f'🤖 `{data["params"]["img_model"]}`'
    caption += f'\n📐 `{data["params"]["ratio"]}`'
    return caption
