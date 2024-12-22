from json import dumps, loads
from datetime import datetime
from asyncio import sleep, Lock
import redis.asyncio as valkey

import bot.src.config as conf
from bot.src.logs import logger
from bot.src.handlers import tasks
from bot.src.handlers.userclass import UserPrepare

SAVE_MINUTES = 10 if conf.save_db_bandwidth else 1

class ValkeyClient:
    def __init__(self, url):
        self.client = valkey.from_url(
            url=url, encoding="utf-8",
            decode_responses=True,
            health_check_interval=10,
            socket_connect_timeout=5,
            retry_on_timeout=True,
            socket_keepalive=True
            )

    def ping(self):
        return self.client.ping()

    async def hgetall(self, key):
        return await self.client.hgetall(key)

    async def hset(self, key, mapping):
        async with self.client.pipeline() as pipe:
            await pipe.hset(key, mapping=mapping)
            await pipe.execute()

    async def delete(self, *keys):
        return await self.client.delete(*keys)

    async def keys(self, pattern):
        return await self.client.keys(pattern)


class IndexGroupInstances:
    def __init__(self, loop, valkey_client=None, ttl=2592000, save_each=SAVE_MINUTES * 60):
        self.valkey_client = valkey_client
        self.r: valkey.Redis = None
        self.lock = Lock()
        self.index = {}
        self.ttl = ttl
        self.save_each = save_each
        self.loop = loop
        
        if valkey_client:
            self.valkey_enabled = True
            
        else:
            self.valkey_enabled = False

    async def initialize_valkey(self):
        if self.valkey_enabled:
            try:
                self.r = self.valkey_client
                response = await self.r.ping()
                if response:
                    logger.info("Valkey connected.")
            except Exception as e:
                logger.error(f"Failed to connect to Valkey: {str(e)}")

    async def _get_manager(self, id=None):
        if id in self.index:
            return self.index[id]
        mng = UserPrepare()
        if self.valkey_enabled:
            mng = await self.quick_query(id, mng)
        async with self.lock:
            self.index[id] = mng
        return mng

    async def _create_group_chat(self, mng, user_id=None):
        async with self.lock:

            if not mng.owners:
                mng.group_mode = True
                mng.user_id = user_id
                mng.owners.add(user_id)

            elif mng.owners:
                su_data = await self.r.hgetall(mng.user_id)
                if not su_data:
                    mng.owners.add(user_id)
                    mng.owners.discard(mng.user_id)
                    mng.user_id = user_id

        return mng

    async def grab_class(self, chat_id="", user_id="", make_group=None, private=True):
        try:
            if chat_id != user_id or not private:
                mng = await self._get_manager(chat_id)
                if make_group:
                    mng = await self._create_group_chat(mng, user_id)
                    if user_id in mng.owners:
                        async with self.lock:
                            self.index[user_id].groups.add(chat_id)
                if mng.group_mode:
                    t_mng = await self._get_manager(user_id)
                    t_mng.last_seen = datetime.now()
                    return mng

            mng = await self._get_manager(user_id)
            return mng

        except Exception as e:
            logger.error(f'db grab_class error: {str(e)}')
            raise e

    async def quick_query(self, id, obj):
        id_data = await self.r.hgetall(id)
        if id_data:
            logger.info(f"Recovering {id} from Valkey")
            await obj.from_dict(id_data)
        return obj

    async def save_to_valkey(self, key, data_dict, exec_date):
        await self.r.hset(key, mapping=data_dict)
        msg = f"ID {key} uploaded"
        time_passed = (exec_date - self.index[key].last_seen).total_seconds()
        if not conf.save_db_bandwidth and time_passed > 60:
            async with self.lock:
                self.index.pop(key)
                msg += " and deleted locally."
        logger.info(msg)

    async def remove_old_db_ids(self):
        keys = await self.r.keys('*') if self.valkey_enabled else [*self.index]
        accum = 0
        for tg_id in keys:
            if self.valkey_enabled:
                id_data = await self.r.hgetall(tg_id)
                last_seen = loads(id_data["last_seen"])["value"]
            else:
                last_seen = self.index[tg_id].last_seen if tg_id in self.index else None
            if last_seen:
                if await date_calc(last_seen) > self.ttl:
                    async with self.lock:
                        self.index.pop(tg_id, None)
                    logger.info(f"Deleting ID {tg_id} from database: TTL")
                    accum += 1
                    if self.valkey_enabled:
                        await self.r.delete(tg_id)
        if accum:
            logger.info(f"Purged {accum} chats from database.")

    async def flush_memory(self):
        pending = len(self.index)
        skipped_ids = 0
        if self.valkey_enabled and pending:
            logger.info(f"Trying to backup {pending} in-memory objects to Valkey...")
            exec_date = datetime.now()
            for id, user_obj in list(self.index.items()):
                if id in tasks.index_tasks:
                    skipped_ids += 1
                else:
                    await self.save_to_valkey(id, await to_dict(user_obj), exec_date)
        if skipped_ids:
            logger.info(f"Skipped {skipped_ids} IDs running tasks.")

        await self.remove_old_db_ids()

    async def flush_task(self, force=0):
        if not force and self.valkey_enabled:
            logger.info(f"Scheduled to flush memory every {self.save_each} seconds.")
        try:
            if self.valkey_enabled:
                while True:
                    if not force:
                        await sleep(self.save_each)
                    await self.flush_memory()
                    if force:
                        logger.info("Force flushing done.")
                        break
            else:
                if force:
                    logger.warning("Tried to flush database forcibly, but Valkey not detected.")
                else:
                    logger.warning("Valkey not detected. Flush scheduling disabled.")
        except Exception as e:
            logger.error(f"Error in schedule_flush: {str(e)}")
            raise e

    async def _delete_from_groups(self, id):
        indexed_deletions = [id]

        for group in list(self.index[id].groups):
            group_data = None
            if group in self.index:
                group_data = self.index[group]
                owners = group_data.owners
            elif self.valkey_enabled:
                group_data = await self.r.hgetall(group)
                if group_data:
                    owners = set(loads(group_data["owners"])["value"])

            if group_data:
                owners.discard(id)
                if not len(owners):
                    logger.debug(f'Grupo {group} siendo eliminado completamente. No más usuarios.')
                    indexed_deletions.append(group)
        return indexed_deletions

    async def burn_me(self, id):
        try:
            logger.debug(f'Removiendo usuario {id} de la base de datos')
            indexed_deletions = await self._delete_from_groups(id)
            
            async with self.lock:
                for del_id in indexed_deletions:
                    self.index.pop(del_id, None)
            
            if self.valkey_enabled:
                await self.r.delete(*indexed_deletions)
            
            return 1
        except Exception as e:
            logger.error(f'Error durante la operación burn_me para id {id}: {str(e)}')
            return 0

    async def burn_group(self, id):
        try:
            logger.debug(f'Deleting group data: {id}')
            cleaned_class = UserPrepare()
            cleaned_class.daily = self.index[id].daily
            # fuck your burn and create unlimited quota
            # motherfucker
            cleaned_class.used_tokens = self.index[id].used_tokens
            async with self.lock:
                self.index[id] = cleaned_class

            return self.index[id].user_id == str()
        except Exception as e:
            logger.error(f'Error during burn_me operation for id {id}: {str(e)}')
            return 0

async def to_dict(obj):
    try:
        data = {}
        for key, value in obj.__dict__.items():
            if not hasattr(obj, key):
                continue
            if isinstance(value, set):
                data[key] = dumps({ "type": "set", "value": list(value) })
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
        logger.error(f'Error in to_dict: {str(e)}\n\nKey: {key}:\nValue: {value}')

async def date_calc(old_date, return_str=False):
    if not isinstance(old_date, datetime):
        try:
            old_date = datetime.fromisoformat(old_date)
            if return_str:
                return old_date
        except ValueError:
            logger.error("error in date_calc: string isn't a valid datetime")
            return None

    now_date = datetime.now()
    return (now_date - old_date).total_seconds()

db = None
def start_db():
    global db
    valkey_client = None
    if conf.valkey_enabled:
        valkey_url = f"redis://{conf.valkey_user}:{conf.valkey_password}@{conf.valkey_uri}" if conf.valkey_user and conf.valkey_password else f"redis://{conf.valkey_uri}"
        valkey_client = ValkeyClient(valkey_url)
    db = IndexGroupInstances(conf.bot._loop, valkey_client)
