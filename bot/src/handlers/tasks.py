from bot.src.logs import logger
import bot.src.config as c

from asyncio import Lock as TaskLock, CancelledError, sleep
from telethon import Button

from copy import deepcopy
from datetime import datetime, timedelta
from random import choice
from string import ascii_letters, digits

index_tasks = {}

def task_gen_temp_identifier(length=3):
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
    return chat_locks[user_id]

async def add_task(task_type, user_id, task, task_id):
    user_lock = await get_chat_lock(user_id)
    task_wrapper = None
    async with user_lock:
        if user_id not in index_tasks:
            index_tasks[user_id] = deepcopy(task_types)
        
        if len(index_tasks[user_id][task_type]) < task_limits[task_type]:
            task_wrapper = c.bot._loop.create_task(task)
            index_tasks[user_id][task_type][task_id] = {"task": task_wrapper, "created_at": datetime.now()}
            logger.info(f"Task {task_type} - User: {user_id} - Queued.")
        else:
            logger.info(f"Can't add more tasks {task_type}. Please wait.")
            return "CantAddMore"
    if task_wrapper:
        try:
            return await task_wrapper
        except CancelledError:
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
        except Exception as e:
            logger.error(f"Error in task: {task_type} - Task ID: {task_id} - User: {user_id}: {e}")
        finally:
            async with user_lock:
                index_tasks[user_id][task_type].pop(task_id, None)

async def cancel_task(task_type, user_id, task_id):
    user_lock = await get_chat_lock(user_id)
    async with user_lock:
        user_tasks = index_tasks.get(user_id, {})
        if not user_tasks.get(task_type):
            return "🤡"
        
        task_info = user_tasks[task_type].get(task_id)
        if not task_info:
            return "❓ 🤔 ❌"
        
        task = task_info["task"]
        logger.info(f"Cancelling {task_type} {task_id}")
        try:
            task.cancel(msg="nDDñd Cancelled by user.")
            await task
        except CancelledError:
            logger.info(f"Task {task_type} - Task ID: {task_id} - User: {user_id} - Cancelled.")
            return "🫡✅"
        except Exception as e:
            logger.error(f"Error cancelling task {task_type} {task_id}: {e}")
            return "❌"
        finally:
            user_tasks[task_type].pop(task_id, None)

async def monitor_tasks(update_each_seconds=5, timeout_seconds=600):
    last_total_users = 0
    timeout_delta = timedelta(seconds=timeout_seconds)
    
    while True:
        current_users = list(index_tasks.keys())
        if current_users:
            now = datetime.now()
            users_to_remove = []
            
            for tg_id in current_users:
                user_lock = await get_chat_lock(tg_id)
                async with user_lock:
                    user_tasks = index_tasks.get(tg_id, {})
                    if not user_tasks:
                        users_to_remove.append(tg_id)
                        continue
                    
                    # Loggear estado de tareas (sección restaurada)
                    task_counts = []
                    for cmd in [c.command_chat, c.command_image, c.command_stt, c.command_tts]:
                        count = len(user_tasks.get(cmd, {}))
                        if count > 0:
                            task_counts.append(f"- {cmd}: {count}")
                    if task_counts:
                        logger.info(f"User {tg_id} tasks: {' '.join(task_counts)}")
                    
                    # Manejo de timeouts
                    task_types_to_remove = []
                    for task_type in list(user_tasks.keys()):
                        tasks_dict = user_tasks[task_type]
                        task_ids_to_cancel = []
                        
                        for task_id, task_info in list(tasks_dict.items()):
                            created_at = task_info.get("created_at")
                            task = task_info.get("task")
                            
                            if created_at and (now - created_at) > timeout_delta:
                                task_ids_to_cancel.append((task_id, task))
                        
                        for task_id, task in task_ids_to_cancel:
                            try:
                                task.cancel(msg="nDDñd Timeout. Force cancelled.")  # Mensaje específico
                                await task
                            except CancelledError as ce:
                                if "Timeout" in str(ce):
                                    logger.info(f"Task {task_type}:{task_id} from {tg_id} - Timeout. Force cancelled.")
                            except Exception as e:
                                logger.error(f"Error cancelling {task_id} from {tg_id}: {e}")
                            finally:
                                tasks_dict.pop(task_id, None)
                                logger.debug(f"Removed: {task_type}:{task_id} from {tg_id}")
                        
                        if not tasks_dict:
                            task_types_to_remove.append(task_type)
                    
                    # Limpieza de tipos de tarea vacíos
                    for task_type in task_types_to_remove:
                        user_tasks.pop(task_type, None)
                    
                    if not user_tasks:
                        users_to_remove.append(tg_id)
            
            # Eliminar usuarios sin tareas
            for tg_id in users_to_remove:
                async with (await get_chat_lock(tg_id)):
                    index_tasks.pop(tg_id, None)
                    chat_locks.pop(tg_id, None)
                    logger.debug(f"Removed user {tg_id}")
            
            # Loggear total de usuarios
            total_users = len(index_tasks)
            if total_users != last_total_users:
                logger.info(f'Users with tasks: {total_users} - {list(index_tasks.keys())}')
                last_total_users = total_users
        else:
            if last_total_users != 0:
                logger.info("No active tasks")
                last_total_users = 0
        
        await sleep(update_each_seconds)