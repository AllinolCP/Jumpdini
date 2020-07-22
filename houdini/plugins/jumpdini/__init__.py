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
