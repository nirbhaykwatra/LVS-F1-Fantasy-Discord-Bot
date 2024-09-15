#region Imports
import os

from discord.app_commands import MissingRole
from dotenv import load_dotenv
import logging

import discord
from discord.ext import commands
from discord import app_commands
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
bot = cmds.Bot(command_prefix='!', intents=intents)
guild = discord.Object(id=int(os.getenv('GUILD_ID')))
#endregion

@bot.event
async def on_ready():
    logging.info(f'{bot.user} logged into guild {bot.get_guild(guild.id)} with guild ID {guild.id}')

@bot.event
async def on_message(message):
    author = message.author
    message = message.content
    if author == bot.user:
        return
    else:

        logging.info(f'[Message] {author}: {message}')

bot.run(os.getenv('TOKEN'))