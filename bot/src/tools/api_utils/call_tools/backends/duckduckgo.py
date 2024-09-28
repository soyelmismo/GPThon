from duckduckgo_search import DDGS

class Results():
    """Packs the results to easy drive while parsing"""
    def __init__(self, results) -> None:
        self.results_data: list = results
        self.formatted: str = str()

async def search(
        query=None, timelimit: str = None,
        type='text', max_results = 3, region = "wt-wt"):
    try:
        if not query: return "No results found..."
        if type not in ["text", "news", "videos"]: type = "text"
        #resultados=[]
        with DDGS() as ddgs:
            max_results = int(max_results) if int(max_results) != 1 else 3
            ddgs_gen = getattr(ddgs, type)(keywords=query, safesearch='off', timelimit=timelimit, max_results=min(max_results, 5), region = region)

        data_instance = Results(ddgs_gen)
        match type:
            case "text" | "news":
                await parse_text_news_search(data_instance, type)
            case "videos":
                await parse_video_search(data_instance)
        return data_instance.formatted
    except Exception as e: raise ConnectionError(e)

async def parse_text_news_search(data: Results, type: str):
    for result in data.results_data:
        title = f'{result["title"]}' + f' by {result["source"]}' if type == "news" else ''
        href = result['href'] if type == "text" else result['url']
        body = result['body']
        data.formatted += f"- {title}: {body}: give this to user: {href}\n\n"
    
async def parse_video_search(data: Results):
    for result in data.results_data:
        title = f'{result["title"]} by {result["uploader"]}'
        url = result['content']
        description = result['description']
        duration_and_uploaded = f' ({result["duration"]}) date: {result["published"].split("T")[0]}'
        data.formatted += f"- {title}: {description}... {duration_and_uploaded}: give this to user: {url}\n\n"