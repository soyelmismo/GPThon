from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc

from bot.src.tools.api_utils.call_tools.backends import smart_gsm

@openaifunc
async def search_smartphone_specs(model: str, **kwargs) -> str:
    """
    Receives the device name and makes a search in the smart_gsm website returning all the device specifications.
    Inform the user in a detailed way the features of the device.

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
