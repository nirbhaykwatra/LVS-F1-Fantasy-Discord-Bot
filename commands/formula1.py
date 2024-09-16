import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
import fastf1
from fastf1.ergast import Ergast
import pandas as pd

#region Initialize FastF1
logger = settings.create_logger('fantasy-fastf1')
fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
ergast = Ergast()
fastf1.Cache.enable_cache(f'G:\\projects\\personal\\programming\\LVS-F1-Fantasy-Discord-Bot\\data\\fastf1\\cache')
#endregion

#region FastF1 Data
def fastf1_run():

    print_var = ergast.get_driver_standings(2024).content[0]
    logger.info(drivers())

#endregion

#region Command Choices

def drivers() -> []:
    drivers_list = []

    driver_standings = ergast.get_driver_standings(2024).content[0]
    lastname_series = driver_standings.familyName
    firstname_series = driver_standings.givenName
    tla_series = driver_standings.driverCode

    for driver in range(0, len(driver_standings.position)):
        first_name = firstname_series.get(driver)
        last_name = lastname_series.get(driver)
        tla = tla_series.get(driver)

        drivers_list.append(Choice(name=f"{first_name} {last_name}", value=tla))

    return drivers_list

#endregion

#region Cog
class Formula1(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    stats_group = app_commands.Group(name='f1',
                                     description='Get information about Formula 1.',
                                     guild_ids=[settings.GUILD_ID])

    @stats_group.command(name='driver', description='Get information about Formula 1 drivers.')
    @app_commands.choices(driver=drivers())
    async def get_driver_data(self, interaction: discord.Interaction, driver: Choice[str]):
        await interaction.response.send_message(f'Information about {driver.name}: ', ephemeral=True)

    @stats_group.command(name='grand-prix', description='Get information about Formula 1 Grand Prix events.')
    async def get_grand_prix_data(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Here is your grand prix info: ', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Formula1(bot))
#endregion

if __name__ == '__main__':
    fastf1_run()