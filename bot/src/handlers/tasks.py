
from bot.src.logs import logger
import bot.src.config as c

from asyncio import Lock as TaskLock, CancelledError, sleep
from telethon import Button

from copy import deepcopy
from random import choice
from string import ascii_letters, digits


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
    c.command_chat: {},
    c.command_image: {},
    c.command_stt: {},
    "/tts": {}
}

task_limits = {
    c.command_chat: 2,
    c.command_image: 2,
    c.command_stt: 2,
    "/tts": 2
}

chat_locks = {}
async def get_chat_lock(user_id, chat_id):
    if user_id not in chat_locks:
        chat_locks[user_id] = TaskLock()
    if chat_id != user_id and chat_id not in chat_locks:
        chat_locks[chat_id] = TaskLock()
    return chat_locks.get(user_id, None), chat_locks.get(chat_id, None)


async def add_task(task_type, user_id, chat_id, task, task_id):
    user_lock, chat_lock = await get_chat_lock(user_id, chat_id)
    task_wrapper = None
    async with user_lock:
        if user_id not in index_tasks:
            index_tasks[user_id] = deepcopy(task_types)
        if chat_lock and chat_id not in index_tasks:
            async with chat_lock:
                index_tasks[chat_id] = deepcopy(task_types)

        if len(index_tasks[user_id][task_type]) < task_limits[task_type]:
            task_wrapper = c.bot._loop.create_task(task)

            if chat_lock and chat_id in index_tasks:
                async with chat_lock:
                    index_tasks[chat_id][task_type][task_id] = task_wrapper

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
            if chat_lock and chat_id in index_tasks:
                async with chat_lock:
                    index_tasks[chat_id][task_type].pop(task_id, None)
            async with user_lock:
                index_tasks[user_id][task_type].pop(task_id, None)



async def cancel_task(task_type, user_id, task_id, chat_id):
    user_lock, chat_lock = await get_chat_lock(user_id, chat_id)
    async with user_lock:
        if not index_tasks.get(user_id, {}).get(task_type):
            return "🤡"

        task = index_tasks[user_id][task_type].get(task_id, None)
        if not task:
            return "❓ 🤔 ❌"

        logger.info(f"Cancelling {task_type} {task_id}")
        try:
            task.cancel(msg="Cancelled by user.")
            await task
        except CancelledError:
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
            return "🫡✅"
        except Exception as e:
            logger.error(f"Error cancelling task {task_type} {task_id}: {e}")
            return "❌"
        finally:
            if chat_lock and chat_id in index_tasks:
                index_tasks.get(chat_id, {}).get(task_type, {}).pop(task_id, None)
            index_tasks.get(user_id, {}).get(task_type, {}).pop(task_id, None)

async def monitor_tasks(update_each_seconds=5):
    last_total_users = 0
    while True:
        if len(index_tasks):
            users_to_remove = []
            for tg_id, tasks in list(index_tasks.items()):
                chat_count = len(tasks[c.command_chat])
                img_count = len(tasks[c.command_image])
                stt_count = len(tasks[c.command_stt])
                tts_count = len(tasks["/tts"])

                if chat_count or img_count or stt_count or tts_count:
                    logger.debug(f"{tg_id}: {c.command_chat}: {chat_count}, {c.command_image}: {img_count}, {c.command_stt}: {stt_count}. /tts: {stt_count}.")
                else:
                    users_to_remove.append(tg_id)

            for tg_id in users_to_remove:
                index_tasks.pop(tg_id)
                chat_locks.pop(tg_id)
                logger.debug(f"Removed user {tg_id} from task index due to no active tasks.")

            total_users = len(index_tasks)
            if total_users != last_total_users:
                logger.info(f'Total users with tasks: {total_users}: {list(index_tasks)}')
                last_total_users = total_users
        else:
            if last_total_users != 0:
                logger.info("No queued tasks")
                last_total_users = 0
        await sleep(update_each_seconds)
