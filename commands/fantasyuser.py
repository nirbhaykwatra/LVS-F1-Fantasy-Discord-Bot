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
import df2img as df2
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

        try:
            if not any(sql.players.userid == interaction.user.id):

                unregistered_embed = discord.Embed(
                    title=f"You are not registered!",
                    description=f" Please register to draft!",
                    colour=settings.EMBED_COLOR
                )

                await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
                return
        except ValueError as e:

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to draft!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

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
        sql.create_player_table(interaction.user.id)
        sql.write_to_fantasy_database('players', sql.players)
        sql.write_to_fantasy_database('results', sql.results)
        sql.import_players_table()

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
                    team: Choice[str]):

        await interaction.response.defer(ephemeral=True)

        try:
            if not any(sql.players.userid == interaction.user.id):
    
                unregistered_embed = discord.Embed(
                    title=f"You are not registered!",
                    description=f" Please register to draft!",
                    colour=settings.EMBED_COLOR
                )
    
                await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
                return
        except ValueError as e:
            
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
        
        # Deadline check
        embed_deadline = discord.Embed(title="The draft deadline has passed!", description="In case of extraordinary circumstances, contact the league administrator to see if they can "
                                                                                           "draft your team for you.", colour=settings.EMBED_COLOR)
        
        bDraftDeadlinePassed = timing.draft_deadline_passed(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item())
        
        if bDraftDeadlinePassed:
            await interaction.followup.send(embed=embed_deadline, ephemeral=True)
            return 
            
        #region Draft Checks
        
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
        driver_info = f1.get_driver_info(settings.F1_SEASON)
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

        #Check if more than 2 drivers are in the same team
        selected_drivers = [driver1.value, driver2.value, driver3.value, bogey_driver.value]
        
        driverIds = []
        selected_constructors = []
        
        for driver in selected_drivers:
            driverIds.append(driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze())
            
        for driver in driverIds:
            selected_constructors.append(f1.ergast.get_constructor_info(season='current', driver=driver).constructorId.squeeze())
            
        embed_const = discord.Embed(title="Invalid Draft!", description="You cannot pick both drivers from multiple constructors!", colour=settings.EMBED_COLOR)
        embed_team = discord.Embed(title="Invalid Draft!", description="At least one picked driver has to represent your selected constructor!", colour=settings.EMBED_COLOR)
        
        bHasDuplicateConstructor = len(set(selected_constructors)) < 3
        
        if bHasDuplicateConstructor:
            await interaction.followup.send(embed=embed_const, ephemeral=True)
        
        bNoDriverFromConstructor = team.value not in selected_constructors

        if bNoDriverFromConstructor:
            await interaction.followup.send(embed=embed_team, ephemeral=True)
        
        #endregion
        
        bDraftInvalid = bBogeyDriverTeamInvalid or bNoDriverFromConstructor or bPickExhausted or bHasDuplicateConstructor
        
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
        # TODO: Add except to handle retrieval of driver info if driver info is not yet populated.
        #  For example, if the season has not begun but the year has incremented; if the driver info for 2025 is not available, retrieve for 2024
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
    async def team(self, interaction: discord.Interaction, grand_prix: Choice[str] | None, user: discord.User = None):
        
        await interaction.response.defer(ephemeral=True)

        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )

        if user is None:
            user = interaction.user

        try:
            if not any(sql.players.userid == user.id):

                unregistered_embed = discord.Embed(
                    title=f"You are not registered!",
                    description=f" Please register to view teams!",
                    colour=settings.EMBED_COLOR
                )

                await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
                return
        except ValueError as e:

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view teams!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        player_table = sql.retrieve_player_table(user.id)
        # TODO: Add except to handle retrieval of driver info if driver info is not yet populated.
        #  For example, if the season has not begun but the year has incremented; if the driver info for 2025 is not available, retrieve for 2024
        driver_info = f1.get_driver_info(settings.F1_SEASON)

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
            # endregion

            await interaction.followup.send(f'',embed=embed, ephemeral=True)

        else:
            # region Team Embed
            if any(player_table['round'] == (int(grand_prix.value) - 1)):

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
                                value="Wildcard", inline=True)
                embed_previous.add_field(name=f"{em_team}",
                                value="Constructor", inline=True)
                # endregion

                await interaction.followup.send(f'', embed=embed_previous, ephemeral=True)
            else:
                embed_fallback = discord.Embed(
                    title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
                    description=f"There is no team set for round {grand_prix.value} or the previous round."
                )
                embed_fallback.set_author(name=str(user.name))
                embed_fallback.set_thumbnail(url=user.display_avatar.url)

                await interaction.followup.send(f'', embed=embed_fallback, ephemeral=True)


    @app_commands.command(name='exhausted', description='View your team exhaustions.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def exhausted(self, interaction: discord.Interaction, user: discord.User):
        player_table = sql.retrieve_player_table(interaction.user.id)
        
        last_team = player_table[player_table['round'] == settings.F1_ROUND - 1].squeeze()
        second_last_team = player_table[player_table['round'] == settings.F1_ROUND - 2].squeeze()
        
        common = pd.Series(list(set(last_team).intersection(set(second_last_team))))
        
        embed = discord.Embed(title="Exhausted Drivers", colour=settings.EMBED_COLOR)
        
        for element in common:
            embed.add_field(name=f"{element}", value=f"Exhausted", inline=False)
        
        logger.info(f'Last team: {last_team}\n Second last team: {second_last_team}\n Common team: {common}')
        
        await interaction.followup.send(embed=embed, ephemeral=True)

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
        
        if user.id not in sql.players.userid.to_list():
            unregistered_embed = discord.Embed(
                title=f"{user.name} is not registered!",
                description=f"You cannot counter-pick a user who is not registered! ",
                colour=settings.EMBED_COLOR
            )

            await interaction.response.send_message(embed=unregistered_embed, ephemeral=True)
            return

        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )
        
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
            if driver.value in sql.counterpick[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['targetuser'] == user.id)].targetdriver:
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
        if not any(sql.players.userid == user.id):
            logger.error(f'User {user.name} with user ID {user.id} is not registered.')
            await interaction.response.send_message(f'{user.name} is not registered!', ephemeral=True)
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

        user_row = sql.results.loc[sql.results['userid'] == user.id].drop(labels=['userid','username', 'teamname'], axis=1).squeeze()
        if user_row.empty:
            embed.add_field(name=f"0",
                            value=f"Most Points Scored",
                            inline=True)
        else:
            embed.add_field(name=f"{user_row.max()}",
                            value=f"Most Points Scored",
                            inline=True)
        embed.set_image(url=user.display_avatar.url)
        # endregion

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name='leaderboard', description='View the leaderboard.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'leaderboard command triggered', ephemeral=True)

    @app_commands.command(name='points-breakdown', description='View points breakdown for given grand prix.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def points_breakdown(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        await interaction.response.defer(ephemeral=True)
        try:
            if not any(sql.players.userid == interaction.user.id):

                unregistered_embed = discord.Embed(
                    title=f"You are not registered!",
                    description=f" Please register to view points!",
                    colour=settings.EMBED_COLOR
                )

                await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
                return
        except ValueError as e:

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view points!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return
        
        embed_points = discord.Embed(
            title=f"Points Breakdown for the {grand_prix.name}",
            colour=settings.EMBED_COLOR
        )
        
        embed_points.set_author(name=f"Round {grand_prix.value}")
        
        embed_points.add_field(name=f"{sql.results.loc[sql.results['userid'] == interaction.user.id, f'round{grand_prix.value}'].item()} points", value=f"Total Points")
        
        breakdown_json = sql.results.loc[sql.results['userid'] == interaction.user.id, f'round{grand_prix.value}breakdown'].item()
        breakdown = json.loads(breakdown_json)
        
        for key, value in breakdown.items():
            embed_points.add_field(name=f"{value} points", value=f"{dt.points_breakdown_map[key]}")
            
        await interaction.followup.send(embed=embed_points, ephemeral=True)

    @app_commands.command(name='points-table', description='View the points table.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def points_table(self, interaction: discord.Interaction):
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
        results = df2.plot_dataframe(results_prep, fig_size=(2560, 600), print_index=False,
                                     title={
                                         "automargin": True,
                                         "yref": "container",
                                         "text": "LVS Formula 1 League",
                                         "font_family": "Formula1 Display",
                                         "font_size": 30,
                                         "font_color": "white",
                                         "pad_l": 1000,
                                         "pad_t": 5
                                     },
                                     tbl_header={
                                         "font_family": "Formula1 Display",
                                         "font_color": "white",
                                         "fill_color": "rgba(26, 26, 26, 1)",
                                         "font_size": 10,
                                         "font_textcase": "upper",
                                         "line_color": "rgba(26, 26, 26, 1)",
                                         "height": 10
                                     },
                                     tbl_cells={
                                         "font_family": "Formula1 Display",
                                         "font_color": "white",
                                         "fill_color": "rgba(26, 26, 26, 1)",
                                         "font_size": 12,
                                         "font_textcase": "upper",
                                         "line_color": "rgba(26, 26, 26, 1)",
                                     },
                                     paper_bgcolor="rgba(26, 26, 26, 1)"
                                     )
        df2.save_dataframe(fig=results, filename=settings.BASE_DIR/"data"/"points_table.png")
        await interaction.response.send_message(file=discord.File(f'{settings.BASE_DIR}/data/points_table.png'), ephemeral=True)
    #endregion

    @app_commands.command(name='edit-motto', description='Edit your team motto.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_motto(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Team motto changed.', ephemeral=True)

    @app_commands.command(name='edit-team-name', description='Edit your team name.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_name(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Team name changed.', ephemeral=True)

    @app_commands.command(name='edit-timezone', description='Edit your timezone. Make sure to enter a valid pytz timezone.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_timezone(self, interaction: discord.Interaction, timezone: str):
        
        await interaction.response.defer(ephemeral=True)
        
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
    logger.info(f1.ergast.get_constructor_standings(season=2024).content[0].constructorId[5:].to_list())
    pass
