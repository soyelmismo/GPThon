import cv2
import numpy as np
import tempfile
from PIL import Image
from bot.src.logs import logger
from bot.src.config import vision_max_images_seq

async def extract_photos(bytes, mime):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{mime}') as temp_file:
            temp_file.write(bytes)
            temp_file_path = temp_file.name

        cap = cv2.VideoCapture(temp_file_path)

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Definir número de imágenes dependiendo de total_frames
        IMAGES_QUANTITY = min(total_frames, vision_max_images_seq)

        frames_to_extract = [int(total_frames * i / IMAGES_QUANTITY) for i in range(IMAGES_QUANTITY)]

        frames = []
        for frame_num in frames_to_extract:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
            ret, frame = cap.read()

            if ret:
                frames.append(frame)
            else:
                logger.error(f"extract_photos: can't read frame: {frame_num}")

        cap.release()

        if not len(frames):
            logger.error("extract_photos: couldn't extract images.")
            return None

        height, width, _ = frames[0].shape
        resized_frames = [cv2.resize(frame, (width, height)) for frame in frames]

        # Crear cuadrícula automáticamente según los frames que tengamos
        grid_size = int(np.ceil(np.sqrt(len(frames))))

        # Añadir imágenes negras si es necesario para completar la cuadrícula
        while len(resized_frames) < grid_size ** 2:
            resized_frames.append(np.zeros_like(resized_frames[0]))
        
        # Crear filas para la cuadrícula
        rows = [np.hstack(resized_frames[i*grid_size:(i+1)*grid_size]) for i in range(grid_size)]

        # Combinar las filas para obtener la imagen final
        grid_image = np.vstack(rows)

        return Image.fromarray(cv2.cvtColor(grid_image, cv2.COLOR_BGR2RGB))

    except Exception as e:
        logger.error(f"couldn't extract images correctly from video: {str(e)}")
        return None
