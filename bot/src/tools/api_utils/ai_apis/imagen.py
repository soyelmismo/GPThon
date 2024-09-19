from asyncio import CancelledError
from bot.src.logs import logger

from bot.src.tools.general_tools.image_tools import download_images_list
from bot.src.tools.api_utils.api_selector import select_api_data, shuffle_apis, update_total_reqs, api_reqs

import bot.src.constants as c


async def generate_image(thisShit, model, user_id, command):
    response = None
    img_pending = True
    images = None
    models_to_check = c.img_models.keys() if not c.img_models.get(thisShit.img_model) else [thisShit.img_model]
    while img_pending:
        for model in models_to_check:
            temp_apis = await shuffle_apis(user_id, model, command)
            logger.debug(f"apis for images {temp_apis}")
            for img_api in temp_apis:
                try:
                    logger.debug(f"Joining image generation with {img_api}")
                    if thisShit.style_data:
                        temp_prompt = thisShit.style_data[1]
                    else:
                        temp_prompt = thisShit.prompt

                    client = await select_api_data(img_api)
                    try:
                        response = await client.images.generate(
                            model=model,
                            prompt=temp_prompt,
                            size=thisShit.ratio,
                            n=thisShit.photos,
                            quality="hd",
                            timeout=60
                        )
                    except CancelledError as e:
                        if "Cancelled by user." not in str(e):
                            continue
                        else:
                            raise e
                    logger.debug(response)

                    if not isinstance(response, str):
                        images = response.data
                        img_list = []
                        if isinstance(images, list):
                            for i in images:
                                img_list.append(i.url)
                        img_list, resolutions = await download_images_list(img_list, thisShit)
                        img_prompt = response.data[0].revised_prompt or thisShit.prompt
                    logger.debug(img_list)

                    logger.debug("Received, yielding")
                    await update_total_reqs(command, img_api, model, user_id, 1)
                    yield img_list, resolutions, img_prompt
                    img_pending = False
                except CancelledError as e:
                    img_pending = False
                    raise e
                except Exception as e:
                    await update_total_reqs(command, img_api, model, user_id, 0, response, e)
                    logger.error(f"image generation exception: {str(e)}... {response}")
                    continue
            else:
                logger.error(f"all apis for imagen, {model} failed.")
                img_pending = False
        else:
            img_pending = False
        break
    yield "🎨 😔❌👍", None, "fail"