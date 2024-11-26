
from bot.src.logs import logger
import bot.src.config as c

from asyncio import Lock as TaskLock, CancelledError, sleep
from telethon import Button

from copy import deepcopy
from datetime import datetime, timedelta
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
    c.command_tts: {}
}

task_limits = {
    c.command_chat: 2,
    c.command_image: 2,
    c.command_stt: 2,
    c.command_tts: 2
}

chat_locks = {}
async def get_chat_lock(user_id):
    if user_id not in chat_locks:
        chat_locks[user_id] = TaskLock()
    return chat_locks.get(user_id, None)


async def add_task(task_type, user_id, task, task_id):
    user_lock = await get_chat_lock(user_id)
    task_wrapper = None
    async with user_lock:
        if user_id not in index_tasks:
            index_tasks[user_id] = deepcopy(task_types)

        if len(index_tasks[user_id][task_type]) < task_limits[task_type]:
            task_wrapper = c.bot._loop.create_task(task)

            index_tasks[user_id][task_type][task_id] = {"task": task_wrapper, "created_at": datetime.now()}
            logger.info(f"Task {task_type} - User: {user_id}' - Queued.")
        else:
            logger.info(f"Can't add more tasks {task_type}. Please wait.")
            return "CantAddMore"
    if task_wrapper:
        try:
            return await task_wrapper
        except CancelledError:
            task_wrapper.cancel(msg="Cancelled by user.")
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
        except Exception as e:
            logger.info(f"Error in task: {task_type} - Task ID: {task_id} - User: {user_id}: {e}")
        finally:
            async with user_lock:
                index_tasks[user_id][task_type].pop(task_id, None)



async def cancel_task(task_type, user_id, task_id):
    user_lock = await get_chat_lock(user_id)
    async with user_lock:
        if not index_tasks.get(user_id, {}).get(task_type):
            return "🤡"

        task = index_tasks[user_id][task_type].get(task_id, None).get("task", None)
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
            index_tasks.get(user_id, {}).get(task_type, {}).pop(task_id, None)

async def monitor_tasks(update_each_seconds=5, timeout_seconds=600):

    last_total_users = 0
    timeout_delta = timedelta(seconds=timeout_seconds)

    while True:
        if index_tasks:
            users_to_remove = []
            now = datetime.now()
            tasks_to_cancel = []

            for tg_id, tasks in list(index_tasks.items()):
                chat_count = len(tasks.get(c.command_chat, {}))
                img_count = len(tasks.get(c.command_image, {}))
                stt_count = len(tasks.get(c.command_stt, {}))
                tts_count = len(tasks.get(c.command_tts, {}))

                if chat_count or img_count or stt_count or tts_count:
                    logger.info(f"{tg_id}: "
                                f"- {c.command_chat}: {chat_count}" if chat_count else ''
                                f"- {c.command_image}: {img_count}" if img_count else ''
                                f"- {c.command_stt}: {stt_count}" if stt_count else ''
                                f"- {c.command_tts}: {tts_count}" if tts_count else '')
                else:
                    users_to_remove.append(tg_id)

                for task_type, tasks_dict in tasks.items():
                    for task_id, task_info in list(tasks_dict.items()):
                        created_at = task_info.get("created_at")
                        task = task_info.get("task")

                        if created_at and task:
                            elapsed = now - created_at
                            if elapsed > timeout_delta:
                                tasks_to_cancel.append((tg_id, task_type, task_id, task))

            for tg_id, task_type, task_id, task in tasks_to_cancel:
                try:
                    task.cancel()
                    await task
                except CancelledError:
                    logger.info(f"Task {task_type}:{task_id} from {tg_id} "
                                f"force cancelled due to timeout.")
                except Exception as e:
                    logger.error(f"Error cancelling {task_id} from {tg_id}: {e}")
                finally:
                    index_tasks[tg_id][task_type].pop(task_id)
                    logger.debug(f"Task {task_id} from {tg_id} force deleted due to timeout.")

            for tg_id in users_to_remove:
                index_tasks.pop(tg_id, None)
                chat_locks.pop(tg_id, None)
                logger.debug(f"Removed user {tg_id} from task index due to no active tasks.")

            total_users = len(index_tasks)
            if total_users != last_total_users:
                logger.info(f'Total users with tasks: {total_users}: {list(index_tasks.keys())}')
                last_total_users = total_users
        else:
            if last_total_users != 0:
                logger.info("No queued tasks")
                last_total_users = 0

        await sleep(update_each_seconds)
