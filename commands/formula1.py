from dateutil.relativedelta import relativedelta
import settings
import discord
from discord import app_commands
from discord.ext import commands
from utilities import fastf1util as f1
from utilities import datautils as dt
from utilities import drstatslib as stats
from utilities import postgresql as sql
from fastf1 import plotting
from datetime import datetime

logger = settings.create_logger('fantasy-fastf1')

try:
    drivers_standings = f1.get_drivers_standings(datetime.now().year)
except IndexError as e:
    drivers_standings = f1.get_drivers_standings(datetime.now().year - 1)
    logger.warning(
        f"Unable to retrieve driver standings for the year {datetime.now().year}! Retrieved driver standings for the year {datetime.now().year - 1} instead.")

#region Cog
class Formula1(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    stats_group = app_commands.Group(name='f1',
                                     description='Get information about Formula 1.',
                                     guild_ids=[settings.GUILD_ID])

    @stats_group.command(name='driver', description='Get information about Formula 1 drivers.')
    @app_commands.choices(driver=dt.drivers_choice_list(info=True))
    async def get_driver_data(self, interaction: discord.Interaction, driver: dt.Choice[str]):

        logger.info(f"Command 'driver' executed with name {driver.name} (TLA: {driver.value})")

        #region Driver Info embed
        driver_info_embed = discord.Embed(title=f'{driver.name}',
                                          url=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverUrl"][dt.drivers_choice_list(info=True).index(driver)],
                                          description=f'#{drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverNumber"][dt.drivers_choice_list(info=True).index(driver)]} - {driver.value}',
                                          colour=discord.Colour.from_str(str(sql.drivers.loc[sql.drivers["driverCode"] == driver.value, "drivercolor"].item()))
                                          )

        driver_info_embed.set_author(name=f'{dt.get_full_team_name(drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "constructorNames"][dt.drivers_choice_list(info=True).index(driver)][0])}')

        driver_info_embed.add_field(name=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverNationality"][dt.drivers_choice_list(info=True).index(driver)],
                                    value="Nationality",
                                    inline=True)
        date = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "dateOfBirth"][dt.drivers_choice_list(info=True).index(driver)].to_pydatetime()
        driver_info_embed.add_field(name=date.strftime("%d %b %Y"),
                                    value="Date of Birth",
                                    inline=True)
        age = relativedelta(datetime.now(), date).years
        driver_info_embed.add_field(name=age,
                                    value="Age",
                                    inline=True)

        driver_first_name = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "givenName"][dt.drivers_choice_list(info=True).index(driver)]
        driver_last_name = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "familyName"][dt.drivers_choice_list(info=True).index(driver)]

        driver_info_embed.set_image(
            url=f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"
                f"/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01"
                f"_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png")
        #endregion

        #region Driver Statistics embed

        driver_stats_embed = discord.Embed(title=f"P{drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "positionText"][dt.drivers_choice_list(info=True).index(driver)]} - {str(drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "points"][dt.drivers_choice_list(info=True).index(driver)])} Points",
                                          colour=discord.Colour.from_str(str(sql.drivers.loc[sql.drivers["driverCode"] == driver.value, "drivercolor"].item()))
                                          )

        driver_stats_embed.set_author(name=f"{driver.name}'s Season Summary")

        driver_stats_embed.add_field(
            name=f'{drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "wins"][
                      dt.drivers_choice_list(info=True).index(driver)]}',
            value="Wins",
            inline=True)

        driver_stats_embed.add_field(name=sql.drivers.loc[sql.drivers['driverCode'] == driver.value, 'podiums'].item(),
                                    value="Podiums",
                                    inline=True)

        driver_stats_embed.add_field(name="Against Teammate (Race)",
                                    value=f'',
                                    inline=False)

        driver_stats_embed.add_field(name="Against Teammate (Qualifying)",
                                    value=f'',
                                    inline=True)
        #endregion

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f'', embeds=[driver_info_embed, driver_stats_embed], ephemeral=True)

    @stats_group.command(name='grand-prix', description='Get information about Formula 1 Grand Prix events.')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def get_grand_prix_data(self, interaction: discord.Interaction, grand_prix: dt.Choice[str]):
        #TODO: Create embed with grand prix circuit, country and start time information. If there are some interesting historical stats,
        # those would be nice too.
        await interaction.response.send_message(f'Here is your grand prix info: ', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Formula1(bot))
#endregion

if __name__ == '__main__':
    logger.info(sql.drivers.loc[sql.drivers['driverCode'] == "VER", 'podiums'].item())
    pass