import discord
from discord import app_commands
from discord.ext import commands

import settings
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

        await interaction.response.defer(ephemeral=True)

        guild = self.bot.get_guild(settings.GUILD_ID)
        season = f1.event_schedule

        if guild is not None:

            for event in range(0, len(season['RoundNumber'])):
                logger.info(f"Round {event} ----------------------------------------------------------------------")

                name = season['OfficialEventName'][event]
                logger.info(f"Event Name: {name}")

                start_time: dt.pd.Timestamp = season['Session5Date'][event]
                logger.info(f"Event Start Time: {start_time}")

                end_time = start_time + dt.timedelta(hours=3)
                logger.info(f"Event End Time: {end_time}")

                location = season['Location'][event]
                logger.info(f"Event Location: {location}")


                await guild.create_scheduled_event(
                    name=name,
                    start_time=start_time,
                    end_time=end_time,
                    location=location,
                    entity_type=discord.EntityType.external,
                    privacy_level=discord.PrivacyLevel.guild_only,
                )

        embed = discord.Embed(
            title='Season calendar has been added.',
            description='',
            colour=settings.EMBED_COLOR
        )
        embed.set_author(name="Setup")

        await interaction.followup.send(embed=embed)
        
    @setup_group.command(name='create-league', description='Create a new league.')
    @app_commands.checks.has_role('Administrator')
    async def create_league(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Create League command executed successfully.", ephemeral=True)
        pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasySetup(bot))