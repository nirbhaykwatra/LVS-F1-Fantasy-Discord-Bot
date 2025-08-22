import json
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
from utilities import datautils as dt
from utilities import postgresql as sql
from utilities import fastf1util as f1
import pandas as pd
import df2img as d2i
import utilities.timing as timing

logger = settings.create_logger('fantasy-user')

class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #region Basic functions
    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(timezone=dt.timezone_choice_list())
    async def register(self, interaction: discord.Interaction,  timezone: dt.Choice[str], team_name: str, team_motto: str = "The one and only!"):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /register with parameters: timezone: {timezone}, team_name: {team_name}, team_motto: {team_motto}")
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id in sql.players.userid.to_list():
            registered_embed = discord.Embed(
                title=f"You are already registered!",
                colour=settings.EMBED_COLOR
            )
            await interaction.followup.send(embed=registered_embed, ephemeral=True)
            return

        #region Create new player Series
        player_record = pd.Series({'username': interaction.user.name,
                         'userid': interaction.user.id,
                         'teamname': f"{team_name}",
                         'teammotto': f"{team_motto}", 
                         'points': 0,
                         'timezone': timezone.value
                                   })
        results_record = pd.Series({'userid': interaction.user.id,
                                    'username': interaction.user.name,
                                    'teamname': f"{team_name}"})
        #endregion

        sql.players = pd.concat([sql.players, player_record.to_frame().T], ignore_index=True)
        sql.results = pd.concat([sql.results, results_record.to_frame().T], ignore_index=True)
        
        for event in range(0, len(f1.event_schedule.RoundNumber.to_list())):
            sql.results.loc[sql.results['userid'] == interaction.user.id, f'round{event + 1}'] = 0
        
        sql.create_player_table(interaction.user.id)
        sql.write_to_fantasy_database('players', sql.players)
        sql.write_to_fantasy_database('results', sql.results)
        sql.import_players_table()
        sql.import_results_table()
        
        logger.info(f"Registered player {interaction.user.name}.")

        #region Player Profile embed
        embed = discord.Embed(title=f"{sql.players.loc[sql.players['userid'] == interaction.user.id, 'teamname'].item()}",
                              description=f"{sql.players.loc[sql.players['userid'] == interaction.user.id, 'teammotto'].item()}",
                              colour=settings.EMBED_COLOR)

        embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == interaction.user.id, 'username'].item()}")

        user_points = sql.players.loc[sql.players['userid'] == interaction.user.id, 'points']
        if user_points.dropna().empty:
            embed.add_field(name=f"0",
                            value=f"Season Points",
                            inline=True)
        else:
            embed.add_field(name=f"{user_points.item()}",
                            value=f"Season Points",
                            inline=True)

        user_row = sql.results.loc[sql.results['userid'] == interaction.user.id].drop(labels=['userid','username','teamname'],
                                                                          axis=1).squeeze()
        if user_row.empty:
            embed.add_field(name=f"0",
                            value=f"Most Points Scored",
                            inline=True)
        else:
            embed.add_field(name=f"{user_row.max()}",
                            value=f"Most Points Scored",
                            inline=True)
        embed.set_image(url=interaction.user.display_avatar.url)
        #endregion

        await interaction.followup.send(f'Registered player {interaction.user.name}!', embed=embed, ephemeral=True)

    @app_commands.command(name='draft', description='Draft your team!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(driver1=dt.drivers_choice_list(),
                          driver2=dt.drivers_choice_list(),
                          driver3=dt.drivers_choice_list(),
                          bogey_driver=dt.drivers_choice_list(),
                          team=dt.constructor_choice_list(),
                          )
    async def draft(self, interaction: discord.Interaction,
                    driver1: Choice[str],
                    driver2: Choice[str],
                    driver3: Choice[str],
                    bogey_driver: Choice[str],
                    team: Choice[str],
                    ):
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to draft!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return


        grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                            value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                            )


        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /draft with parameters: {driver1.name}, {driver2.name}, {driver3.name}, {bogey_driver.name}, {dt.team_names_full[team.value]} for the {grand_prix.name}")
        
        # Deadline check
        embed_deadline = discord.Embed(title="The draft deadline has passed!", description="In case of extraordinary circumstances, contact the league administrator to see if they can "
                                                                                           "draft your team for you.", colour=settings.EMBED_COLOR)
        
        bDraftDeadlinePassed = timing.has_deadline_passed(int(grand_prix.value), sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item(), 'deadline')
        
        if bDraftDeadlinePassed:
            await interaction.followup.send(embed=embed_deadline, ephemeral=True)
            return 
            
        #region Draft Checks
        
        # Duplicate Check
        team_list = [driver1, driver2, driver3, bogey_driver]
        
        bHasDuplicateDriver = len(team_list) != len(set(team_list))

        embed_duplicate = discord.Embed(title="Invalid Draft!", description="You have chosen one driver more than once! Please try again.", colour=settings.EMBED_COLOR)
        if bHasDuplicateDriver:
            await interaction.followup.send(embed=embed_duplicate, ephemeral=True)
        
        # Exhausted Check
        player_table = sql.retrieve_player_table(interaction.user.id)

        last_team = player_table[player_table['round'] == settings.F1_ROUND - 1].squeeze()
        second_last_team = player_table[player_table['round'] == settings.F1_ROUND - 2].squeeze()

        common = pd.Series(list(set(last_team).intersection(set(second_last_team))))
        
        driver_info = f1.get_driver_info(season='current')
        
        exhausted = []
        embed_exhausted = discord.Embed(title="Invalid Draft!", description="One or more of the following picks are exhausted!", colour=settings.EMBED_COLOR)
        
        for element in common:
            if driver1.value == element or driver2.value == element or driver3.value == element or bogey_driver.value == element:
                embed_exhausted.add_field(name=f"{driver_info.loc[driver_info['driverCode'] == element, 'givenName'].item()} "
                                               f"{driver_info.loc[driver_info['driverCode'] == element, 'familyName'].item()}", value="Exhausted!", inline=False)
                exhausted.append(element)
                
            if team.value == element:
                embed_exhausted.add_field(name=f"{dt.team_names_full[element]}", value="Exhausted!", inline=False)
                exhausted.append(element)
                
        bPickExhausted = len(exhausted) != 0
        
        if bPickExhausted:
            await interaction.followup.send(embed=embed_exhausted, ephemeral=True)

        # Bogey Driver Check
        '''
        try:
            constructor_standings = f1.ergast.get_constructor_standings(season='current').content[0]
        except IndexError as e:
            constructor_standings = f1.ergast.get_constructor_standings(season=settings.F1_SEASON - 1).content[0]
            logger.warning(
                    f"Unable to retrieve driver standings for the year {settings.F1_SEASON}! Retrieved driver standings for the year {settings.F1_SEASON - 1} instead.")
        
        constructor_list = constructor_standings.constructorId.to_list()
        
        last_five_constructors = constructor_list[5:]
        
        bogey_id = driver_info.loc[driver_info['driverCode'] == bogey_driver.value, ['driverId']].squeeze()
        bogey_constructor = f1.ergast.get_constructor_info(season='current', driver=bogey_id).constructorId.squeeze()

        embed_bogey = discord.Embed(title="Invalid Draft!", description="Your bogey driver must be from the last 5 constructors.", colour=settings.EMBED_COLOR)
        
        bBogeyDriverTeamInvalid = bogey_constructor not in last_five_constructors
        
        if bBogeyDriverTeamInvalid:
            await interaction.followup.send(embed=embed_bogey, ephemeral=True)
        '''

        #Check if more than 2 drivers are in the same team
        selected_drivers = [driver1.value, driver2.value, driver3.value, bogey_driver.value]
        
        driverIds = []
        selected_constructors = []
        
        for driver in selected_drivers:
            driverIds.append(driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze())
            
        for driver in driverIds:
            #TODO: Figure out a better way to get a driver's current team instead of this.
            if driver in dt.driver_current_teams.keys():
                selected_constructors.append(dt.driver_current_teams[driver])
            else:
                selected_constructors.append(f1.ergast.get_constructor_info(season='current', driver=driver).constructorId.squeeze())
            
        embed_const = discord.Embed(title="Invalid Draft!", description="You cannot pick both drivers from multiple constructors!", colour=settings.EMBED_COLOR)
        embed_team = discord.Embed(title="Invalid Draft!", description="At least one picked driver has to represent your selected constructor!", colour=settings.EMBED_COLOR)
        
        bHasDuplicateConstructor = len(set(selected_constructors)) < 3
        
        if bHasDuplicateConstructor:
            await interaction.followup.send(embed=embed_const, ephemeral=True)
        
        bNoDriverFromConstructor = team.value not in selected_constructors

        if bNoDriverFromConstructor:
            await interaction.followup.send(embed=embed_team, ephemeral=True)
        
        # Check if a driver has been counter-picked
        current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (sql.counterpick['targetuser'] == interaction.user.id)].targetdriver.array
        embed_counterpick = discord.Embed(title="Invalid Draft!", description="The following drivers have been banned by counterpick for this round!", colour=settings.EMBED_COLOR)
        bDriverCounterpicked = False
        
        for driver in current_round_counterpicks:
            if driver1.value == driver or driver2.value == driver or driver3.value == driver or bogey_driver.value == driver:
                embed_counterpick.add_field(name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                                                 f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}", value=f"Banned!", inline=False)
                bDriverCounterpicked = True
        
        if bDriverCounterpicked:
            await interaction.followup.send(embed=embed_counterpick, ephemeral=True)
    
        
        #endregion
        
        bDraftInvalid = bNoDriverFromConstructor or bPickExhausted or bHasDuplicateConstructor or bDriverCounterpicked or bHasDuplicateDriver
        
        if bDraftInvalid:
            return 
            
        
        # Operation to modify the database table has to be done before creating the embed, as the embed will error out
        # if there are no values in the table
        sql.draft_to_table(
                user_id=interaction.user.id,
                round=int(grand_prix.value),
                driver1=driver1.value,
                driver2=driver2.value,
                driver3=driver3.value,
                wildcard=bogey_driver.value,
                team=team.value
            )
        #region Team Embed
        player_table = sql.retrieve_player_table(interaction.user.id)
        driver_info = f1.get_driver_info(settings.F1_SEASON)
    
        tla_driver1 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item()
        tla_driver2 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item()
        tla_driver3 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item()
        tla_wildcard = player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item()
        short_team = player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item()
    
        em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
        em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
        em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
        em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
        em_team = dt.team_names_full[short_team]
        
        embed = discord.Embed(
            title=f"{sql.players.loc[sql.players['userid'] == interaction.user.id, 'teamname'].item()}",
            description=f"{grand_prix.name}",
            colour=settings.EMBED_COLOR)
    
        embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == interaction.user.id, 'username'].item()}")
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
        embed.add_field(name=f"{em_driver1}",
                        value="Driver 1", inline=True)
        embed.add_field(name=f"{em_driver2}",
                        value="Driver 2", inline=True)
        embed.add_field(name=f"{em_driver3}",
                        value="Driver 3", inline=True)
        embed.add_field(name=f"{em_wildcard}",
                        value="Bogey Driver", inline=True)
        embed.add_field(name=f"{em_team}",
                        value="Constructor", inline=True)
        #endregion
    
        await interaction.followup.send(f"",embed=embed, ephemeral=True)

    @app_commands.command(name='team', description='View your team.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def team(self, interaction: discord.Interaction, grand_prix: Choice[str] | None, user: discord.User = None, hidden: bool = True, show_all: bool = False):
        await interaction.response.defer(ephemeral=hidden)

        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )
        if user is None:
            user = interaction.user
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /team with parameters: grand_prix: {grand_prix.name}, user: {user.name}, hidden: {hidden}, show_all: {show_all}")

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view teams!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        if user.id != interaction.user.id:
            embed_deadline = discord.Embed(title="The draft deadline has not yet passed!", description="You cannot view other players' teams before the draft "
                                                                                                       "deadline has passed.", colour=settings.EMBED_COLOR)
            bDraftDeadlinePassed = timing.has_deadline_passed(int(grand_prix.value), sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item(), 'deadline')
        
            if not bDraftDeadlinePassed:
                await interaction.followup.send(embed=embed_deadline, ephemeral=True)
                return

        if show_all:
            team_embeds = [discord.Embed()]

            for user in sql.players.userid.to_list():
                guild = await self.bot.fetch_guild(settings.GUILD_ID)
                user = await guild.fetch_member(int(user))
                logger.info(f"Retrieving team for {user.name}...")

                player_table = sql.retrieve_player_table(user.id)
                driver_info = f1.get_driver_info(season='current')
                current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (
                            sql.counterpick['targetuser'] == user.id)].targetdriver.array

                # region Team Embed
                embed = discord.Embed(
                    title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
                    description=f"{grand_prix.name}",
                    colour=settings.EMBED_COLOR)

                if any(player_table['round'] == int(grand_prix.value)):

                    tla_driver1 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item()
                    tla_driver2 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item()
                    tla_driver3 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item()
                    tla_wildcard = player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item()
                    short_team = player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item()

                    em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
                    em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
                    em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
                    em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                                   f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
                    em_team = dt.team_names_full[short_team]

                    embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()} ")
                    embed.set_thumbnail(url=user.display_avatar.url)
                    embed.add_field(name=f"{em_driver1}",
                                    value="Driver 1", inline=True)
                    embed.add_field(name=f"{em_driver2}",
                                    value="Driver 2", inline=True)
                    embed.add_field(name=f"{em_driver3}",
                                    value="Driver 3", inline=True)
                    embed.add_field(name=f"{em_wildcard}",
                                    value="Bogey Driver", inline=True)
                    embed.add_field(name=f"{em_team}",
                                    value="Constructor", inline=True)

                    if current_round_counterpicks.size != 0:
                        embed.add_field(name=f"Counter Pick Information", value=f"For the {grand_prix.name}.",
                                        inline=False)
                        for driver in current_round_counterpicks:
                            embed.add_field(
                                name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                                     f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}",
                                value=f"Banned for this round!", inline=True)

                    # endregion
                    await interaction.followup.send(embed=embed, ephemeral=hidden)

                elif any(player_table['round'] == (int(grand_prix.value) - 1)):
                    # region Team Embed
                    embed_previous = discord.Embed(
                        title=f"There is no team set for round {grand_prix.value}",
                        description=f"Showing the previous round's team.",
                        colour=settings.EMBED_COLOR)

                    tla_driver1 = player_table.loc[
                        player_table['round'] == (int(grand_prix.value) - 1), 'driver1'].item()
                    tla_driver2 = player_table.loc[
                        player_table['round'] == (int(grand_prix.value) - 1), 'driver2'].item()
                    tla_driver3 = player_table.loc[
                        player_table['round'] == (int(grand_prix.value) - 1), 'driver3'].item()
                    tla_wildcard = player_table.loc[
                        player_table['round'] == (int(grand_prix.value) - 1), 'wildcard'].item()
                    short_team = player_table.loc[
                        player_table['round'] == (int(grand_prix.value) - 1), 'constructor'].item()

                    em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
                    em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
                    em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                                  f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
                    em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                                   f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
                    em_team = dt.team_names_full[short_team]

                    embed_previous.set_author(
                        name=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()} ")
                    embed_previous.set_thumbnail(url=user.display_avatar.url)
                    embed_previous.add_field(name=f"{em_driver1}",
                                             value="Driver 1", inline=True)
                    embed_previous.add_field(name=f"{em_driver2}",
                                             value="Driver 2", inline=True)
                    embed_previous.add_field(name=f"{em_driver3}",
                                             value="Driver 3", inline=True)
                    embed_previous.add_field(name=f"{em_wildcard}",
                                             value="Bogey Driver", inline=True)
                    embed_previous.add_field(name=f"{em_team}",
                                             value="Constructor", inline=True)

                    if current_round_counterpicks.size != 0:
                        embed.add_field(name=f"Counter Pick Information", value=f"For the {grand_prix.name}.",
                                        inline=False)
                    for driver in current_round_counterpicks:
                        embed.add_field(
                            name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                                 f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}",
                            value=f"Banned for this round!", inline=True)
                    # endregion

                    await interaction.followup.send(embed=embed_previous, ephemeral=hidden)

                else:
                    embed_fallback = discord.Embed(
                        title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
                        description=f"There is no team set for round {grand_prix.value} or the previous round.",
                        colour=settings.EMBED_COLOR
                    )
                    embed_fallback.set_author(name=str(user.name))
                    embed_fallback.set_thumbnail(url=user.display_avatar.url)

                    await interaction.followup.send(embed=embed_fallback, ephemeral=hidden)

            return

        player_table = sql.retrieve_player_table(user.id)
        driver_info = f1.get_driver_info(season='current')
        current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (sql.counterpick['targetuser'] == user.id)].targetdriver.array

        # region Team Embed
        embed = discord.Embed(
            title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
            description=f"{grand_prix.name}",
            colour=settings.EMBED_COLOR)

        if any(player_table['round'] == int(grand_prix.value)):

            tla_driver1 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item()
            tla_driver2 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item()
            tla_driver3 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item()
            tla_wildcard = player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item()
            short_team = player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item()

            em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
            em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
            em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
            em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                           f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
            em_team = dt.team_names_full[short_team]

            embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()} ")
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.add_field(name=f"{em_driver1}",
                            value="Driver 1", inline=True)
            embed.add_field(name=f"{em_driver2}",
                            value="Driver 2", inline=True)
            embed.add_field(name=f"{em_driver3}",
                            value="Driver 3", inline=True)
            embed.add_field(name=f"{em_wildcard}",
                            value="Bogey Driver", inline=True)
            embed.add_field(name=f"{em_team}",
                            value="Constructor", inline=True)
            
            if current_round_counterpicks.size != 0:
                embed.add_field(name=f"Counter Pick Information", value=f"For the {grand_prix.name}.", inline=False)
                for driver in current_round_counterpicks:
                    embed.add_field(name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                                         f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}", value=f"Banned for this round!", inline=True)
                    
            
            # endregion

            await interaction.followup.send(f'',embed=embed, ephemeral=hidden)
        elif any(player_table['round'] == (int(grand_prix.value) - 1)):
        # region Team Embed
            embed_previous = discord.Embed(
                title=f"There is no team set for round {grand_prix.value}",
                description=f"Showing the previous round's team.",
                colour=settings.EMBED_COLOR)

            tla_driver1 = player_table.loc[player_table['round'] == (int(grand_prix.value) - 1), 'driver1'].item()
            tla_driver2 = player_table.loc[player_table['round'] == (int(grand_prix.value) - 1), 'driver2'].item()
            tla_driver3 = player_table.loc[player_table['round'] == (int(grand_prix.value) - 1), 'driver3'].item()
            tla_wildcard = player_table.loc[player_table['round'] == (int(grand_prix.value) - 1), 'wildcard'].item()
            short_team = player_table.loc[player_table['round'] == (int(grand_prix.value) - 1), 'constructor'].item()

            em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
            em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
            em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                          f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
            em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                           f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
            em_team = dt.team_names_full[short_team]

            embed_previous.set_author(
                name=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()} ")
            embed_previous.set_thumbnail(url=user.display_avatar.url)
            embed_previous.add_field(name=f"{em_driver1}",
                            value="Driver 1", inline=True)
            embed_previous.add_field(name=f"{em_driver2}",
                            value="Driver 2", inline=True)
            embed_previous.add_field(name=f"{em_driver3}",
                            value="Driver 3", inline=True)
            embed_previous.add_field(name=f"{em_wildcard}",
                            value="Bogey Driver", inline=True)
            embed_previous.add_field(name=f"{em_team}",
                            value="Constructor", inline=True)

            if current_round_counterpicks.size != 0:
                embed.add_field(name=f"Counter Pick Information", value=f"For the {grand_prix.name}.", inline=False)
            for driver in current_round_counterpicks:
                embed.add_field(name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                                     f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}", value=f"Banned for this round!", inline=True)
            # endregion

            await interaction.followup.send(f'', embed=embed_previous, ephemeral=True)
        else:
            embed_fallback = discord.Embed(
                title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
                description=f"There is no team set for round {grand_prix.value} or the previous round.",
                colour=settings.EMBED_COLOR
            )
            embed_fallback.set_author(name=str(user.name))
            embed_fallback.set_thumbnail(url=user.display_avatar.url)

            await interaction.followup.send(f'', embed=embed_fallback, ephemeral=hidden)


    @app_commands.command(name='exhausted', description='View your team exhaustions.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def exhausted(self, interaction: discord.Interaction, user: discord.User = None):
        await interaction.response.defer(ephemeral=True)

        if user is None:
            user = interaction.user
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /exhausted with parameters: user: {user.name}")

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view exhaustions!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        player_table = sql.retrieve_player_table(user.id)
        
        last_team = player_table[player_table['round'] == settings.F1_ROUND - 1].squeeze()
        second_last_team = player_table[player_table['round'] == settings.F1_ROUND - 2].squeeze()

        if last_team.empty or second_last_team.empty:
            embed_no = discord.Embed(title=f"There are no exhaustions for {user.name}", colour=settings.EMBED_COLOR)
            await interaction.followup.send(embed=embed_no, ephemeral=True)
            return

        common = pd.Series(list(set(last_team).intersection(set(second_last_team))))
        
        embed = discord.Embed(title=f"Exhausted Drivers for {user.name}", colour=settings.EMBED_COLOR)
        driver_info = f1.get_driver_info(season='current')
        constructor_info = f1.ergast.get_constructor_info(season='current')
        
        for element in common:
            if element in driver_info.driverCode.to_list():
                embed.add_field(name=f"{driver_info.loc[driver_info['driverCode'] == element, 'givenName'].item()} "
                                     f"{driver_info.loc[driver_info['driverCode'] == element, 'familyName'].item()}",
                                value=f"Exhausted", inline=False)
            elif element in constructor_info.constructorId.to_list():
                embed.add_field(name=f"{dt.team_names_full[element]}",
                                value=f"Exhausted", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name='check-deadline', description='Check deadlines for a given round.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def check_deadline(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /check-deadline with parameters: grand_prix: {grand_prix.name}")
        draft_timestamp = sql.timings.loc[sql.timings['round'] == int(grand_prix.value), 'deadline'].item()
        counterpick_timestamp = sql.timings.loc[sql.timings['round'] == int(grand_prix.value), 'counterpick_deadline'].item()

        draft: pd.Timestamp = draft_timestamp.tz_localize('UTC')
        counterpick: pd.Timestamp = counterpick_timestamp.tz_localize('UTC')

        embed = discord.Embed(title=f"Deadlines for the {grand_prix.name}", colour=settings.EMBED_COLOR)
        embed.add_field(name=f"Draft Deadline", value=f"{draft.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}")
        embed.add_field(name=f"Counter-Pick Deadline", value=f"{counterpick.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='counter-pick', description=f"Choose a driver to ban from a player's team for a specific round.")
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list(),
                          driver=dt.drivers_choice_list())
    async def counter_pick(self, interaction: discord.Interaction, user: discord.User, driver: Choice[str], grand_prix: Choice[str] | None):
        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to counter-pick!",
                colour=settings.EMBED_COLOR
            )

            await interaction.response.send_message(embed=unregistered_embed, ephemeral=True)
            return


        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /counter-pick with parameters: user: {user.name}, driver: {driver.name}, grand_prix: {grand_prix.name}")

        # Deadline check
        bHasCounterpickDeadlinePassed = timing.has_deadline_passed(int(grand_prix.value), sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item(), 'counterpick_deadline')
        
        embed_deadline = discord.Embed(title="The counter-pick deadline has passed!", description="You can no longer use or modify your counter-pick for this race.", colour=settings.EMBED_COLOR)
        if bHasCounterpickDeadlinePassed:
            await interaction.response.send_message(embed=embed_deadline, ephemeral=True)
            return

        # Register new counterpick for a given round
        if interaction.user.id not in sql.counterpick[sql.counterpick['round'] == int(grand_prix.value)].pickinguser.to_list():
            # If user's id exists in the counterpick table more times than the counterpick limit, interrupt counter-picking
            number_of_counterpicks = len(sql.counterpick[sql.counterpick['pickinguser'] == interaction.user.id].pickinguser.array)
            if number_of_counterpicks >= settings.COUNTERPICK_LIMIT:
                counter_pick_limit_embed = discord.Embed(
                    title=f"No Counter Picks Left!",
                    description=f"You have exhausted all of your counter picks! Try revoking counter picks by using the grand-prix option on the /revoke-counter-pick command!",
                    colour=settings.EMBED_COLOR
                )
                await interaction.response.send_message(embed=counter_pick_limit_embed, ephemeral=True)
                return

            # If a driver has already been counter picked for a given player, interrupt counter-picking
            if driver.value in sql.counterpick[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['targetuser'] == user.id)].targetdriver.array:
                driver_counterpick_embed = discord.Embed(
                    title=f"Counter Pick Invalid!",
                    description=f"**{driver.name}** is already counter-picked against **{user.name}** for the **{grand_prix.name}**! Try counter-picking another driver!",
                    colour=settings.EMBED_COLOR
                )
                await interaction.response.send_message(embed=driver_counterpick_embed, ephemeral=True)
                return
            
            # If a target user exists in the given round in the counterpick table more times than the driver ban limit, interrupt counter-picking
            counterpick_target_drivers = len(sql.counterpick[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['targetuser'] == user.id)].targetuser)
            if counterpick_target_drivers >= settings.DRIVER_BAN_LIMIT:
                counterpick_drivers_embed = discord.Embed(
                    title=f"Counter Pick Invalid!",
                    description=f"**{user.name}** is not available to counter-pick against for the **{grand_prix.name}**! Try counter-picking another player!",
                    colour=settings.EMBED_COLOR
                )
                await interaction.response.send_message(embed=counterpick_drivers_embed, ephemeral=True)
                return
            
            # Create new counter-pick entry
            counterpick_record = pd.Series(
                {
                    'round': int(grand_prix.value),
                    'pickinguser': interaction.user.id,
                    'targetuser': user.id,
                    'targetdriver': driver.value
                }
            )
            sql.counterpick = pd.concat([sql.counterpick, counterpick_record.to_frame().T], ignore_index=True)
            sql.write_to_fantasy_database('counterpick', sql.counterpick)
            sql.counterpick = sql.import_counterpick_table()
            counter_pick_embed = discord.Embed(
                title=f"Counter Pick Used!",
                description=f"",
                colour=settings.EMBED_COLOR
            )
            counter_pick_embed.set_author(name=f"ANNOUNCEMENT")

            counter_pick_embed.add_field(name="Round",
                                         value=f"**{grand_prix.name}**",
                                         inline=False)
            counter_pick_embed.add_field(name="Picking User",
                                         value=f"{interaction.user.name}",
                                         inline=True)
            counter_pick_embed.add_field(name="Target Driver",
                                         value=f"{driver.name}",
                                         inline=True)
            counter_pick_embed.add_field(name="Target User",
                                         value=f"{user.name}",
                                         inline=True)

            await interaction.response.send_message(embed=counter_pick_embed, ephemeral=False)
            return
        
        # If a driver has already been counter picked for a given player, interrupt counter-picking
        if driver.value in sql.counterpick[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['targetuser'] == user.id)].targetdriver.array:
            driver_counterpick_embed = discord.Embed(
                title=f"Counter Pick Invalid!",
                description=f"**{driver.name}** is already counter-picked against **{user.name}** for the **{grand_prix.name}**! Try counter-picking another driver!",
                colour=settings.EMBED_COLOR
            )
            await interaction.response.send_message(embed=driver_counterpick_embed, ephemeral=True)
            return
        
        
        # Modify previously existing counter-pick
        sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == interaction.user.id), 'targetuser'] = user.id
        sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == interaction.user.id), 'targetdriver'] = driver.value

        sql.write_to_fantasy_database('counterpick', sql.counterpick)
        sql.counterpick = sql.import_counterpick_table()
        
        counter_pick_embed = discord.Embed(
            title=f"Counter Pick Modified!",
            description=f"",
            colour=settings.EMBED_COLOR
        )
        
        counter_pick_embed.set_author(name=f"ANNOUNCEMENT")

        counter_pick_embed.add_field(name="Round",
                        value=f"**{grand_prix.name}**",
                        inline=False)
        counter_pick_embed.add_field(name="Picking User",
                        value=f"{interaction.user.name}",
                        inline=True)
        counter_pick_embed.add_field(name="Target Driver",
                        value=f"{driver.name}",
                        inline=True)
        counter_pick_embed.add_field(name="Target User",
                        value=f"{user.name}",
                        inline=True)
        
        await interaction.response.send_message(embed=counter_pick_embed, ephemeral=False)

    @app_commands.command(name='revoke-counter-pick', description=f"Revoke your counter-pick for a given round.")
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list()
                          )
    async def revoke_counter_pick(self, interaction: discord.Interaction, grand_prix: Choice[str] | None):
        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f"How can you have a counter pick to revoke if you're not registered? Do not use this command.",
                colour=settings.EMBED_COLOR
            )

            await interaction.response.send_message(embed=unregistered_embed, ephemeral=True)
            return

        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )

        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /revoke-counter-pick with parameters: grand_prix: {grand_prix.name}")
        # Deadline check
        bHasCounterpickDeadlinePassed = timing.has_deadline_passed(int(grand_prix.value), sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item(), 'counterpick_deadline')

        embed_deadline = discord.Embed(title="The counter-pick deadline has passed!", description="You can no longer revoke counter-pick for this race.", colour=settings.EMBED_COLOR)
        if bHasCounterpickDeadlinePassed:
            await interaction.response.send_message(embed=embed_deadline, ephemeral=True)
            return
        
        if int(grand_prix.value) not in sql.counterpick.loc[sql.counterpick['pickinguser'] == interaction.user.id]['round'].array:
            embed_invalid = discord.Embed(title="No Counter Pick Made!", description=f"You have not made any counter-pick for the {grand_prix.name}.", colour=settings.EMBED_COLOR)
            await interaction.response.send_message(embed=embed_invalid, ephemeral=True)
            return

        counterpick = sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == interaction.user.id)]
        
        sql.counterpick = sql.counterpick.drop(counterpick.index.values)

        sql.write_to_fantasy_database('counterpick', sql.counterpick)
        sql.counterpick = sql.import_counterpick_table()

        counter_pick_embed = discord.Embed(
            title=f"Counter Pick Revoked!",
            description=f"{interaction.user.name} has revoked their counter pick for the {grand_prix.name}!",
            colour=settings.EMBED_COLOR
        )

        counter_pick_embed.set_author(name=f"IMPORTANT")

        await interaction.response.send_message(embed=counter_pick_embed, ephemeral=False)

    @app_commands.command(name='check-counter-pick', description=f"Check your counter pick status.")
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def check_counter_pick(self, interaction: discord.Interaction):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /check-counter-pick")
        await interaction.response.defer(ephemeral=True)
        
        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to counter-pick!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        embed = discord.Embed(title="Counter Pick Status",
                             colour=settings.EMBED_COLOR)

        embed.add_field(name=f"{settings.COUNTERPICK_LIMIT - len(sql.counterpick[sql.counterpick['pickinguser'] == interaction.user.id].pickinguser.array)}",
                        value="Counter Picks Available",
                        inline=False)
        embed.add_field(name="Active Counter Picks",
                        value="-----------------------------------",
                        inline=False)
        
        player_counter_picks: pd.DataFrame = sql.counterpick[sql.counterpick['pickinguser'] == interaction.user.id]
        driver_info = f1.get_driver_info(season='current')
        
        for pick in player_counter_picks.itertuples(index=False):
            embed.add_field(name=f"{f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == pick.round, "EventName"].item()}",
                            value="",
                            inline=False)
            
            user: discord.User = await self.bot.fetch_user(pick.targetuser)
            
            embed.add_field(name="Target Player",
                            value=f"{user.name}",
                            inline=True)
            embed.add_field(name="Target Driver",
                            value=f"{driver_info.loc[driver_info['driverCode'] == pick.targetdriver, "givenName"].item()} {driver_info.loc[driver_info['driverCode'] == pick.targetdriver, "familyName"].item()}",
                            inline=True)

            deadline_timestamp = sql.timings.loc[sql.timings['round'] == pick.round, 'counterpick_deadline'].item()

            deadline: pd.Timestamp = deadline_timestamp.tz_localize('UTC')
            
            embed.add_field(name="Deadline",
                            value=f"{deadline.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}",
                            inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    #endregion

    #region Player information
    @app_commands.command(name='player-profile', description="View a player's profile.")
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def player_profile(self, interaction: discord.Interaction, user: discord.User):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /player-profile with parameters: user")
        if user == interaction.user and interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view your profile!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        # region Player Profile embed
        embed = discord.Embed(title=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()} ",
                              description=f"{sql.players.loc[sql.players['userid'] == user.id, 'teammotto'].item()}",
                              colour=settings.EMBED_COLOR)

        embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}")

        user_points = sql.players.loc[sql.players['userid'] == user.id, 'points']
        if user_points.dropna().empty:
            embed.add_field(name=f"0",
                            value=f"Season Points",
                            inline=True)
        else:
            embed.add_field(name=f"{user_points.item()}",
                            value=f"Season Points",
                            inline=True)

        user_row = sql.results.loc[sql.results['userid'] == user.id].drop(labels=['userid','username', 'teamname','round1breakdown', 'round2breakdown', 'round3breakdown',
                                                         'round4breakdown', 'round5breakdown', 'round6breakdown',
                                                         'round7breakdown', 'round8breakdown', 'round9breakdown',
                                                         'round10breakdown', 'round11breakdown', 'round12breakdown',
                                                         'round13breakdown', 'round14breakdown', 'round15breakdown',
                                                         'round16breakdown', 'round17breakdown', 'round18breakdown',
                                                         'round19breakdown', 'round20breakdown', 'round21breakdown',
                                                         'round22breakdown', 'round23breakdown', 'round24breakdown', 'total'], axis=1).squeeze()
        if user_row.empty:
            embed.add_field(name=f"0",
                            value=f"Most Points Scored",
                            inline=True)
        else:
            embed.add_field(name=f"{user_row.max()}",
                            value=f"Most Points Scored in a Round",
                            inline=True)
        embed.set_image(url=user.display_avatar.url)
        # endregion

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='leaderboard', description='View the leaderboard.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /leaderboard")
        await interaction.response.send_message(f'leaderboard command triggered', ephemeral=True)

    @app_commands.command(name='points-breakdown', description='View points breakdown for given grand prix.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def points_breakdown(self, interaction: discord.Interaction, grand_prix: Choice[str], user: discord.User = None):
        await interaction.response.defer(ephemeral=True)

        event_schedule = f1.event_schedule

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f"You don't even have any points, what do you want to see a points breakdown for?"
                            f"What would that even look like?",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        if user == None:
            user = interaction.user

        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /points-breakdown with parameters: grand_prix: {grand_prix.name}, user: {user.name}")
        embed_points = discord.Embed(
            title=f"Points Breakdown for the {grand_prix.name}",
            colour=settings.EMBED_COLOR
        )


        embed_points.set_author(name=f"{user.name}")

        embed_points.add_field(name=f"{sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}'].item()} points", value=f"Total Points")
        breakdown_json = sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}breakdown'].item()

        if breakdown_json is None:
            embed_no_points = discord.Embed(
                title=f"No breakdown for the {grand_prix.name}",
                description=f"Points have not been updated for the {grand_prix.name} yet. Come back afterwards!",
                colour=settings.EMBED_COLOR
            )
            await interaction.followup.send(embed=embed_no_points, ephemeral=True)
            return

        breakdown = json.loads(breakdown_json)
        driver_info = f1.get_driver_info(season='current')
        player_table = sql.retrieve_player_table(user.id)

        tla_driver1 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item()
        tla_driver2 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item()
        tla_driver3 = player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item()
        tla_wildcard = player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item()
        short_team = player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item()

        em_driver1 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver1, 'familyName'].item()}")
        em_driver2 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver2, 'familyName'].item()}")
        em_driver3 = (f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'givenName'].item()} "
                      f"{driver_info.loc[driver_info['driverCode'] == tla_driver3, 'familyName'].item()}")
        em_wildcard = (f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'givenName'].item()} "
                       f"{driver_info.loc[driver_info['driverCode'] == tla_wildcard, 'familyName'].item()}")
        em_team = dt.team_names_full[short_team]


        embed_points.add_field(name=f"Race", value="", inline=False)
        embed_points.add_field(value=f"{breakdown['driver1']} points", name=f"{em_driver1}", inline=True)
        embed_points.add_field(value=f"{breakdown['driver2']} points", name=f"{em_driver2}", inline=True)
        embed_points.add_field(value=f"{breakdown['driver3']} points", name=f"{em_driver3}", inline=True)
        embed_points.add_field(value=f"{breakdown['bogey_driver']} points", name=f"{em_wildcard}", inline=True)
        embed_points.add_field(value=f"{breakdown['team']} points", name=f"{em_team}", inline=True)
                
        embed_points.add_field(name="Qualifying", value="", inline=False)
        embed_points.add_field(value=f"{breakdown['driver1quali']} points", name=f"{em_driver1}", inline=True)
        embed_points.add_field(value=f"{breakdown['driver2quali']} points", name=f"{em_driver2}", inline=True)
        embed_points.add_field(value=f"{breakdown['driver3quali']} points", name=f"{em_driver3}", inline=True)
        
        if event_schedule.loc[event_schedule['RoundNumber'] == int(grand_prix.value), "EventFormat"].item() == 'sprint_qualifying':
            embed_points.add_field(name="Sprint Race", value="", inline=False)
            embed_points.add_field(value=f"{breakdown['driver1sprint']} points", name=f"{em_driver1}", inline=True)
            embed_points.add_field(value=f"{breakdown['driver2sprint']} points", name=f"{em_driver2}", inline=True)
            embed_points.add_field(value=f"{breakdown['driver3sprint']} points", name=f"{em_driver3}", inline=True)
            embed_points.add_field(value=f"{breakdown['bogey_driver_sprint']} points", name=f"{em_wildcard}", inline=True)

            embed_points.add_field(name="Sprint Qualifying", value="", inline=False)
            embed_points.add_field(value=f"{breakdown['driver1sprintquali']} points", name=f"{em_driver1}", inline=True)
            embed_points.add_field(value=f"{breakdown['driver2sprintquali']} points", name=f"{em_driver2}", inline=True)
            embed_points.add_field(value=f"{breakdown['driver3sprintquali']} points", name=f"{em_driver3}", inline=True)
            
        await interaction.followup.send(embed=embed_points, ephemeral=True)

    #TODO: Improve the points-table render. Use imgkit, wkhtmltopdf and jinja to convert dataframe to html, then html to image.
    @app_commands.command(name='points-table', description='View the points table.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def points_table(self, interaction: discord.Interaction, hidden: bool = True):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /points-table with parameters: hidden: {hidden}")
        results_prep = sql.results.drop(axis=1, columns=['userid',
                                                         'round1breakdown', 'round2breakdown', 'round3breakdown',
                                                         'round4breakdown', 'round5breakdown', 'round6breakdown',
                                                         'round7breakdown', 'round8breakdown', 'round9breakdown',
                                                         'round10breakdown', 'round11breakdown', 'round12breakdown',
                                                         'round13breakdown', 'round14breakdown', 'round15breakdown',
                                                         'round16breakdown', 'round17breakdown', 'round18breakdown',
                                                         'round19breakdown', 'round20breakdown', 'round21breakdown',
                                                         'round22breakdown', 'round23breakdown', 'round24breakdown'
                                                         ])

        results_prep = results_prep.sort_values(by='total', ascending=False)

        results_prep = results_prep.rename({'username': 'Player', 'teamname':'Team'}, axis='columns')

        results_prep = results_prep.rename(dt.points_table_rename_map, axis='columns')
        
        results_prep = results_prep.reset_index(drop=True)
        
        results_prep.index += 1

        previous_grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND - 1, "EventName"].item(),
                            value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND - 1, "RoundNumber"].item()
                            )    

        # Render DataFrame directly to image using df2img with readable styling
        fig = d2i.plot_dataframe(
            df=results_prep,
            title={
                "text": "Points Table",
                "font_color": "#FFFFFF",
                "font_size": 30,
                "font_family": "Formula1 Display-Wide",
                "x": 0.5,
                "pad_t": 0,
                "pad_l": 0,
                "pad_b": 0,
                "pad_r": 0,
                "xanchor": "center",
                "y": 0.13,
                "yanchor": "bottom",
                "subtitle": {
                    "text": f"after the {previous_grand_prix.name}",
                    "font_color": "#FFFFFF",
                    "font_size": 25,
                    "font_family": "Formula1 Display-Regular",
                }
            },
            tbl_header={
                "align": "center",
                "fill_color": "#212121",
                "font_color": "#FFFFFF",
                "font_size": [14, 14, 14, 11],
                "font_family": "Formula1 Display-Wide",
                "line_color": "#4a4a4a",
            },
            tbl_cells={
                "align": "center",
                "fill_color": ["#212121", "#1a1a1a"],
                "font_color": "#FFFFFF",
                "font_size": [13, 13, 13, 17],
                "font_family": "Formula1 Display-Regular",
                "height": 40,
                "line_color": "#4a4a4a",
            },
            fig_size=(1920, 700),  # Adjust to (3840, 1440) if you want a 4K-wide image
            col_width=[0.5, 2, 2.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 1],
            row_fill_color=("#1a1a1a", "#212121"),
            paper_bgcolor="rgba(0, 0, 0, 0)",
            plotly_renderer="pdf"
        )
        d2i.save_dataframe(fig=fig, filename=settings.BASE_DIR / "data" / "points_table.pdf")

        await interaction.response.send_message(file=discord.File(settings.BASE_DIR / "data" / "points_table.png"), ephemeral=hidden)

    #endregion

    @app_commands.command(name='edit-motto', description='Edit your team motto.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_motto(self, interaction: discord.Interaction, motto: str):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /edit-team-motto with parameters: motto: {motto}")
        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f"You need to have a team in order to have a team motto. Register to get a team.",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        sql.players.loc[sql.players['userid'] == interaction.user.id, 'teammotto'] = motto
        sql.write_to_fantasy_database('players', sql.players)
        sql.import_players_table()
        
        motto_embed = discord.Embed(
            title=f"Team motto changed for {sql.players.loc[sql.players['userid'] == interaction.user.id, 'teamname'].item()}"
        )
        await interaction.response.send_message(embed=motto_embed, ephemeral=True)

    @app_commands.command(name='edit-team-name', description='Edit your team name.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_name(self, interaction: discord.Interaction, team_name: str):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /edit-team-name with parameters: team_name: {team_name}")
        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f"You don't have a team. What team name?",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        sql.players.loc[sql.players['userid'] == interaction.user.id, 'teamname'] = team_name
        sql.write_to_fantasy_database('players', sql.players)
        sql.import_players_table()

        team_name_embed = discord.Embed(
            title=f"Team name changed to {sql.players.loc[sql.players['userid'] == interaction.user.id, 'teamname'].item()}",
            description=f"Owned by {sql.players.loc[sql.players['userid'] == interaction.user.id, 'username'].item()}"
        )
        await interaction.response.send_message(embed=team_name_embed, ephemeral=True)

    @app_commands.command(name='edit-timezone', description='Edit your timezone. Make sure to enter a valid pytz timezone.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_timezone(self, interaction: discord.Interaction, timezone: str):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /edit-timezone with parameters: timezone: {timezone}")
        await interaction.response.defer(ephemeral=True)

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f"Please register to set a timezone!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        all_tz = dt.all_tz
        
        previous_timezone = sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()
        current_timezone = timezone

        embed = discord.Embed(title=f"Invalid Timezone!", description=f"Please make sure to enter a valid pytz timezone! Go here https://tinyurl.com/mspkxsua to see if your timezone is valid.", colour=settings.EMBED_COLOR)
        
        if current_timezone not in all_tz:
            await interaction.followup.send(embed=embed, ephemeral=True)
            return 
        
        sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'] = current_timezone
        sql.write_to_fantasy_database('players', sql.players)
        sql.import_players_table()
        
        embed = discord.Embed(title=f"Timezone changed!", description=f"Your timezone has been changed from {previous_timezone} to {current_timezone}!", colour=settings.EMBED_COLOR)
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))

if __name__ == '__main__':
    pass
