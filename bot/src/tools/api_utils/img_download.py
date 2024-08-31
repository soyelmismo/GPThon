from httpx import AsyncClient
from io import BytesIO
from PIL.Image import open
from random import randint
import asyncio

async def download_image(client, url):
    response = await client.get(url)
    if response.status_code == 200:
        img = BytesIO(response.content)
        img.seek(0)

        # Abrir la imagen con PIL
        image = open(img)

        # Crear un buffer para la imagen en formato JPEG
        img_jpeg = BytesIO()
        
        # Guardar la imagen en el buffer con formato JPEG y la calidad especificada
        image.save(img_jpeg, format='JPEG', quality=85)
        
        # Reiniciar el puntero al principio del buffer
        img_jpeg.seek(0)
        
        # Generar un ID aleatorio de 8 dígitos
        random_id = randint(0, 99999999)
        img_jpeg.name = f'{random_id}.jpeg'

        return img_jpeg
    return None


async def download_images(urls):
    images = []
    async with AsyncClient() as client:
        tasks = [download_image(client, url) for url in urls]
        images = await asyncio.gather(*tasks)
    return [img for img in images if img is not None]
