import discord
from discord import app_commands
from discord.ext import commands
import settings
from utilities import postgresql as sql
from utilities import drstatslib as stats
from utilities import fastf1util as f1

logger = settings.create_logger('fantasy-admin')

class FantasyAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='update-driver-stats', description='Update driver statistics.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.checks.has_role('Administrator')
    async def update_driver_stats(self, interaction: discord.Interaction, round: int):
        try:
            for driver in f1.get_drivers_standings(settings.F1_SEASON, round)['driverCode']:
                stats.calculate_driver_stats(driver, round)

            logger.info(f'Updated driver stats for round {round} of the {settings.F1_SEASON} season: \n {sql.drivers}')
            sql.update_driver_statistics()
        except Exception as e:
            logger.error(f'Updating driver statistics failed with exception: {e}')
            await interaction.response.send_message(f'Error updating driver statistics!', ephemeral=True)
        await interaction.response.send_message(f'Driver statistics updated.', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyAdmin(bot))
