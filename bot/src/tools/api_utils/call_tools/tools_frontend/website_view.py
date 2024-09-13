from bot.src.constants import ERRFUNC, FUNCNOARG
from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends.website_view import extract_from_url

@openaifunc
async def read_a_website(url: str) -> str:
    """
    Open a website.
    Reveives an url to open. talk freely about the website content.
    Give the relevant data to the user.

    Args:
        url (str): the url to be grabbed
    
    Returns:
        str: website text
    """

    if url:
        try:
            return await extract_from_url(url = url)
        except ValueError:
            return "Website is too big to be loaded. Sorry."
        except Exception:
            return ERRFUNC
    else: return FUNCNOARG
