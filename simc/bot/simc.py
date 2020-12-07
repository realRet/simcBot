from discord.ext import commands
import logging


Simc = commands.Bot(command_prefix='!')
logger = logging.getLogger(__name__)

Simc.load_extension('simc.bot.cogs.simulation')
