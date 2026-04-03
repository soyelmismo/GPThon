from asyncio import CancelledError, sleep
from random import uniform
from sys import _getframe
from json import loads
from copy import deepcopy
from openai import APITimeoutError

from bot.src.logs import logger
from bot.src.config import command_chat
from bot.src.constants import ERRFUNC
from bot.src.tools.api_utils.ai_apis.shared_vars import total_tokens
from bot.src.tools.api_utils.api_selector import select_api_data, shuffle_apis, update_total_reqs

from bot.src.tools.api_utils.call_tools.functions_extraction import get_openai_funcs
from bot.src.tools.other_tools import calculate_token_length

functions_called_stats = {}

imported_functions = get_openai_funcs(return_function_objects = True)
functions_data = get_openai_funcs()

async def fuk_collector(tools):
    collect = []
    for fuk in tools:
        collect.append({
            "id": fuk.id,
            "name": fuk.function.name,
            "args": loads(fuk.function.arguments)
        })
    return collect

async def manage_non_stream_response(thisShit, res_text, response):
    global total_tokens

    try:
        if thisShit.tool_call and response.choices[0].message.tool_calls:
            yield response.choices[0].message.tool_calls, "stall"

        logger.debug("No streaming...")
        res_text += response.choices[0].message.content
        if not res_text: 
            raise ValueError(f'"res_text" inexistent')

        tok = await calculate_token_length(res_text)

        total_tokens += tok
        thisShit.used_tokens += tok
        yield res_text, "stop"
    except Exception as e:
        raise Exception(f"{_getframe().f_code.co_name}: {str(e)}")


async def process_function_data(functions, payload):
    for func in functions:
        tries = 0
        error = 0
        while True:
            try:
                f = func.function
                response = await imported_functions[f.name](**loads(f.arguments))
            except Exception as e:
                logger.error(f'{f}: retrying {tries}: {str(e)}')
                if tries > 2:
                    error = 1
                    response = ERRFUNC
                else:
                    tries += 1
                    await sleep(0.2)
                    continue
            payload["messages"].append(
                {
                #"tool_call_id": func.id,
                "role": "user",
                #"name": f.name,
                "content": f'resume this for user:\n{response}',
                })
            if not error:
                f = f.name
                global functions_called_stats
                if f not in functions_called_stats:
                    functions_called_stats[f] = 1
                else:
                    functions_called_stats[f] += 1

                logger.info(f'🛠 ({functions_called_stats[f]}) {f} ✅')
            break


    payload.pop("tools")
    payload.pop("tool_choice")

    return payload

async def manage_stream_response(thisShit, res_text, response):
    global total_tokens

    try:
        logger.debug("Using streaming...")

        async for chunk in response:
            if thisShit.tool_call and chunk.choices[0].delta.tool_calls:
                yield chunk.choices[0].delta.tool_calls, "stall"

            logger.debug(f'Chunk: {chunk} <---- Chunk')
            if chunk.choices:
                res_text += getattr(chunk.choices[0].delta, 'content', "") or ""
                fr = str(chunk.choices[0].finish_reason).lower()
            else: 
                res_text += ""
                fr = "continue"
            logger.debug(fr)
            if fr in ["stop", "length"]:
                if not res_text:
                    raise ValueError(f'"{res_text}" inexistent')
                tok = await calculate_token_length(res_text)

                total_tokens += tok
                thisShit.used_tokens += tok
                logger.debug(f'Yielding entire response: {res_text}')
                yield res_text, "stop"
            elif fr in ["content_filter"]:
                raise ValueError("Censored")

            yield res_text, "continue"
    except Exception as e:
        raise Exception(f"{_getframe().f_code.co_name}: {str(e)}")


stream_type = {
    True: manage_stream_response,
    False: manage_non_stream_response   
}

err = '✍️ 😔❌👍'

async def request_chat_completion(thisShit, model, user_id, command, quick):
    response = "placeholder_empty_response"
    try:
        payload = await configure_payload(thisShit, model, command, quick)
        
        logger.debug("Generating response...")
        temp_apis = await shuffle_apis(user_id, payload["model"], command)
        for api in temp_apis:
            if api in ["cerebras", "google"]:
                payload.pop("frequency_penalty")
                payload.pop("presence_penalty")
                if api == "google": payload.pop("seed")
            try:
                logger.debug(f"Joining chat completion with {api}")
                res_text = ""
                status = ""
                client = await select_api_data(api)
                try:
                    response = await client.chat.completions.create(**payload)
                except CancelledError as e:
                    if "nDDñd" not in str(e):
                        continue
                    raise e
                except Exception as e:
                    if isinstance(response, str):
                        raise e

                logger.debug(f'Response: {response} <---- Response')

                resser = stream_type[payload["stream"]]
                outsider = True
                try:
                    async for res_text, status in resser(thisShit, res_text, response):
                        if "您今日的USD" in res_text:
                            raise BrokenPipeError("API is too poor to provide responses.")
                        if status in ["stop", "stall"]:
                            await update_total_reqs(command, api, payload["model"], user_id, 1)
                        if status == "stall":
                            second_response = "placeholder_empty_second_response"
                            outsider = False
                            logger.debug("Processing function call...")

                            s_payload = await process_function_data(res_text, deepcopy(payload))
                            thisShit.conversation = s_payload["messages"]

                            s_temp_apis = await shuffle_apis(user_id, model, command)
                            for s_api in s_temp_apis:
                                try:
                                    logger.debug(f"Joining second chat completion with {s_api}")
                                    s_payload["model"] = model
                                    s_res_text = ""
                                    s_client = await select_api_data(s_api)
                                    try:
                                        second_response = await s_client.chat.completions.create(**s_payload)
                                        async for s_res_text, s_status in resser(thisShit, s_res_text, second_response):
                                            if s_status in ["stop"]:
                                                await update_total_reqs(command, s_api, s_payload["model"], user_id, 1)
                                            yield s_res_text, s_status
                                    except APITimeoutError:
                                        continue

                                except Exception as s_e:
                                    await update_total_reqs(command, s_api, s_payload["model"], user_id, 0, second_response, s_e)
                                    logger.error(f"Error with {s_api}: {str(s_e)}")
                                    continue
                            else:
                                raise ConnectionError("None of APIs responded correctly.")
                                # yield err, "error"
                        elif outsider:
                            yield res_text, status
                except Exception as e:
                    raise BufferError(f'Error iterating response. {api}, {payload["model"]} [res_test: {res_text}, status: {status}]: {str(e)}')
            except Exception as e:
                await update_total_reqs(command, api, payload["model"], user_id, 0, response, e)
                logger.error(f"Error with {api}: {str(e)}")
                continue
        else:
            raise ConnectionError("None of APIs responded correctly.")
            # yield err, "error"

    except Exception as e:
        raise e
        # raise ConnectionError(f"{_getframe().f_code.co_name}: {str(e)} {response}")



async def configure_payload(thisShit, model, command, quick):
    logger.debug("Set-up chat payload")
    try:

        payload = {
            "messages": thisShit.conversation,
            "model": model,
            #"reasoning_effort": "high",
            "stream": False if quick else thisShit.streaming,
            "seed": thisShit.seed,
            "max_tokens": thisShit.max_tokens, # + int(thisShit.output_tokens if isinstance(thisShit.output_tokens, int) else 0),
            "timeout": thisShit.timeout if thisShit.timeout > 60 else 6 if thisShit.streaming else 15
        }
        if not quick and thisShit.tool_call and command == command_chat:
            payload["tools"] = functions_data
            payload["tool_choice"] = "auto"

        if not thisShit.randomizer:
            logger.debug("Not using randomizer")
            payload["temperature"] = thisShit.temperature
            payload["top_p"] = thisShit.top_p
            payload["frequency_penalty"] = thisShit.frequency_penalty
            payload["presence_penalty"] = thisShit.presence_penalty
        else:
            logger.debug("Using randomizer")
            payload["temperature"] = uniform(0.1, 2.0)
            payload["top_p"] = uniform(0.1, 1.0)
            payload["frequency_penalty"] = uniform(-2.0, 2.0)
            payload["presence_penalty"] = uniform(-2.0, 2.0)
        return payload
    except Exception as e:
        logger.error(f"{_getframe().f_code.co_name}: {str(e)}")

