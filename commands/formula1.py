from dateutil.relativedelta import relativedelta
import settings
import discord
import pandas as pd
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from utilities import fastf1util as f1
from utilities import datautils as dt
from utilities import postgresql as sql
from datetime import datetime

logger = settings.create_logger('fantasy-fastf1')

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
        driver_info = f1.get_driver_info(season='current')
        
        drivers_standings = f1.ergast.get_driver_standings(season='current')
        
        if not drivers_standings:
            drivers_standings = f1.get_drivers_standings(season=settings.F1_SEASON - 1)
            
        driverId = driver_info.loc[driver_info['driverCode'] == driver.value, 'driverId'].item()

        #TODO: Create a color map where {constructorId: color}. Use this map to get embed colors for both drivers and teams.
        #region Driver Info embed
        driver_info_embed = discord.Embed(title=f'{driver.name}',
                                          url=driver_info.loc[driver_info["driverCode"] == driver.value, "driverUrl"].item(),
                                          description=f'#{driver_info.loc[driver_info["driverCode"] == driver.value, "driverNumber"].item()} - {driver.value}',
                                          colour=discord.Colour.from_str(dt.constructors_color_map[f1.ergast.get_constructor_info(season='current', driver=driverId).constructorId.values[0]])
                                          )
        driver_info_embed.set_author(name=f'{dt.team_names_full[f1.ergast.get_constructor_info(season='current', driver=driverId).constructorId.values[0]]}')

        driver_info_embed.add_field(name=driver_info.loc[driver_info["driverCode"] == driver.value, "driverNationality"].item(),
                                    value="Nationality",
                                    inline=True)
        date = driver_info.loc[driver_info["driverCode"] == driver.value, "dateOfBirth"].item().to_pydatetime()
        driver_info_embed.add_field(name=date.strftime("%d %b %Y"),
                                    value="Date of Birth",
                                    inline=True)
        age = relativedelta(datetime.now(), date).years
        driver_info_embed.add_field(name=age,
                                    value="Age",
                                    inline=True)

        driver_first_name = driver_info.loc[driver_info["driverCode"] == driver.value, "givenName"].item()
        driver_last_name = driver_info.loc[driver_info["driverCode"] == driver.value, "familyName"].item()

        driver_info_embed.set_image(
            url=f"https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers"
                f"/{driver_first_name[0].upper()}/{driver_first_name[0:3].upper()}{driver_last_name[0:3].upper()}01"
                f"_{driver_first_name}_{driver_last_name}/{driver_first_name[0:3]}{driver_last_name[0:3]}01.png")
        #endregion

        #region Driver Statistics embed
        '''
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
        '''
        #endregion

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f'', embeds=[driver_info_embed], ephemeral=True)

    @stats_group.command(name='manufacturer', description='Get information about Formula 1 constructors.')
    @app_commands.choices(team=dt.constructor_choice_list())
    async def get_constructor_data(self, interaction: discord.Interaction, team: Choice[str]):
        await interaction.response.defer(ephemeral=True)
        constructor_standings = f1.ergast.get_constructor_standings(season='current').content
        
        if not constructor_standings:
            constructor_standings = f1.ergast.get_constructor_standings(season=settings.F1_SEASON - 1).content[0]
        else:
            constructor_standings = constructor_standings[0]
        
        constructor_embed = discord.Embed(
            title=f'{team.name}', colour=discord.Colour.from_str(dt.constructors_color_map[team.value])
        )
        
        constructor_embed.set_author(name=f'Constructor')
        for index, driver in enumerate(f1.ergast.get_driver_info(season='current', constructor=team.value).driverId):
            constructor_embed.add_field(value=f"{f1.ergast.get_driver_info(season='current', constructor=team.value).givenName[index]} "
                                             f"{f1.ergast.get_driver_info(season='current', constructor=team.value).familyName[index]}", 
                                        name=f"Driver {index + 1}", inline=True)
            
        constructor_embed.add_field(name=f"Championship Standing", 
                                    value=f"P{constructor_standings.loc[constructor_standings['constructorId'] == team.value, 'position'].item()}", inline=False)
        constructor_embed.add_field(name=f"Championship Points", value=f"{constructor_standings.loc[constructor_standings['constructorId'] == team.value, 'points'].item()}"
                                    , inline=True)
        
        constructor_embed.set_image(
            url=f"https://media.formula1.com/image/upload/content/dam/fom-website/2018-redesign-assets/team%20logos/"
                f"{team.value}"
        )
        
        await interaction.followup.send(embeds=[constructor_embed], ephemeral=True)

    @stats_group.command(name='grand-prix', description='Get information about Formula 1 Grand Prix events.')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def get_grand_prix_data(self, interaction: discord.Interaction, grand_prix: dt.Choice[str]):
        #TODO: Create embed with grand prix circuit, country and start time information. If there are some interesting historical stats,
        # those would be nice too.
        
        await interaction.response.defer(ephemeral=True)
        
        event_schedule = f1.event_schedule
        circuit_info = f1.ergast.get_circuits(season='current')
        user_tz = sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()
        
        grand_prix_info = event_schedule.loc[event_schedule['RoundNumber'] == int(grand_prix.value)]
        grand_prix_circuit = circuit_info.loc[circuit_info['circuitId'] == dt.circuit_map[grand_prix.value], 'circuitName']
        
        session1Utc: pd.Timestamp = grand_prix_info.Session1DateUtc.item().tz_localize('UTC')
        session2Utc: pd.Timestamp = grand_prix_info.Session2DateUtc.item().tz_localize('UTC')
        session3Utc: pd.Timestamp = grand_prix_info.Session3DateUtc.item().tz_localize('UTC')
        session4Utc: pd.Timestamp = grand_prix_info.Session4DateUtc.item().tz_localize('UTC')
        session5Utc: pd.Timestamp = grand_prix_info.Session5DateUtc.item().tz_localize('UTC')

        
        embed = discord.Embed(title=f"{grand_prix_info.OfficialEventName.item()}",
                              description=f"{grand_prix_circuit.item()}",
                              colour=settings.EMBED_COLOR)

        if grand_prix_info.EventFormat.item() == "conventional":
            embed.set_author(name=f"Grand Prix")
        if grand_prix_info.EventFormat.item() == "sprint_qualifying":
            embed.set_author(name=f"Sprint")
            
        
        embed.add_field(name="Weekend Overview",
                        value="",
                        inline=False)
        embed.add_field(name="Friday",
                        value="...........................................................................",
                        inline=False)

        embed.add_field(name=f"{grand_prix_info.Session1.item()}",
                        value=f"{session1Utc.astimezone(user_tz).strftime('%d %B %Y at %I:%M %p')}",
                        inline=True)
        embed.add_field(name=f"{grand_prix_info.Session2.item()}",
                        value=f"{session2Utc.astimezone(user_tz).strftime('%d %B %Y at %I:%M %p')}",
                        inline=True)
        embed.add_field(name="Saturday",
                        value="...........................................................................",
                        inline=False)
        embed.add_field(name=f"{grand_prix_info.Session3.item()}",
                        value=f"{session3Utc.astimezone(user_tz).strftime('%d %B %Y at %I:%M %p')}",
                        inline=True)
        embed.add_field(name=f"{grand_prix_info.Session4.item()}",
                        value=f"{session4Utc.astimezone(user_tz).strftime('%d %B %Y at %I:%M %p')}",
                        inline=True)
        embed.add_field(name="Sunday",
                        value=".............................................................................",
                        inline=False)
        embed.add_field(name=f"{grand_prix_info.Session5.item()}",
                        value=f"{session5Utc.astimezone(user_tz).strftime('%d %B %Y at %I:%M %p')}",
                        inline=True)
        
        embed.set_image(url=f"https://media.formula1.com/image/upload/content/dam/fom-website/2018-redesign-assets/Circuit%20maps%2016x9/{dt.img_url_map[grand_prix.value]}_Circuit")
                
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Formula1(bot))
#endregion

if __name__ == '__main__':
    logger.info(sql.drivers.loc[sql.drivers['driverCode'] == "VER", 'podiums'].item())
    pass