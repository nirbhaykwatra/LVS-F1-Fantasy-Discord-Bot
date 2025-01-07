import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import settings
from utilities import postgresql as sql
from utilities import drstatslib as stats
from utilities import fastf1util as f1
from utilities import datautils as dt

logger = settings.create_logger('fantasy-debug')

class FantasyDebug(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    debug_group = app_commands.Group(name='debug',
                                     description='A group of debug commands.',
                                     guild_ids=[settings.GUILD_ID])

    @debug_group.command(name='show-excluded-drivers', description='Show drivers excluded from driver choice list.')
    @app_commands.checks.has_role('Administrator')
    async def show_excluded_drivers(self, interaction: discord.Interaction):
        excluded_drivers = dt.exclude_drivers
        logger.info(f'Excluded drivers: {excluded_drivers}')

        embed = discord.Embed(
            title='Excluded Drivers',
            description='Drivers excluded from driver choice list.'
        )

        embed.set_author(name="Debug")

        for driver in excluded_drivers:
            if driver is not None:
                embed.add_field(
                    name=driver,
                    value=''
                )
            else:
                embed.add_field(name='There are no excluded drivers.', value="")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug_group.command(name='remove-season-events', description='Remove all season events from server calendar.')
    @app_commands.checks.has_role('Administrator')
    async def remove_season_events(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = self.bot.get_guild(settings.GUILD_ID)

        if guild is not None:

            events = guild.scheduled_events

            for event in events:
                await event.delete()

            await interaction.followup.send(f"Season events removed.")

        else:
            await interaction.followup.send(f"Could not retrieve guild! Perhaps the guild ID is incorrect?")




async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyDebug(bot))
