from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc

from bot.src.tools.api_utils.call_tools.backends import smart_gsm

@openaifunc
async def search_smartphone_info(model: str) -> str:
    """
    Receives the device name and makes a search in the smart_gsm website returning all the device info.

    Args:
        model (str): only the device model, without extra text.

    Returns:
        str: all the device specifications to be tell to the user
    """
    if model:
        try:
            return await smart_gsm.get_device(query = model)
        except Exception: return ERRFUNC
    else: return FUNCNOARG
