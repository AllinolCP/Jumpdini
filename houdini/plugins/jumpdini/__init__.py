from houdini.plugins import IPlugin
from houdini import commands
from houdini.data.penguin import Penguin
from houdini import handlers
from houdini.handlers import XTPacket, XMLPacket
import difflib
import asyncio
from houdini.constants import ClientType
from houdini.handlers.login.world import world_login
from houdini.handlers.play.navigation import get_minutes_played_today
import time
import os
import random
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
