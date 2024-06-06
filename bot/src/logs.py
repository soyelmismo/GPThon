import logging

name = "GPT"
level = logging.DEBUG

# Configurar el logger
logger = logging.getLogger(name)
logger.setLevel(level)

# Configurar el manejador de salida
handler = logging.StreamHandler()
handler.setLevel(level)

handler.setFormatter(logging.Formatter('%(name)s > %(message)s'))

# Agregar el manejador al logger
logger.addHandler(handler)

