from bot.src.tools.api_utils.call_tools.functions_extraction import openaifunc
from bot.src.tools.api_utils.call_tools.backends import duckduckgo, brave_search
from bot.src.logs import log_error, logger
from sys import _getframe
from bot.src.config import BRAVE_SEARCH_APIKEY
from bot.src.constants import FUNCNOARG


ENGINES = {
        "duckduckgo": duckduckgo.search,
    }

if BRAVE_SEARCH_APIKEY:
    ENGINES["brave_search"] = brave_search.search

@openaifunc
async def search_on_internet(query: str, search_type: str, timelimit: str, max_results: int = 3, region: str = "wt-wt", **kwargs) -> str:
    """
    Search information and news on internet
    User gives a sentence or word query to search information and recommendations on the web. talk freely about the results and provide the sources.
    Give the found sources to the user.

    Args:
        query (str): the keywords that will be searched
        search_type (str): can be "text", "news", "videos". depending of what the user has requested.
        timelimit (str): use "d" if latest results from today, for other time limits: "w", "m", "y". depends of what the user requested.
        max_results (int): from 1 to 5.
        region (str): wt-wt, us-en, uk-en, ru-ru, etc. MANDATORY. select the region corresponding to the language of the query.

    Returns:
        str: the search / news results to inform the user
    """

    if query:
        results = None
        errors = []
        for engine_name, engine_func in ENGINES.items():
            try:
                results = await engine_func(
                    query=str(query),
                    timelimit=str(timelimit) if timelimit else None,
                    type=str(search_type),
                    max_results=int(max_results),
                    region=str(region)
                )
                if results:
                    break
            except Exception as e:
                errors.append((engine_name, str(e)))
                logger.error(f'{str(e)}: {await log_error(_getframe().f_code.co_name, **locals())}')


        if not results:
            error_details = "; ".join([f"{name}: {msg}" for name, msg in errors])
            raise Exception(f"No results. Errors: {error_details}")
        
        return results

    else: return FUNCNOARG
