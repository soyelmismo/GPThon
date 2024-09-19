
from bot.src.logs import logger
from bot.src.config import command_chat, command_image, command_stt, bot

from asyncio import Lock as TaskLock, CancelledError, sleep
from telethon import Button

from copy import deepcopy
from random import choice
from string import ascii_letters, digits
from . import select_instance

index_tasks = {}



def task_gen_temp_identifier(length = 3):
    caracteres = ascii_letters + digits
    return ''.join(choice(caracteres) for _ in range(length))

async def gen_cancel_button(command, task_id):
    return [
        [Button.inline("🚫", data=f'{tasks_identifier}|{command}|{task_id}')]
        ]

tasks_identifier = task_gen_temp_identifier(3)

task_types = {
    command_chat: {},
    command_image: {},
    command_stt: {},
    "/tts": {}
}

task_limits = {
    command_chat: 2,
    command_image: 2,
    command_stt: 2,
    "/tts": 2
}

user_locks = {}
async def get_user_lock(user_id):
    if user_id not in user_locks:
        user_locks[user_id] = TaskLock()
    return user_locks[user_id]


async def add_task(task_type, user_id, task, task_id):
    user_lock = await get_user_lock(user_id)
    task_wrapper = None
    async with user_lock:
        if not index_tasks.get(user_id):
            index_tasks[user_id] = deepcopy(task_types)
        if len(index_tasks[user_id][task_type]) < task_limits[task_type]:
            task_wrapper = bot.loop.create_task(task)
            index_tasks[user_id][task_type][task_id] = task_wrapper
            logger.info(f"Task {task_type} - User: {user_id}' - Queued.")
        else:
            logger.info(f"Can't add more tasks {task_type}. Please wait.")
            return "CantAddMore"
    if task_wrapper:
        try:
            return await task_wrapper
            # logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Finished.")
        except CancelledError:
            task_wrapper.cancel(msg="Cancelled by user.")
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
        except Exception as e:
            logger.info(f"Error in task: {task_type} - Task ID: {task_id} - User: {user_id}: {e}")
        finally:
            index_tasks[user_id][task_type].pop(task_id, None)
        


async def cancel_task(task_type, user_id, task_id):
    user_lock = await get_user_lock(user_id)
    message = None
    logger.debug("Joining lock")
    async with user_lock:
        logger.debug("Joined lock")
        try:
            if not index_tasks.get(user_id, {}).get(task_type):
                logger.info(f"No tasks of {task_type}")
                raise ModuleNotFoundError("Task not found")

            task = index_tasks[user_id][task_type].get(task_id, None)
            if not task:
                logger.info(f"No task found {task_id}")
                message = "❓ 🤔 ❌"
            else:
                logger.info(f"Cancelling {task_type} {task_id}")
                task.cancel(msg="Cancelled by user.")
                await task
        except ModuleNotFoundError:
            message = "🤡"
        except CancelledError:
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
            message = "🫡✅"
        finally:
            index_tasks.get(user_id, {}).get(task_type, {}).pop(task_id, None)
            return message

async def cancel_callback(event):
    try:
        _, c_type, c_tik = str(event.data.decode('utf-8')).split("|")
        user_id = await select_instance(event = event, task_id=c_tik)
        logger.debug(event)
        logger.debug(f'{c_type} {user_id} {c_tik}')
        message = await cancel_task(c_type, user_id, c_tik)
        if message:
            await event.answer(message, alert=False)
    except Exception as e:
        logger.error(str(e))


async def monitor_tasks(update_each_seconds=5):
    while True:
        if len(index_tasks):
            users_to_remove = []
            for user_id, tasks in list(index_tasks.items()):
                chat_count = len(tasks[command_chat])
                img_count = len(tasks[command_image])
                stt_count = len(tasks[command_stt])
                tts_count = len(tasks["/tts"])

                if chat_count or img_count or stt_count or tts_count:
                    logger.debug(f"{user_id}: {command_chat}: {chat_count}, {command_image}: {img_count}, {command_stt}: {stt_count}. /tts: {stt_count}.")
                else:
                    users_to_remove.append(user_id)

            for user_id in users_to_remove:
                del index_tasks[user_id]
                del user_locks[user_id]
                logger.debug(f"Removed user {user_id} from task index due to no active tasks.")
            logger.info(f'Total users with tasks: {len(index_tasks)}: {list(index_tasks.keys())}')
        else:
            logger.debug("No queued tasks")
        await sleep(update_each_seconds)