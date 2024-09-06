from base64 import b64encode
from bot.src.tools.tg_tools import extract_media
from bot.src.tools.api_utils.gpt import quick_chat_completion, compress_image, c

async def do_vision(self, event, prompt, file_meta):
    file_meta = await extract_media(event, file_meta)
    mime_type=file_meta["mime"]
    if mime_type not in c.allowed_image_mimetypes:
        mime_type = "jpeg"
    image_bytes, file_name = await compress_image(file_meta["file"], file_name=file_meta["name"], mime_type=mime_type, quality=65)
    file_meta["name"] = file_name
    doc = f"data:image/{mime_type};base64,{b64encode(image_bytes.getvalue()).decode('utf-8')}"
    vision_response = await quick_chat_completion(self, self.vision_model, [
        {"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": doc}}
            ]}
        ], custom_params={"temperature": 0}
        )

    if vision_response == "Cancelled":
        return None, None
    return vision_response, file_meta
