from random import randint
from bot.src.config import allowed_image_mimetypes
from io import BytesIO
from PIL import Image
from asyncio import gather
from httpx import AsyncClient



async def download_images_list(urls, thisShit = None):
    if not urls:
        raise IndexError("No images received")
    images = []
    resolutions = []
    async with AsyncClient() as client:
        tasks = [download_image(client, url, thisShit) for url in urls]
        results = await gather(*tasks)

    for img_data, resolution in results:
        if img_data is not None:
            images.append(img_data)
            resolutions.append(resolution)
    return images, resolutions

async def download_image(client, url, thisShit = None):
    response = await client.get(url)
    if response.status_code == 200:
        img_data, _, resolution = await compress_image(response.content, black_check=True, thisShit = thisShit)
        return img_data, resolution
    return None, None



async def compress_image(img, black_check = None, file_name = None, mime_type = None, quality = 95, thisShit = None):
    try:
        if isinstance(img, Image.Image):  # Verifica si img ya es un objeto PIL.Image
            image = img
        else:
            # Si img no es un objeto PIL.Image, conviértelo a BytesIO y ábrelo como imagen
            img = BytesIO(img)
            img.seek(0)
            image = Image.open(img)

        if black_check:
            image_gray = image.convert('L')

            if await is_black_image(image_gray):
                raise Exception("Black image detected.")

        img_bytes = BytesIO()

        if mime_type == "webm" or mime_type not in allowed_image_mimetypes:
            mime_type = "jpeg"

        #if not black_check and image.width > 1000 or image.height > 1000:
            #image.thumbnail((1000, 1000))

        if thisShit and thisShit.raw:
            quality = 100
            mime_type = "png"

        resolution = f"{image.size[0]}×{image.size[1]}"
        image.save(img_bytes, format=mime_type, quality=quality)
        img_bytes.seek(0) # type: ignore

        if not file_name:
            random_id = randint(0, 99999999)
            file_name = f'{random_id}.{mime_type}'
            
            img_bytes.name = file_name
        
        return img_bytes, file_name, resolution
    except Exception as e:
        raise Exception(f'compress_image: {e}')

async def is_black_image(image, block_size=1024):
    width, height = image.size
    
    for y in range(0, height, block_size):
        for x in range(0, width, block_size):
            box = (x, y, min(x + block_size, width), min(y + block_size, height))
            block = image.crop(box)
            pixels = block.getdata()
            if any(pixel != 0 for pixel in pixels):
                return False 

    return True 
