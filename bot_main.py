#region Imports
import os

from discord.app_commands import MissingRole
from dotenv import load_dotenv
import logging

import discord
from discord.ext import commands
from discord import app_commands

import commands as cmds
import settings

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


#region Command Checks

#endregion

#region Commands

# Global error handler for command tree
@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message(f"You don't have permission to use that command!", ephemeral=True)


@bot.tree.command(name='hello', description='Say hello to your little friend', guild=guild)
@app_commands.checks.has_role('Administrator')
async def hello(interaction: discord.Interaction):
    logger.info(f'User role: {interaction.user.roles[1].name}')
    await interaction.response.send_message(f'Hello, {interaction.user.name}! Nice to meet you!', ephemeral=True)


#endregion

# Run the bot. Note: This must be the last method to be called, owing to the fact that
# it is blocking and will not execute anything after it.
bot.run(os.getenv('TOKEN'))