import pyromod.listen
from collections import defaultdict
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN, STRING_SESSION, LOGIN_SYSTEM

# 🛠️ Fix Pyromod KeyError: <ListenerTypes.MESSAGE: 'message'> Bug
original_client_init = Client.__init__

def patched_client_init(self, *args, **kwargs):
    original_client_init(self, *args, **kwargs)
    # Convert listeners dict to defaultdict so missing keys return empty list [] instead of KeyError
    existing_listeners = getattr(self, "listeners", {})
    self.listeners = defaultdict(list, existing_listeners if isinstance(existing_listeners, dict) else {})

Client.__init__ = patched_client_init


if STRING_SESSION and not LOGIN_SYSTEM:
    TechVJUser = Client("TituUser", api_id=API_ID, api_hash=API_HASH, session_string=STRING_SESSION)
    TechVJUser.start()
else:
    TechVJUser = None

class Bot(Client):
    def __init__(self):
        super().__init__(
            "TituBot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="Titu"),
            workers=100,
            sleep_threshold=10
        )

    async def start(self):
        await super().start()
        print('✅ Titu Bot Successfully Started! Powered by @SarveshAsatkarr')

    async def stop(self, *args):
        await super().stop()
        print('🛑 Titu Bot Stopped.')

if __name__ == "__main__":
    bot = Bot()
    bot.run()
