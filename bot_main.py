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

logger = settings.create_logger('bot-main')
dev_logger = settings.create_logger('dev')

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
bot = commands.Bot(command_prefix='!', intents=intents)
guild = discord.Object(id=settings.GUILD_ID)
#endregion


#region Bot Event Handlers

@bot.event
async def setup_hook():
    for command in settings.CMDS_DIR.glob("*.py"):
        if command.name != '__init__.py':
            await bot.load_extension(f'commands.{command.name[:-3]}')
            logger.info(f"[COGS]    Loaded '{command.name[:-3]}' cog.")


@bot.event
async def on_ready():
    logger.info(f'Fantasy Manager is ready.')
    logger.info(f'{bot.user.name} connected to {bot.get_guild(guild.id)} (guild ID: {guild.id})')


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

@app_commands.command(name='reload-ext', description='Reload the bot extensions')
@app_commands.guilds(discord.Object(id=settings.GUILD_ID))
@app_commands.checks.has_role('Administrator')
async def reloadext(self, interaction: discord.Interaction):
    await interaction.response.send_message(f'Extensions reloaded.')


#endregion

# Run the bot. Note: This must be the last method to be called, owing to the fact that
# it is blocking and will not execute anything after it.
bot.run(settings.TOKEN)