#region Imports
import os

from discord.app_commands import MissingRole
from dotenv import load_dotenv
import logging

import discord
from discord.ext import commands
from discord import app_commands
#endregion


#region Logging Setup

# Create logger object
logger = logging.getLogger('bot-main')

# Set level to DEBUG for base logger object
logger.setLevel(logging.DEBUG)

# Create logging format for console handler
logFormat = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}',
                         datefmt='%Y-%m-%d %H:%M:%S',
                         style='{')

# Create console handler object
console = logging.StreamHandler()
# Set level to INFO for console handler
console.setLevel(logging.INFO)
# Set format to logFormat for console handler
console.setFormatter(logFormat)
# Add console handler to logger
logger.addHandler(console)

#endregion


#region Initialize Intents
intents = discord.Intents.none()
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.emojis_and_stickers = True
intents.guild_scheduled_events = True
#endregion


#region Bot Setup
load_dotenv()
bot = commands.Bot(command_prefix='!', intents=intents)
guild = discord.Object(id=int(os.getenv('GUILD_ID')))
#endregion


#region Bot Event Handlers
@bot.event
async def on_ready():
    logger.info(f'Fantasy Manager is ready.')
    logger.info(f'{bot.user.name} connected to {bot.get_guild(guild.id)} (guild ID: {guild.id})')

    try:
        await bot.tree.sync(guild=guild)
        logger.info(f'Command Tree synced.')
    except Exception as e:
        logger.error(f'Command Tree sync failed with exception: {e}')


@bot.event
async def on_message(message):
    author = message.author
    message = message.content
    if author == bot.user:
        return
    else:
        logging.info(f'{author} messaged: {message}')
#endregion


        logging.info(f'[Message] {author}: {message}')

bot.run(os.getenv('TOKEN'))