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
    message_author = message.author
    message_content = message.content
    if message_author == bot.user:
        return
    else:
        logger.info(f'{message_author} messaged: {message_content}')
    await bot.process_commands(message)
#endregion

#region Commands

# Global error handler for command tree
@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingRole):
        await interaction.response.send_message(f"You don't have permission to use that command!", ephemeral=True)
    else:
        logger.error(error.args)

#region Developer message commands
@bot.group()
async def dev(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send(f'{ctx.subcommand_passed} is not a valid subcommand.')
    dev_logger.info(f"Invoked {ctx.subcommand_passed} subcommand.")


@dev.command(name='sync-tree')
@commands.has_role('Administrator')
async def sync_tree(ctx):
    await bot.tree.sync(guild=guild)
    await ctx.send(f'Command Tree synced.')
    dev_logger.info(f'Command Tree synced.')

@dev.command(name='reload-extensions')
@commands.has_role('Administrator')
async def reload_ext(ctx):
    for command in settings.CMDS_DIR.glob("*.py"):
        if command.name != '__init__.py':
            await bot.reload_extension(f'commands.{command.name[:-3]}')
            dev_logger.info(f"[COGS]    Reloaded '{command.name[:-3]}' cog.")
    await ctx.send(f'Extensions reloaded.')
    dev_logger.info(f'Extensions reloaded.')
#endregion

#endregion

# Run the bot. Note: This must be the last method to be called, owing to the fact that
# it is blocking and will not execute anything after it.
bot.run(settings.TOKEN)