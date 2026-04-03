import logging

name = "|"
level = logging.INFO

# Configurar el logger
logger = logging.getLogger(name)
logger.setLevel(level)

# Configurar el manejador de salida
handler = logging.StreamHandler()
handler.setLevel(level)

handler.setFormatter(logging.Formatter('%(name)s > %(message)s'))

# Agregar el manejador al logger
logger.addHandler(handler)

async def log_error(func_name, **kwargs):
    error_msg = f"{func_name} - Arguments: "
    for key, value in kwargs.items():
        error_msg += f"{key}={value}, "
    return error_msg[:-2]