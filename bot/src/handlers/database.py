from json import dumps, loads
from datetime import datetime
from asyncio import sleep, Lock
import redis.asyncio as redis


from bot.src.config import redis_enabled, redis_password, redis_uri, redis_user, bot, save_db_bandwidth
from bot.src.logs import logger
from bot.src.handlers.commands import tasks
from bot.src.handlers.userclass import UserPrepare

SAVE_MINUTES = 10 if save_db_bandwidth else 1

class IndexGroupInstances:

    def __init__(self, loop):
        self.redis = False
        self.r = None
        self.lock = Lock()
        self.user_index = {}
        self.group_index = {}
        self.ttl = 2592000
        self.save_each = SAVE_MINUTES * 60
        self.loop = loop  # Use the existing event loop

    async def initialize_redis(self):
        if redis_enabled:
            
            try:
                if redis_password and redis_user:
                    separator = ":"
                    another = "@"
                else:
                    separator = ""
                    another = ""
                self.r = redis.from_url(
                    url=f"redis://{redis_user}{separator}{redis_password}{another}{redis_uri}",
                    encoding="utf-8",
                    decode_responses=True
                )
                response = await self.r.ping()  # Test Redis connection
                if response:
                    logger.info("Redis connected.")
                self.redis = True
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                self.redis = False  # Fall back to in-memory storage
        else:
            logger.warning("No Redis password provided. In-memory cache only.")
    
    async def grab_class(self, chat_id= "", user_id= "", make_group=None, only_group = None):
        try:
            mng = None
            indexed = None
            if chat_id != user_id:
                if chat_id not in self.group_index:
                    mng = UserPrepare()
                    if self.redis:
                        mng = await self.quick_query(chat_id, mng)
                    async with self.lock:
                        self.group_index[chat_id] = mng
                else:
                    mng = self.group_index[chat_id]

                if make_group and only_group:
                    mng.group_mode = True
                    mng.user_id = user_id
                    if not mng.owners:
                        mng.owners.add(user_id)
                    elif mng.owners:
                        for owner_id in list(mng.owners):
                            if owner_id in self.user_index:
                                break
                        else:
                            mng.owners.add(user_id)

                    return mng
                if mng.group_mode:
                    self.group_index[chat_id].last_seen = datetime.now()
                    return mng

            if user_id not in self.user_index:
                mng = UserPrepare()
                mng.user_id = user_id
                if self.redis:
                    mng = await self.quick_query(user_id, mng)
                async with self.lock:
                    self.user_index[user_id] = mng

            else:
                self.user_index[user_id].last_seen = datetime.now()
                mng = self.user_index[user_id]

            return mng

        except Exception as e:
            logger.error(f'db grab_class error: {str(e)}')
            raise e

    async def quick_query(self, id, obj):
        id_data = await self.r.hgetall(id)
        if id_data:
            logger.debug(f"Recovering data from Redis: {id}")
            await obj.from_dict(id_data)

        return obj
            
    async def save_to_redis(self, key, data_dict):
        """Save an object in Redis with a TTL."""
        if not self.redis:
            return

        async with self.r.pipeline() as pipe:
            await pipe.hset(key, mapping=data_dict)
            await pipe.execute()
        logger.debug(f"Saved {key} to Redis.")

    async def remove_old_db_ids(self):
        if self.redis:
            keys = await self.r.keys('*')
        else:
            keys = [*self.user_index.keys(), *self.group_index.keys()]
        accum = 0
        for key in keys:
            if self.redis:
                id_data = await self.r.hgetall(key)
                last_seen = loads(id_data["last_seen"])["value"]
            else:
                if key in self.user_index:
                    last_seen = self.user_index[key].last_seen
                elif key in self.group_index:
                    last_seen = self.group_index[key].last_seen
            if await date_calc(last_seen) > self.ttl:
                if key in self.user_index:
                    del self.user_index[key]
                elif key in self.group_index:
                    del self.group_index[key]

                logger.info(f"Deleting ID {key} from database: TTL")
                accum += 1
                if self.redis:
                    await self.r.delete(key)
        if accum:
            logger.info(f"Purged {accum} chats from database. 👍")

    async def flush_memory(self):
        """Backup all in-memory objects to Redis (and clear from memory?)."""
        if self.redis:

            # Save and remove all users from memory
            logger.info("Backup in-memory objects to Redis...")
            if len(self.user_index):
                logger.info("Detected users to backup.")
                for user_id, user_obj in list(self.user_index.items()):
                    await self.save_to_redis(user_id, await to_dict(user_obj))
                    if save_db_bandwidth and user_id not in tasks.index_tasks:
                        del self.user_index[user_id]  # Clear from in-memory once saved
                    logger.info(f"User {user_id} uploaded")

            # Save and remove all groups from memory
            if len(self.group_index):
                logger.info("Detected groups to backup.")
                for group_id, group_obj in list(self.group_index.items()):
                    await self.save_to_redis(group_id, await to_dict(group_obj))
                    if save_db_bandwidth and group_id not in tasks.index_tasks:
                        del self.group_index[group_id]
                    logger.info(f"Group {group_id} uploaded")
        await self.remove_old_db_ids()

    async def flush_task(self, force = 0):
        """Schedule the flush task."""
        if not force and self.redis:
            logger.info(f"Scheduled to flush memory every {self.save_each} seconds.")
        try:
            if self.redis:
                while True:
                    if not force:
                        await sleep(self.save_each)
                    await self.flush_memory()
                    if force:
                        logger.info("Force flushing done.")
                        break 
            elif not self.redis and not force:
                return logger.warning("Redis not detected. Flush scheduling disabled.")
        except Exception as e:
            logger.error(f"Error in schedule_flush: {str(e)}")
            raise e

    async def burn_me(self, id: str):
        try:
            logger.debug(f'Deleting id data: {id}')
            indexed_deletions = [id]
            if id in self.user_index:
                logger.debug(f'Removing user {id} from databases')
                async with self.lock:
                    logger.debug(f'User found in index: {id}')

                    for group in list(self.user_index[id].groups):
                        group_data = None
                        logger.debug(f'User have groups, deleting groups if possible: {id}')
                        logger.debug(f'Checking for this group {group} in database: user {id}')
                        if self.redis:
                            group_data = await self.r.hgetall(group)
                            owners = set(loads(group_data["owners"])["value"])
                        else:
                            if group in self.group_index:
                                group_data = self.group_index[group]
                                owners = self.group_index[group].owners

                        if group_data:
                            logger.debug(f'Removing user {id} from group {group}')
                            owners.discard(id)
                            if not len(owners):
                                logger.debug(f'Group {group} being deleted completely. No more users. Triggered by {id}')
                                self.group_index.pop(group, None)
                                indexed_deletions.append(group)
                    self.user_index.pop(id, None)
                tasks.index_tasks.pop(id, None)
                if self.redis:
                    await self.r.delete(*indexed_deletions)
                return 1
            return 0
        except Exception as e:
            logger.error(f'Error during burn_me operation for id {id}: {str(e)}')
            return 0  # Handle failure gracefully

    async def burn_group(self, id: str):
        try:
            logger.debug(f'Deleting group data: {id}')
            if id in self.group_index:
                logger.debug(f'Removing group {id} from databases')
                async with self.lock:
                    logger.debug(f'Group {id} being deleted completely.')
                    del self.group_index[id]
                tasks.index_tasks.pop(id, None)
                if self.redis:
                    await self.r.delete(id)
                return 1
            return 0
        except Exception as e:
            logger.error(f'Error during burn_me operation for id {id}: {str(e)}')
            return 0  # Handle failure gracefully

    async def set(self, id: str, attr: str, value: int | str | dict | float):
        try:
            setattr(await self.grab_class(id), attr, value)
        except Exception as e:
            logger.error(f'index write error: {id} - {attr} - {value} - {str(e)}')
            raise e

async def to_dict(obj):
    try:
        data = {}
        for key, value in obj.__dict__.items():
            if isinstance(value, set):
                data[key] = dumps({
                    "type": "set",
                    "value": list(value)  # Convert set to list for JSON serialization
                })
            elif isinstance(value, bool):
                data[key] = dumps({"type": "bool", "value": int(value)})
            elif isinstance(value, (str, int, float)):
                data[key] = dumps({"type": type(value).__name__, "value": value})
            elif value is None:
                data[key] = dumps({"type": "none", "value": ":)"})
            elif isinstance(value, (dict, list)):
                data[key] = dumps({"type": type(value).__name__, "value": dumps(value)})
            elif isinstance(value, datetime):
                data[key] = dumps({"type": "datetime", "value": value.isoformat()})
            else:
                raise ValueError(f"Unsupported value type: {type(value)}")
        return data
    except Exception as e:
        logger.error(f'Error in to_dict: {str(e)}')

async def date_calc(old_date, return_str = False):
    if not isinstance(old_date, datetime):
        try:
            old_date = datetime.fromisoformat(old_date)
            if return_str:
                return old_date
        except ValueError:
            logger.error(f"error in date_calc: string isn't a valid datetime")
            return

    now_date = datetime.now()
    return (now_date - old_date).total_seconds()

db = IndexGroupInstances(bot.loop)
