from base64 import b64encode
from bot.src.tools.api_utils.apis_frontend import quick_chat_completion

from bot.src.tools.general_tools.videosplit import extract_photos
from bot.src.tools.general_tools.image_tools import compress_image
from bot.src.tools.tg_tools import extract_media, edit_msg
from bot.src.config import allowed_image_mimetypes

async def do_vision(self, event, user_id, prompt, placeholder_msg, buttons, file_meta: dict):
    file_meta = await extract_media(event, file_meta)
    mime_type = file_meta["mime"]
    image_bytes = file_meta["file"]
    if mime_type not in allowed_image_mimetypes:
        mime_type = "jpeg"
    if mime_type == "webm":
        image_bytes = await extract_photos(file_meta["file"], file_meta["mime"])
        mime_type = "jpeg"
        sequence_prompt = "what happens in this sequence of images?\n\n"
        prompt = f'{sequence_prompt}{prompt}'
    image_bytes, file_name = await compress_image(image_bytes, file_name=file_meta["name"], mime_type=mime_type, quality=55)
    file_meta["name"] = file_name
    doc = f"data:image/{mime_type};base64,{b64encode(image_bytes.getvalue()).decode('utf-8')}"
    await edit_msg(event, placeholder_msg, "👁️⏳...", buttons)

    self.conversation = [
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": doc, "detail": "high"}}
            ]}
        ]
    self.max_tokens = 4095
    vision_response = await quick_chat_completion(self, user_id, self.vision_model)
    if not vision_response:
        await edit_msg(event, placeholder_msg, "📷😔❌")
    elif vision_response == "Cancelled":
        await placeholder_msg.delete()
        return None, file_meta
    return vision_response, file_meta
