import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import settings
from utilities import postgresql as sql
from utilities import drstatslib as stats
from utilities import fastf1util as f1
from utilities import datautils as dt

logger = settings.create_logger('fantasy-setup')

class FantasySetup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    setup_group = app_commands.Group(name='setup',
                                     description='A group of commands used for setting up a new season.',
                                     guild_ids=[settings.GUILD_ID])

    @setup_group.command(name='add-season-events', description='Add all F1 races to the server event calendar.')
    @app_commands.checks.has_role('Administrator')
    async def add_season_events(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title='Season calendar has been added.',
            description=''
        )

        embed.set_author(name="Setup")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasySetup(bot))