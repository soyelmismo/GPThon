
from bot.src.logs import logger
from asyncio import CancelledError
from bot.src.tools.api_utils.api_selector import select_api_data, shuffle_apis, update_total_reqs


import bot.src.constants as c



async def request_embedding(thisShit, model, user_id, command):
    response = None
    try:
        models_to_check = c.embed_models if not c.embed_models.get(thisShit.embedding_model) else [thisShit.embedding_model]
        embed_pending = True
        logger.debug("Set-up embeddings payload")
        payload = {
            "input": thisShit.conversation[-1]["content"].strip(),
            "model": model,
            "timeout": 5
        }
        while embed_pending:
            for model in models_to_check:
                temp_apis = await shuffle_apis(user_id, model, command)
                logger.debug(f"apis for embedding {temp_apis}")
                for api in temp_apis:
                    try:
                        logger.debug(f"Joining embeddings with {api}")
                        res_text = []
                        logger.debug("Generating embedding...")
                        client = await select_api_data(api)
                        tok = 0
                        try:
                            response = await client.embeddings.create(**payload)
                        except CancelledError as e:
                            if "nDDñd" not in str(e):
                                continue
                            else:
                                raise e
                        res_text = response.data[0].embedding
                        if not res_text:
                            raise ValueError(f'"{res_text}" inexistent')
                        try:
                            tok += response.usage.total_tokens
                        except:
                            tok += 1
                        thisShit.used_tokens += tok
                        await update_total_reqs(command, api, model, user_id, 1)
        
                        yield res_text, "stop"
                        embed_pending = False
                    except CancelledError as e:
                        embed_pending = False
                        raise e
                    except Exception as e:
                        await update_total_reqs(command, api, model, user_id, 0, response, e)
                        logger.error(f"embeddings exception: {str(e)}... {response}")
                        continue
                else:
                    logger.error(f"all apis for embedding, {model} failed.")
                    
            else:
                embed_pending = False
                yield "🎨 😔❌👍", "fail"
    except Exception as e:
        raise ConnectionAbortedError(f"embeddings exception: {str(e)}... {response}")


