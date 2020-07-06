from houdini.plugins import IPlugin
from houdini import commands
from houdini.data.penguin import Penguin
from houdini import handlers
from houdini.handlers import XTPacket
import difflib
import asyncio
from houdini.handlers.login.world import world_login
from houdini.handlers.play.navigation import get_minutes_played_today
import time
import os
from houdini.converters import Credentials, WorldCredentials 
class Jumpdini(IPlugin):
    author = "Allinol"
    description = "Jumpdini plugin"
    version = "1.0.0"

    def __init__(self, server):
        super().__init__(server)

    async def ready(self):
        self.server.logger.info("Jumpline Plugin Ready!")
    
    @handlers.handler(XTPacket('q#sj'))
    async def connected_server(self, p, data):
        print(data[2][0])

        tr = p.server.redis.multi_exec()
        tr.incr(f'{p.username}.jumpkey')
        tr.expire(f'{p.username}.jumpkey', 120)
        await tr.execute()
        await p.room.send_xt('sjf', p.id)
        await p.send_xt('sj', 'jumpline', 'jumping')
        
        
    @handlers.handler(XMLPacket('login'), client=ClientType.Vanilla)
    @handlers.allow_once
    @handlers.depends_on_packet(XMLPacket('verChk'), XMLPacket('rndK'))
    async def handle_login(p, credentials: WorldCredentials):
        data = await Penguin.get(credentials.id)
        if await p.server.redis.exists(f"{p.username}.jumpkey"):
            return await world_login(p, data)
        else:
            tr = p.server.redis.multi_exec()
            tr.get(f'{credentials.username}.lkey')
            tr.get(f'{credentials.username}.ckey')
            tr.delete(f'{credentials.username}.lkey', f'{credentials.username}.ckey')
            login_key, confirmation_hash, _ = await tr.execute()
    
    
            if login_key is None or confirmation_hash is None:
                if await p.server.redis.exists(f"{data.username}.jumpkey"):
                    return await world_login(p, data)
                else:
                    return await p.close()

            login_key = login_key.decode()
            login_hash = Crypto.encrypt_password(login_key + p.server.config.auth_key) + login_key
        
            if credentials.client_key != login_hash:
                if await p.server.redis.exists(f"{data.username}.jumpkey"):
                    return await world_login(p, data)
                else:
                    return await p.close()

            if login_key != credentials.login_key or confirmation_hash.decode() != credentials.confirmation_hash:
                if await p.server.redis.exists(f"{data.username}.jumpkey"):
                    return await world_login(p, data)
                else:
                    return await p.close()
            
            p.login_key = login_key
            await world_login(p, data)
            
    @handlers.handler(XTPacket('j', 'js'), pre_login=True)
    @handlers.allow_once
    async def handle_join_server(p, penguin_id: int, login_key: str):
        if penguin_id != p.id:
            return await p.close()
        if not await p.server.redis.exists(f"{p.username}.jumpkey"):
            if login_key != p.login_key:
                return await p.close()
            
        await p.send_xt('activefeatures')

        moderator_status = 3 if p.character else 2 if p.stealth_moderator else 1 if p.moderator else 0

        await p.send_xt('js', int(p.agent_status), int(0),
                        moderator_status, int(p.book_modified))

        current_time = int(time.time())
        penguin_standard_time = current_time * 1000
    
        pst = pytz.timezone(p.server.config.timezone)
        dt = datetime.fromtimestamp(current_time, pst)
        server_time_offset = abs(int(dt.strftime('%z')) // 100)

        if p.timer_active:
            minutes_until_timer_end = datetime.combine(datetime.today(), p.timer_end) - datetime.now()
            minutes_until_timer_end = minutes_until_timer_end.total_seconds() // 60
    
            minutes_played_today = await get_minutes_played_today(p)
            minutes_left_today = (p.timer_total.total_seconds() // 60) - minutes_played_today
            p.egg_timer_minutes = int(min(minutes_until_timer_end, minutes_left_today))
        else:
            p.egg_timer_minutes = 24 * 60

        await p.send_xt('lp', await p.string, p.coins, int(p.safe_chat), p.egg_timer_minutes,
                        penguin_standard_time, p.age, 0, p.minutes_played,
                        p.membership_days_remain, server_time_offset, int(p.opened_playercard),
                        p.map_category, p.status_field)

        spawn = random.choice(p.server.rooms.spawn_rooms)
        await p.join_room(spawn)

        p.server.penguins_by_id[p.id] = p
        p.server.penguins_by_username[p.username] = p

        if p.character is not None:
        p.server.penguins_by_character_id[p.character] = p

        p.login_timestamp = datetime.now()
        p.joined_world = True

        server_key = f'houdini.players.{p.server.config.id}'
        await p.server.redis.sadd(server_key, p.id)
        await p.server.redis.hincrby('houdini.population', p.server.config.id, 1)
