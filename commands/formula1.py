import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
import fastf1
from fastf1.ergast import Ergast
from fastf1 import plotting
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

#region Initialize FastF1
logger = settings.create_logger('fantasy-fastf1')
fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
ergast = Ergast()
fastf1.Cache.enable_cache(f'G:\\projects\\personal\\programming\\LVS-F1-Fantasy-Discord-Bot\\data\\fastf1\\cache')
#endregion

#region FastF1 Data
wdc_standings = ergast.get_driver_standings(datetime.now().year).content[0]
ff1session = fastf1.get_session(2024, 17, "R")

def fastf1_run():

    print_var = ergast.get_driver_standings(2024).content[0]
    logger.info(f"pass")

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

        logger.info(f"Command 'driver' executed with name {driver.name} (TLA: {driver.value})")

        #region Driver Info embed
        driver_info_embed = discord.Embed(title=driver.name,
                                          url=wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "driverUrl"][drivers().index(driver)],
                                          description=f'{driver.value}',
                                          colour=discord.Colour.from_str(plotting.get_driver_color(driver.name, ff1session))
                                          )

        driver_info_embed.set_author(name=wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "constructorNames"][drivers().index(driver)][0])

        driver_info_embed.add_field(name=wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "driverNumber"][drivers().index(driver)],
                                    value="Driver Number",
                                    inline=True)
        driver_info_embed.add_field(name=wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "driverNationality"][drivers().index(driver)],
                                    value="Nationality",
                                    inline=True)

        date = wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "dateOfBirth"][drivers().index(driver)].to_pydatetime()
        driver_info_embed.add_field(name=date.strftime("%d %b %Y"),
                                    value="Date of Birth",
                                    inline=True)
        driver_info_embed.add_field(name=str(wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "points"][drivers().index(driver)]),
                                    value="Points",
                                    inline=True)
        driver_info_embed.add_field(name=f'P{wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "positionText"][drivers().index(driver)]}',
                                    value="Championship Standing",
                                    inline=True)
        age = relativedelta(datetime.now(), date).years
        driver_info_embed.add_field(name=age,
                                    value="Age",
                                    inline=True)

        driver_first_name = wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "givenName"][drivers().index(driver)]
        driver_last_name = wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "familyName"][drivers().index(driver)]

        driver_profile = f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png"
        logger.info(f'Driver URL: {driver_profile}')

        driver_info_embed.set_image(
            url=f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"
                f"/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01"
                f"_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png")
        #endregion

        #region Driver Statistics embed
        driver_stats_embed = discord.Embed(title=f"{str(wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "points"][drivers().index(driver)])} Points",
                                          colour=discord.Colour.from_str(
                                              plotting.get_driver_color(driver.value, ff1session))
                                          )

        driver_stats_embed.set_author(name=f"{driver.name}'s Season Summary")

        driver_stats_embed.add_field(name=wdc_standings.loc[wdc_standings["driverCode"] == driver.value, "wins"][drivers().index(driver)],
                                    value="Wins",
                                    inline=True)

        driver_stats_embed.add_field(name="Podiums",
                                    value=f'',
                                    inline=True)

        driver_stats_embed.add_field(name="Championship Standing",
                                    value=f'',
                                    inline=True)

        driver_stats_embed.add_field(name="Against Teammate (Race)",
                                    value=f'',
                                    inline=True)

        driver_stats_embed.add_field(name="Against Teammate (Qualifying)",
                                    value=f'',
                                    inline=True)
        driver_stats_embed.add_field(name="",
                                    value=f'Constructor',
                                    inline=True)
        #endregion

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f'', embeds=[driver_info_embed, driver_stats_embed], ephemeral=True)

    @stats_group.command(name='grand-prix', description='Get information about Formula 1 Grand Prix events.')
    async def get_grand_prix_data(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Here is your grand prix info: ', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Formula1(bot))
#endregion

if __name__ == '__main__':
    fastf1_run()