from bot.src.constants import FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends.website_view import extract_from_url
from bot.src.logs import log_error
from sys import _getframe


@openaifunc
async def read_a_website(url: str, **kwargs) -> str:
    """
    Open a website provided only by the user.
    Reveives an url from the user to open. talk freely about the website content.
    Give the relevant data to the user.

    Args:
        url (str): the url to be grabbed
    
    Returns:
        str: website text
    """

    if url:
        try:
            return await extract_from_url(url = str(url))
        except ValueError:
            return "Website is too big to be loaded. Sorry."
        except Exception as e:
            raise Exception(f'{str(e)}: {await log_error(_getframe().f_code.co_name, **locals())}')
    else: return FUNCNOARG
