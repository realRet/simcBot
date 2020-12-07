import threading

from simc.bot import Simc
from simc.config import settings
from simc.webapp.server import webservice


if __name__ == '__main__':
    thread = threading.Thread(target=webservice, args=())
    thread.daemon = True
    thread.start()

    Simc.run(settings.DISCORD_API_TOKEN)
