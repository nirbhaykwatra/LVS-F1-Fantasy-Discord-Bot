import settings
import discord
from discord import app_commands
from discord.ext import commands
from utilities import fastf1util as f1
from utilities import datautils as dt
from fastf1 import plotting
from datetime import datetime
from dateutil.relativedelta import relativedelta

logger = settings.create_logger('fantasy-fastf1')

drivers_standings = f1.get_drivers_standings(datetime.now().year)

#region Cog
class Formula1(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    stats_group = app_commands.Group(name='f1',
                                     description='Get information about Formula 1.',
                                     guild_ids=[settings.GUILD_ID])

    @stats_group.command(name='driver', description='Get information about Formula 1 drivers.')
    @app_commands.choices(driver=dt.drivers_choice_list())
    async def get_driver_data(self, interaction: discord.Interaction, driver: dt.Choice[str]):

        logger.info(f"Command 'driver' executed with name {driver.name} (TLA: {driver.value})")

        #region Driver Info embed
        driver_info_embed = discord.Embed(title=driver.name,
                                          url=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverUrl"][dt.drivers_choice_list().index(driver)],
                                          description=f'{driver.value}',
                                          colour=discord.Colour.from_str(plotting.get_driver_color(driver.name, f1.get_session(2024, 17, "R")))
                                          )

        driver_info_embed.set_author(name=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "constructorNames"][dt.drivers_choice_list().index(driver)][0])

        driver_info_embed.add_field(name=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverNumber"][dt.drivers_choice_list().index(driver)],
                                    value="Driver Number",
                                    inline=True)
        driver_info_embed.add_field(name=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "driverNationality"][dt.drivers_choice_list().index(driver)],
                                    value="Nationality",
                                    inline=True)

        date = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "dateOfBirth"][dt.drivers_choice_list().index(driver)].to_pydatetime()
        driver_info_embed.add_field(name=date.strftime("%d %b %Y"),
                                    value="Date of Birth",
                                    inline=True)
        driver_info_embed.add_field(name=str(drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "points"][dt.drivers_choice_list().index(driver)]),
                                    value="Points",
                                    inline=True)
        driver_info_embed.add_field(name=f'P{drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "positionText"][dt.drivers_choice_list().index(driver)]}',
                                    value="Championship Standing",
                                    inline=True)
        age = relativedelta(datetime.now(), date).years
        driver_info_embed.add_field(name=age,
                                    value="Age",
                                    inline=True)

        driver_first_name = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "givenName"][dt.drivers_choice_list().index(driver)]
        driver_last_name = drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "familyName"][dt.drivers_choice_list().index(driver)]

        driver_profile = f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png"
        logger.info(f'Driver URL: {driver_profile}')

        driver_info_embed.set_image(
            url=f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"
                f"/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01"
                f"_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png")
        #endregion

        #region Driver Statistics embed
        driver_stats_embed = discord.Embed(title=f"{str(drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "points"][dt.drivers_choice_list().index(driver)])} Points",
                                          colour=discord.Colour.from_str(
                                              plotting.get_driver_color(driver.value, f1.get_session(2024, 17, "R")))
                                          )

        driver_stats_embed.set_author(name=f"{driver.name}'s Season Summary")

        driver_stats_embed.add_field(name=drivers_standings.loc[drivers_standings["driverCode"] == driver.value, "wins"][dt.drivers_choice_list().index(driver)],
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
    pass