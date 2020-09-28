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
    
    @handlers.handler(XTPacket('q, sj'))
    async def connected_server(self, p, data):
        random_key = Crypto.generate_random_key()
        login_key = Crypto.hash(random_key[::-1])
        confirmation_hash = Crypto.hash(os.urandom(24))
        tr = p.server.redis.multi_exec()
        tr.setex(f'{p.username}.lkey', p.server.config.auth_ttl, login_key)
        tr.setex(f'{p.username}.ckey', p.server.config.auth_ttl, confirmation_hash)
        await tr.execute()
        await p.room.send_xt('sjf', p.id)
        await p.send_xt('sj', int(data=='jumpline'), confirmation_hash)  
