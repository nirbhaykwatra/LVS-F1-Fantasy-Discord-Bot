import discord
import pandas as pd
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands

import settings
from utilities import postgresql as sql
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

    @debug_group.command(name='remove-player-database', description='Remove selected user table from database.')
    @app_commands.checks.has_role('Administrator')
    async def remove_player_database(self, interaction: discord.Interaction, user: discord.User):
        sql.remove_player_table(user.id)
        await interaction.response.send_message(f"Successfully removed {user.name}'s Player Database.", ephemeral=True)

    @debug_group.command(name='set-current-round', description='Set the current round.')
    @app_commands.checks.has_role('Administrator')
    async def set_current_round(self, interaction: discord.Interaction, round_number: int):
        settings.F1_ROUND = round_number
        await interaction.response.send_message(f'Current round set to round {settings.F1_ROUND}', ephemeral=True)

    @debug_group.command(name='show-current-round', description='Show the current round.')
    @app_commands.checks.has_role('Administrator')
    async def show_current_round(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Current round is round {settings.F1_ROUND}', ephemeral=True)
        
    @debug_group.command(name='increment-round', description='Increment the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def increment_round(self, interaction: discord.Interaction, number_of_rounds: int):
        initial_round = settings.F1_ROUND
        settings.F1_ROUND += number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round + number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='decrement-round', description='Decrement the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def decrement_round(self, interaction: discord.Interaction, number_of_rounds: int):
        initial_round = settings.F1_ROUND
        settings.F1_ROUND -= number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round - number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='check-driver-teams', description='Check if two or more drivers are in the same team.')
    @app_commands.checks.has_role('Administrator')
    async def check_driver_teams(self, interaction: discord.Interaction, driver1: str, driver2: str, driver3: str, driver4: str):
        selected_drivers = [driver1, driver2, driver3, driver4]
        driver_info = f1.get_driver_info(settings.F1_SEASON)
        logger.info(f'Driver Info: {driver_info}')
        
        await interaction.response.send_message(f"check-driver-teams command executed.", ephemeral=True)

    @debug_group.command(name='check-draft-deadline', description='Check draft deadline for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def check_draft_deadline(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        timings = sql.retrieve_timings()
        deadline = timings.loc[timings['round'] == int(grand_prix.value), 'deadline'].to_list()
        reset = timings.loc[timings['round'] == int(grand_prix.value), 'reset'].to_list()
        await interaction.response.send_message(f"Draft deadline for {grand_prix.name} is {deadline[0]} and reset is {reset[0]}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyDebug(bot))
