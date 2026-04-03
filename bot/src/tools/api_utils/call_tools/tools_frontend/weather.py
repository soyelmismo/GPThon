from bot.src.constants import FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import wttr
from bot.src.logs import log_error
from sys import _getframe


@openaifunc
async def lookup_weather(location: str, unit: str, **kwargs) -> str:
    """
    Search actual weather info.
    The user ask for weather and you search here for the city he requested.
    You give detailed information about the actual weather.

    Args:
        location (str): the city. mandatory.
        unit: "C" or "F". mandatory, and depends of the city

    Returns:
        str: all the weather info to be tell to the user
    """
    if location:
        try:
            return await wttr.getweather(location = str(location), unit = str(unit))
        except Exception as e:
            raise Exception(f'{str(e)}: {await log_error(_getframe().f_code.co_name, **locals())}')
    else: return FUNCNOARG
