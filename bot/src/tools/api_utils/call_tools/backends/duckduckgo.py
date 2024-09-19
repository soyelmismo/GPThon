from duckduckgo_search import DDGS

async def search(query=None, gptcall=None, timelimit: str = None, type='text', max_results = 3):
    try:
        if not query: return "No results found..."
        #resultados=[]
        with DDGS() as ddgs:
            if type == "text":
                fn = ddgs.text
            else:
                fn = ddgs.news
            ddgs_gen = fn(keywords=query, safesearch='Off', timelimit=timelimit, max_results=min(max_results, 5))
            #for r in islice(ddgs_gen, 10): resultados.append(r)
        formatted_backend = []
        formatted_results = []
        for resultado in ddgs_gen:
            title = resultado['title']
            href = resultado['href'] if type == "text" else resultado['url']
            body = resultado['body']
            formatted_result = f"- [{title}]({href}): {body}"
            backend_result = f"[{title}]({href}): {body}"
            formatted_results.append(formatted_result)
            formatted_backend.append(backend_result)
        formatted_results_string = '\n\n'.join(formatted_results)
        formatted_results_backend = '\n\n'.join(formatted_backend)
        if gptcall == True:
            return formatted_results_backend
        else:
            return formatted_results_backend, formatted_results_string
    except Exception as e: raise ConnectionError(e)