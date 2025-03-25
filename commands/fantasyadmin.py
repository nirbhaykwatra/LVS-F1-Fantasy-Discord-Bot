import datetime, time, json, os, sys, random, discord, pytz, settings
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands, tasks
import pandas as pd
from utilities import postgresql as sql
from utilities import drstatslib as stats
from utilities import fastf1util as f1
from utilities import datautils as dt

logger = settings.create_logger('fantasy-admin')

class FantasyAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    #     self.reminder.start()
    #
    # def cog_unload(self):
    #     self.reminder.cancel()


    admin_group = app_commands.Group(name='admin',
                                     description='A group of admin commands.',
                                     guild_ids=[settings.GUILD_ID])

    # tz = pytz.UTC
    # now = pd.Timestamp.now(tz)
    #
    # rm_12: bool = False
    # rm_6: bool = False
    # rm_3: bool = False
    # rm_1: bool = False
    # rm_m_30: bool = False
    #
    # sec_10 = now + pd.Timedelta(seconds=10)
    # sec_20 = now + pd.Timedelta(seconds=20)
    # logger.info(f"Reminder setup variables:\nnow: {now}\nsec_10: {sec_10}\nsec_20: {sec_20}")
    #
    # @tasks.loop(seconds=1)
    # async def reminder(self):
    #     tz = pytz.UTC
    #     now = pd.Timestamp.now(tz)
    #     f1_round = settings.F1_ROUND
    #
    #
    #
    #     # draft_deadline: pd.Timestamp = sql.timings.loc[sql.timings['round'] == settings.F1_ROUND, 'deadline'].item()
    #     # draft_deadline_tz: pd.Timestamp = draft_deadline.tz_localize(tz="UTC")
    #     #
    #     # dd_12 = draft_deadline_tz + pd.Timedelta(seconds=10)
    #     # dd_6 = draft_deadline_tz + pd.Timedelta(seconds=20)
    #     # dd_3 = draft_deadline_tz - pd.Timedelta(hours=3)
    #     # dd_1 = draft_deadline_tz - pd.Timedelta(hours=1)
    #     # dd_m_30 = draft_deadline_tz - pd.Timedelta(minutes=30)
    #
    #     if self.sec_10 < now and not self.rm_12:
    #         logger.info(f"12 hours reminder")
    #         self.rm_12 = True
    #
    #     if self.sec_20 < now and not self.rm_6:
    #         logger.info(f"6 hours reminder")
    #         self.rm_6 = True
    #
    #     # del now, draft_deadline, draft_deadline_tz, dd_12, dd_6, dd_3, dd_1, dd_m_30

    async def is_team_invalid(self, random_team, player_table, user, grand_prix) -> bool:
        """
        Check if a team follows the validation rules of the draft. Used when validating randomly generated
        teams in the update_player_points method.
            
        Returns bool: Whether the team is invalid.
        
        :parameter random_team: The team to be validated.
        :param player_table: The DataFrame which stores the teams of the player.
        :param user: The Discord ID of the player.
        :param grand_prix: The Grand Prix that the team is being assessed for.
        """

        driver1 = random_team['driver1']
        driver2 = random_team['driver2']
        driver3 = random_team['driver3']
        bogey_driver = random_team['bogey_driver']
        team = random_team['team']
        driver_info = f1.get_driver_info(settings.F1_SEASON)
    
        # Duplicate Check
        team_list = [driver1, driver2, driver3, bogey_driver]
    
        bHasDuplicateDriver = len(team_list) != len(set(team_list))
    
        # Exhausted Check        
        last_team = player_table[player_table['round'] == settings.F1_ROUND - 1].squeeze()
        second_last_team = player_table[player_table['round'] == settings.F1_ROUND - 2].squeeze()
    
        common = pd.Series(list(set(last_team).intersection(set(second_last_team))))
    
        exhausted = []
    
        for element in common:
            if driver1 == element or driver2 == element or driver3 == element or bogey_driver == element:
                exhausted.append(element)
    
            if team == element:
                exhausted.append(element)
    
        bPickExhausted = len(exhausted) != 0
    
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
    
        bogey_id = driver_info.loc[driver_info['driverCode'] == bogey_driver, ['driverId']].squeeze()
        bogey_constructor = f1.ergast.get_constructor_info(season='current', driver=bogey_id).constructorId.squeeze()
    
        bBogeyDriverTeamInvalid = bogey_constructor not in last_five_constructors
        '''
    
        #Check if more than 2 drivers are in the same team
        selected_drivers = [driver1, driver2, driver3, bogey_driver]
    
        driverIds = []
        selected_constructors = []
    
        for driver in selected_drivers:
            driverIds.append(driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze())
    
        for driver in driverIds:
            selected_constructors.append(f1.ergast.get_constructor_info(season='current', driver=driver).constructorId.squeeze())
    
        bHasDuplicateConstructor = len(set(selected_constructors)) < 3
    
        bNoDriverFromConstructor = team not in selected_constructors
    
        # Check if a driver has been counter-picked
        current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (sql.counterpick['targetuser'] == int(user))].targetdriver.array
        bDriverCounterpicked = False
    
        for driver in current_round_counterpicks:
            if driver1 == driver or driver2 == driver or driver3 == driver or bogey_driver == driver:
                bDriverCounterpicked = True
    
        #endregion
    
        bDraftInvalid = bNoDriverFromConstructor or bPickExhausted or bHasDuplicateConstructor or bDriverCounterpicked or bHasDuplicateDriver
    
        return bDraftInvalid

    # @tasks.loop(seconds=5)
    async def reminder(self):
        if dt.start_reminder_loop:
            # round_deadline = sql.timings.loc[sql.timings['round'] == settings.F1_ROUND, 'deadline'].item()
            # logger.info(f"Round {settings.F1_ROUND} deadline: {round_deadline}")
            #
            # round_deadline_aware_utc = round_deadline.tz_localize('UTC')
            #
            # reminder_timestamps = [
            #     round_deadline_aware_utc - pd.Timedelta(hours=12),
            #     round_deadline_aware_utc - pd.Timedelta(hours=6),
            #     round_deadline_aware_utc - pd.Timedelta(hours=3),
            #     round_deadline_aware_utc - pd.Timedelta(hours=1),
            #     round_deadline_aware_utc - pd.Timedelta(minutes=30),
            # ]
            # logger.info(f"Round {settings.F1_ROUND} reminder timestamps: {reminder_timestamps}")
            #
            # undrafted_users = []
            #
            # for index, player in enumerate(sql.players.userid):
            #     player_table = sql.retrieve_player_table(int(player))
            #     user = await self.bot.fetch_user(int(player))
            #     if int(settings.F1_ROUND) not in player_table['round'].to_list():
            #         undrafted_users.append(user)
            #
            # for deadline in reminder_timestamps:
            #     if deadline < pd.Timestamp.utcnow():
            #         for user in undrafted_users:
            #             embed = discord.Embed(title='Draft Reminder',
            #                                   description=f"You have not yet drafted your team for the "
            #                                               f"**{f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, 'EventName'].item()}**! "
            #                                               f"Please draft your team at the earliest. You can check the drafting deadline by using the "
            #                                               f"**/check-deadline** command.\n If you are unable to draft yourself, you can contact a League Administrator "
            #                                               f"and let them know your team picks, they will draft for you. If you do not draft before the drafting deadline "
            #                                               f"elapses, a team will be assigned to you at random.",
            #                                   colour=settings.EMBED_COLOR)
            #             await user.send(embed=embed)
            #             reminder_timestamps.remove(deadline)
            pass
        else:
            pass

    @admin_group.command(name='update-player-points', description='Update player points, as of the given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def update_player_points(self, interaction: discord.Interaction, grand_prix: Choice[str], quali_results: str, race_results: str, sprint_results: str = "none", sprint_quali_results: str = "none", hidden: bool = True):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin update-player-points with Parameters:grand_prix: {grand_prix.name} quali_results: {quali_results} race_results: {race_results} sprint_results: {sprint_results} sprint_quali_results: {sprint_quali_results}")

        await interaction.response.defer(ephemeral=hidden)

        results = sql.results
        driver_info = f1.get_driver_info(season='current')
        constructor_info = f1.ergast.get_constructor_info(season='current')
        
        race_results = race_results.split()
        quali_results = quali_results.split()
        sprint_results = sprint_results.split()
        sprint_quali_results = sprint_quali_results.split()
        
        undrafted_players = []
        
        # Assign random team if none exists
        for index, player in enumerate(sql.players.userid):
            player_table = sql.retrieve_player_table(int(player))
            user = await self.bot.fetch_user(int(player))
            
            if int(grand_prix.value) not in player_table['round'].to_list():
                logger.info(f"Player {user.name} does not have a team for the {grand_prix.name}. Assigning random team to {user.name}.")
                undrafted_players.insert(index, player)
                while True:
                    random_team = {
                        "driver1": random.choice(driver_info.driverCode.to_list()),
                        "driver2": random.choice(driver_info.driverCode.to_list()),
                        "driver3": random.choice(driver_info.driverCode.to_list()),
                        "bogey_driver": random.choice(driver_info.driverCode.to_list()),
                        "team": random.choice(constructor_info.constructorId.to_list()),
                    }
                    if not await self.is_team_invalid(random_team, player_table, player, grand_prix):
                        logger.info(f"Found valid team for {player}!: {random_team}")
                        sql.draft_to_table(
                            user_id=int(player),
                            round=int(grand_prix.value),
                            driver1=random_team['driver1'],
                            driver2=random_team['driver2'],
                            driver3=random_team['driver3'],
                            wildcard=random_team['bogey_driver'],
                            team=random_team['team'],)
                        break
                
        # Calculate points
        for player in sql.players.userid:
            user = await self.bot.fetch_user(player)
            logger.info(f"Calculating player points for {user.name}...")
            player_table = sql.retrieve_player_table(int(player))
            
            try:
                player_team = {
                    "driver1" : player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item(),
                    "driver2" : player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item(),
                    "driver3" : player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item(),
                    "bogey_driver" : player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item(),
                    "team" : player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item(),
                }
            except ValueError as e:
                embed_no_team = discord.Embed(title=f'No team found for {sql.players.loc[sql.players['userid'] == player, 'username'].item()}!', color=discord.Color.red())
                await interaction.followup.send(f"", embed=embed_no_team, ephemeral=True)
                return
            
            top_three_drivers = [player_team['driver1'], player_team['driver2'], player_team['driver3']]
            
            current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['targetuser'] == player)].targetdriver.array
            logger.info(f"Counterpicks for {user.name}: {current_round_counterpicks}")
            if current_round_counterpicks != 0:
                for index, driver in enumerate(top_three_drivers):
                    if driver in current_round_counterpicks:
                        top_three_drivers[top_three_drivers.index(driver)] = 'TLA'
                        
            logger.info(f"{user.name}'s team for the {grand_prix.name}: {top_three_drivers}")
            
            bogey_driver = player_team['bogey_driver']
            team = player_team['team']
            
            total_points = 0
            points_breakdown = {
                "driver1" : 0,
                "driver2" : 0,
                "driver3" : 0,
                "driver1sprint": 0,
                "driver2sprint": 0,
                "driver3sprint": 0,
                "driver1quali": 0,
                "driver2quali": 0,
                "driver3quali": 0,
                "driver1sprintquali": 0,
                "driver2sprintquali": 0,
                "driver3sprintquali": 0,
                "bogey_driver" : 0,
                "bogey_driver_sprint": 0,
                "team" : 0,
            }
            
            constructor_points = {}

            bogey_id = driver_info.loc[driver_info['driverCode'] == bogey_driver, ['driverId']].squeeze()
            bogey_constructor = f1.ergast.get_constructor_info(season='current', driver=bogey_id).constructorId.squeeze()
            constructor_drivers = f1.ergast.get_driver_info(season='current', constructor=bogey_constructor).driverCode.to_list()
            bogey_teammate = constructor_drivers[0] if constructor_drivers[0] != bogey_driver else constructor_drivers[1]
            
            # Add points for top 3 drivers and add constructor points
            
            #region Race and Quali points calculation
            for index, driver in enumerate(quali_results):
                if index <= 4:
                    if driver in top_three_drivers:
                        total_points += settings.QUALI_POINTS[index]
                        points_breakdown[f"{list(player_team.keys())[list(player_team.values()).index(driver)]}quali"] = settings.QUALI_POINTS[index]

                    driverId = driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze()
                    constructor = f1.ergast.get_constructor_info(season='current', driver=driverId).constructorId.squeeze()

                    if constructor not in constructor_points:
                        constructor_points[constructor] = settings.RACE_POINTS[index]
                    else:
                        constructor_points[constructor] += settings.RACE_POINTS[index]
            
            for index, driver in enumerate(race_results):
                if index <= 9:
                    if driver in top_three_drivers:
                        total_points += settings.RACE_POINTS[index]
                        points_breakdown[list(player_team.keys())[list(player_team.values()).index(driver)]] = settings.RACE_POINTS[index]

                    driverId = driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze()
                    constructor = f1.ergast.get_constructor_info(season='current', driver=driverId).constructorId.squeeze()
                    
                    if constructor not in constructor_points:
                        constructor_points[constructor] = settings.RACE_POINTS[index]
                    else:
                        constructor_points[constructor] += settings.RACE_POINTS[index]
            
            teammate_delta_race = race_results.index(bogey_driver) - race_results.index(bogey_teammate)
            
            if teammate_delta_race < 0:
                total_points += settings.BOGEY_POINTS[abs(teammate_delta_race)]
                points_breakdown["bogey_driver"] = settings.BOGEY_POINTS[abs(teammate_delta_race)]
            elif teammate_delta_race > 0:
                total_points += -settings.BOGEY_POINTS[abs(teammate_delta_race)]
                points_breakdown["bogey_driver"] = -settings.BOGEY_POINTS[abs(teammate_delta_race)]
            #endregion
                    
            # Output list of constructors sorted by total points
            constructor_points_sorted = sorted(constructor_points.items(), key=lambda item: item[1], reverse=True)
            constructor_points_sorted_dict = dict(constructor_points_sorted)
            constructor_points_sorted_list = list(constructor_points_sorted_dict.keys())
            
            # Add points if chosen constructor is in top 5 items of sorted list
            for index, constructor in enumerate(constructor_points_sorted_list):
                if index <= 4:
                    if constructor == team:
                        total_points += settings.CONSTRUCTOR_POINTS[index]
                        points_breakdown["team"] = settings.CONSTRUCTOR_POINTS[index]
                        
            # If sprint results were given, calculate sprint points
            if f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == int(grand_prix.value), "EventFormat"].item() == 'sprint_qualifying':
                logger.info(f"It's a sprint weekend: {f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == int(grand_prix.value), "EventFormat"].item()}")
                if sprint_results != "none":
                    for index, driver in enumerate(sprint_results):
                        if index <= 9:
                            if driver in top_three_drivers:
                                total_points += settings.SPRINT_POINTS[index]
                                points_breakdown[f"{list(player_team.keys())[list(player_team.values()).index(driver)]}sprint"] = settings.SPRINT_POINTS[index]
    
                    teammate_delta_sprint = sprint_results.index(bogey_driver) - sprint_results.index(bogey_teammate)
    
                    if teammate_delta_sprint < 0:
                        total_points += settings.BOGEY_POINTS[abs(teammate_delta_sprint)]
                        points_breakdown["bogey_driver_sprint"] = settings.BOGEY_POINTS[abs(teammate_delta_sprint)]
                    elif teammate_delta_sprint > 0:
                        total_points += -settings.BOGEY_POINTS[abs(teammate_delta_sprint)]
                        points_breakdown["bogey_driver_sprint"] = -settings.BOGEY_POINTS[abs(teammate_delta_sprint)]
                            
                if sprint_quali_results != "none":
                    for index, driver in enumerate(sprint_quali_results):
                        if index <= 2:
                            if driver in top_three_drivers:
                                total_points += settings.SPRINT_QUALI_POINTS[index]
                                points_breakdown[f"{list(player_team.keys())[list(player_team.values()).index(driver)]}sprintquali"] = settings.SPRINT_QUALI_POINTS[index]
            # Update database
            
            # Store dict as json for SQL table
            points_breakdown_json = json.dumps(points_breakdown)
            results.loc[results['userid'] == player, f'round{grand_prix.value}'] = total_points
            results.loc[results['userid'] == player, f'round{grand_prix.value}breakdown'] = [points_breakdown_json]
            sql.write_to_fantasy_database('results', results)

        sql.update_all_player_points()
        sql.results = sql.import_results_table()
        sql.players = sql.import_players_table()
            
        embed_points = discord.Embed(
            title=f'Points for the {grand_prix.name} have been updated!',
            description=f'To check your points breakdown, use /points-breakdown with the specified grand prix.',
            color=settings.EMBED_COLOR
        )
        settings.F1_ROUND += 1
        logger.info(f"Points have been calculated. F1 round has been set to {settings.F1_ROUND}.")
        await interaction.followup.send(embed=embed_points, ephemeral=True)

    @admin_group.command(name='update-driver-stats', description='Update driver statistics, as of the given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def update_driver_stats(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        logger.info(f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin update-driver-stats with parameters: grand_prix: {grand_prix.name}")
        #TODO: Add except to handle retrieval of driver standings if driver standings are not yet populated.
        # For example, if the season has not begun but the year has incremented; if the driver standings for 2025 are not available, retrieve for 2024
        try:
            for driver in f1.get_drivers_standings(settings.F1_SEASON, int(grand_prix.value))['driverCode']:
                stats.calculate_driver_stats(driver, int(grand_prix.value))

            logger.info(f'Updated driver stats for round {int(grand_prix.value)} of the {settings.F1_SEASON} season: ')
        except Exception as e:
            logger.error(f'Updating driver statistics failed with exception: {e}')
            embed = discord.Embed(title="Error updating driver statistics!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title="Driver statistics updated.", colour=settings.EMBED_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name='list-players', description='List registered players.')
    @app_commands.checks.has_role('Administrator')
    async def list_players(self, interaction: discord.Interaction):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin list-players")
        embed = discord.Embed(title="Registered Players")

        if len(sql.players.userid) == 0:
            embed = discord.Embed(title="There are no registered players.", color=settings.EMBED_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        for player in sql.players['username']:
            embed.add_field(name=f"{player}", value="", inline=False)

        await interaction.response.send_message(f'', embed=embed, ephemeral=True)

    @admin_group.command(name='remove-player', description='Remove specified players from the league.')
    @app_commands.checks.has_role('Administrator')
    async def remove_player(self, interaction: discord.Interaction, player: discord.User):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin remove-player with parameters: player: {player.name}")
        sql.players = sql.players[sql.players.userid != player.id]
        sql.results = sql.results[sql.results.userid != player.id]
        sql.write_to_fantasy_database('players', sql.players)
        sql.write_to_fantasy_database('results', sql.results)
        sql.remove_player_table(player.id)
        await interaction.response.send_message(f'Removed {player.name} from the league.', ephemeral=True)

    @admin_group.command(name='modify-driver-choice', description='Modify the drivers choice pool.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(operation=[Choice(name='Exclude Driver', value="add"), Choice(name='Include Driver', value="remove")])
    async def modify_driver_choice(self, interaction: discord.Interaction, operation: Choice[str], driver_code: str ):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin modify-driver-choice with parameters: operation: {operation.name}, driver_code: {driver_code}")
        excluded_drivers = dt.exclude_drivers
        logger.info(f'Excluded drivers: {excluded_drivers}')

        if operation.value == 'add':
            if driver_code in excluded_drivers:
                await interaction.response.send_message(f"Drive {driver_code} is already excluded in drivers choice pool.")
                return
            excluded_drivers.append(driver_code)
            logger.info(f"Removed {driver_code} from drivers choice pool.")
            await interaction.response.send_message(f'Driver {driver_code} has been excluded from drivers choice pool.', ephemeral=True)

        elif operation.value == 'remove':
            if driver_code not in excluded_drivers:
                await interaction.response.send_message(f"Drive {driver_code} is already included in drivers choice pool.")
                return
            excluded_drivers.remove(driver_code)
            logger.info(f"Added {driver_code} to drivers choice pool.")
            await interaction.response.send_message(f'Driver {driver_code} has been added to the drivers choice pool.',
                                                    ephemeral=True)

        dt.exclude_drivers = excluded_drivers
        dt.write_excluded_drivers()
        logger.info(f'Excluded drivers {dt.exclude_drivers}.')

    @admin_group.command(name='draft', description='Draft team for any user or grand prix.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(driver1=dt.drivers_choice_list(),
                          driver2=dt.drivers_choice_list(),
                          driver3=dt.drivers_choice_list(),
                          bogey_driver=dt.drivers_choice_list(),
                          team=dt.constructor_choice_list(),
                          grand_prix=dt.grand_prix_choice_list())
    async def draft(self, interaction: discord.Interaction,
                    user: discord.User,
                    driver1: Choice[str],
                    driver2: Choice[str],
                    driver3: Choice[str],
                    bogey_driver: Choice[str],
                    team: Choice[str],
                    grand_prix: Choice[str]):
        await interaction.response.defer(ephemeral=True)

        if user.id not in sql.players.userid.to_list():
            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to draft!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        if grand_prix is None:
            grand_prix = Choice(
                name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                )
        else:
            grand_prix = Choice(name=f1.event_schedule.loc[
                f1.event_schedule['RoundNumber'] == int(grand_prix.value), "EventName"].item(),
                                value=f1.event_schedule.loc[
                                    f1.event_schedule['RoundNumber'] == int(grand_prix.value), "RoundNumber"].item()
                                )

        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin draft for {user.name} with parameters: {driver1}, {driver2}, {driver3}, {bogey_driver}, {team} for the {grand_prix.name}")
        driver_info = f1.get_driver_info(settings.F1_SEASON)

        # region Draft Checks

        # Duplicate Check
        team_list = [driver1, driver2, driver3, bogey_driver]

        bHasDuplicateDriver = len(team_list) != len(set(team_list))

        embed_duplicate = discord.Embed(title="Invalid Draft!",
                                        description="You have chosen one driver more than once! Please try again.",
                                        colour=settings.EMBED_COLOR)
        if bHasDuplicateDriver:
            await interaction.followup.send(embed=embed_duplicate, ephemeral=True)

        # Exhausted Check
        player_table = sql.retrieve_player_table(user.id)

        last_team = player_table[player_table['round'] == settings.F1_ROUND - 1].squeeze()
        second_last_team = player_table[player_table['round'] == settings.F1_ROUND - 2].squeeze()

        common = pd.Series(list(set(last_team).intersection(set(second_last_team))))

        driver_info = f1.get_driver_info(season='current')

        exhausted = []
        embed_exhausted = discord.Embed(title="Invalid Draft!",
                                        description="One or more of the following picks are exhausted!",
                                        colour=settings.EMBED_COLOR)

        for element in common:
            if driver1.value == element or driver2.value == element or driver3.value == element or bogey_driver.value == element:
                embed_exhausted.add_field(
                    name=f"{driver_info.loc[driver_info['driverCode'] == element, 'givenName'].item()} "
                         f"{driver_info.loc[driver_info['driverCode'] == element, 'familyName'].item()}",
                    value="Exhausted!", inline=False)
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

        # Check if more than 2 drivers are in the same team
        selected_drivers = [driver1.value, driver2.value, driver3.value, bogey_driver.value]

        driverIds = []
        selected_constructors = []

        for driver in selected_drivers:
            driverIds.append(driver_info.loc[driver_info['driverCode'] == driver, ['driverId']].squeeze())

        for driver in driverIds:
            selected_constructors.append(
                f1.ergast.get_constructor_info(season='current', driver=driver).constructorId.squeeze())

        embed_const = discord.Embed(title="Invalid Draft!",
                                    description="You cannot pick both drivers from multiple constructors!",
                                    colour=settings.EMBED_COLOR)
        embed_team = discord.Embed(title="Invalid Draft!",
                                   description="At least one picked driver has to represent your selected constructor!",
                                   colour=settings.EMBED_COLOR)

        bHasDuplicateConstructor = len(set(selected_constructors)) < 3

        if bHasDuplicateConstructor:
            await interaction.followup.send(embed=embed_const, ephemeral=True)

        bNoDriverFromConstructor = team.value not in selected_constructors

        if bNoDriverFromConstructor:
            await interaction.followup.send(embed=embed_team, ephemeral=True)

        # Check if a driver has been counter-picked
        current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (
                    sql.counterpick['targetuser'] == user.id)].targetdriver.array
        embed_counterpick = discord.Embed(title="Invalid Draft!",
                                          description="The following drivers have been banned by counterpick for this round!",
                                          colour=settings.EMBED_COLOR)
        bDriverCounterpicked = False

        for driver in current_round_counterpicks:
            if driver1.value == driver or driver2.value == driver or driver3.value == driver or bogey_driver.value == driver:
                embed_counterpick.add_field(
                    name=f"{driver_info.loc[driver_info['driverCode'] == driver, 'givenName'].item()} "
                         f"{driver_info.loc[driver_info['driverCode'] == driver, 'familyName'].item()}",
                    value=f"Banned!", inline=False)
                bDriverCounterpicked = True

        if bDriverCounterpicked:
            await interaction.followup.send(embed=embed_counterpick, ephemeral=True)

        # endregion

        bDraftInvalid = bNoDriverFromConstructor or bPickExhausted or bHasDuplicateConstructor or bDriverCounterpicked or bHasDuplicateDriver

        if bDraftInvalid:
            return

            # Operation to modify the database table has to be done before creating the embed, as the embed will error out
        # if there are no values in the table
        sql.draft_to_table(
            user_id=user.id,
            round=int(grand_prix.value),
            driver1=driver1.value,
            driver2=driver2.value,
            driver3=driver3.value,
            wildcard=bogey_driver.value,
            team=team.value
        )

        # region Team Embed
        player_table = sql.retrieve_player_table(user.id)
        # TODO: Add except to handle retrieval of driver info if driver info is not yet populated.
        #  For example, if the season has not begun but the year has incremented; if the driver info for 2025 is not available, retrieve for 2024
        driver_info = f1.get_driver_info(season="current")

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
            title=f"{sql.players.loc[sql.players['userid'] == user.id, 'teamname'].item()}",
            description=f"{grand_prix.name}",
            colour=settings.EMBED_COLOR)

        embed.set_author(name=f"{sql.players.loc[sql.players['userid'] == user.id, 'username'].item()}")
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name=f"{em_driver1}",
                        value="Driver 1", inline=True)
        embed.add_field(name=f"{em_driver2}",
                        value="Driver 2", inline=True)
        embed.add_field(name=f"{em_driver3}",
                        value="Driver 3", inline=True)
        embed.add_field(name=f"{em_wildcard}",
                        value="Wildcard", inline=True)
        embed.add_field(name=f"{em_team}",
                        value="Constructor", inline=True)
        # endregion

        await interaction.followup.send(f"", embed=embed, ephemeral=True)

    @admin_group.command(name='team', description='View your team.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def team(self, interaction: discord.Interaction, grand_prix: Choice[str], user: discord.User, hidden: bool = True):
        await interaction.response.defer(ephemeral=hidden)

        if grand_prix is None:
            grand_prix = Choice(name=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "EventName"].item(),
                                value=f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, "RoundNumber"].item()
                                )
        if user is None:
            user = interaction.user
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin team with parameters: grand_prix: {grand_prix.name}, user: {user.name}, hidden: {hidden}")

        if interaction.user.id not in sql.players.userid.to_list():

            unregistered_embed = discord.Embed(
                title=f"You are not registered!",
                description=f" Please register to view teams!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        player_table = sql.retrieve_player_table(user.id)
        driver_info = f1.get_driver_info(season='current')
        current_round_counterpicks = sql.counterpick[(sql.counterpick['round'] == grand_prix.value) & (sql.counterpick['targetuser'] == interaction.user.id)].targetdriver.array

        #TODO: Add section for showing counter picked drivers in team embed

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

    @admin_group.command(name='clear-team', description='Clear the drafted team for any player, in any round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list())
    async def clear_team(self, interaction: discord.Interaction, user: discord.User, grand_prix: Choice[str]):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin clear-team with parameters: user: {user.name}, grand_prix: {grand_prix.name}")

        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(title=f"Removed {user.name}'s team for {grand_prix.name}", colour=settings.EMBED_COLOR)
        player_table = sql.retrieve_player_table(user.id)
        player_table = player_table[player_table['round'] != int(grand_prix.value)]
        sql.write_to_player_database(str(user.id), player_table)
        sql.import_players_table()

        await interaction.followup.send(f"", embed=embed)

    @admin_group.command(name='set-draft-deadline', description='Clear the drafted team for any player, in any round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list()
    )
    async def set_draft_deadline(self, interaction: discord.Interaction, grand_prix: Choice[str], datetime_utc_naive: str, column: str):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin set-draft-deadline with parameters: grand_prix: {grand_prix.name}, datetime_utc_naive: {datetime_utc_naive}, column: {column}")
        sql.modify_timings(int(grand_prix.value), datetime_utc_naive, column)
        await interaction.response.send_message(f"New draft deadline set for {grand_prix.name}", ephemeral=True)

    @admin_group.command(name='counter-pick', description='Make a counter pick for a given user and round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list(),
        driver=dt.drivers_choice_list()
    )    
    async def counter_pick(self, interaction: discord.Interaction, picking_user: discord.User, user: discord.User, driver: Choice[str], grand_prix: Choice[str]):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin counter-pick with parameters: picking_user: {picking_user.name}, target_user: {user.name}, driver: {driver.name}, grand_prix: {grand_prix.name}")
        if picking_user.id not in sql.counterpick[sql.counterpick['round'] == int(grand_prix.value)].pickinguser.to_list():
            # If user's id exists in the counterpick table more times than the counterpick limit, interrupt counter-picking
            number_of_counterpicks = len(sql.counterpick[sql.counterpick['pickinguser'] == picking_user.id].pickinguser.array)
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
                    'pickinguser': picking_user.id,
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
                                         value=f"{picking_user.name}",
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
        sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == picking_user.id), 'targetuser'] = user.id
        sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == picking_user.id), 'targetdriver'] = driver.value

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
                                     value=f"{picking_user.user.name}",
                                     inline=True)
        counter_pick_embed.add_field(name="Target Driver",
                                     value=f"{driver.name}",
                                     inline=True)
        counter_pick_embed.add_field(name="Target User",
                                     value=f"{user.name}",
                                     inline=True)

        await interaction.response.send_message(embed=counter_pick_embed, ephemeral=False)

    @admin_group.command(name='view-counter-picks', description='View the counter-picks for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list()
    )
    async def view_counter_picks(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin view-counter-picks with parameters: grand_prix: {grand_prix.name}")
        current_round_counterpick = sql.counterpick[sql.counterpick['round'] == int(grand_prix.value)]
        rounds = current_round_counterpick['round'].array
        pickingusers = current_round_counterpick.pickinguser.array
        targetusers = current_round_counterpick.targetuser.array
        targetdrivers = current_round_counterpick.targetdriver.array
        
        embed = discord.Embed(
            title=f"**Counter Picks for the {grand_prix.name}**",
        )
        
        for index in range(0, len(rounds)):
            embed.add_field(name=f"Counter Pick {index + 1}", value="-------------------------", inline=False)
            picking_user = await self.bot.fetch_user(pickingusers[index])
            embed.add_field(name=f"Picking User", value=f"{picking_user.name}", inline=True)
            target_user = await self.bot.fetch_user(targetusers[index])
            embed.add_field(name=f"Target User", value=f"{target_user.name}", inline=True)
            embed.add_field(name=f"Target Driver", value=f"{targetdrivers[index]}", inline=True)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @admin_group.command(name='show-undrafted', description='Show players who have not yet drafted for the specified round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list()
    )
    async def show_undrafted(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        await interaction.response.defer(ephemeral=True)
        undrafted_embed = discord.Embed(
            title=f"**Undrafted Players for the {grand_prix.name}**",
            description=f"",
            colour=settings.EMBED_COLOR
        )
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin show-undrafted with parameters: grand_prix: {grand_prix.name}")
        for index, player in enumerate(sql.players.userid):
            player_table = sql.retrieve_player_table(int(player))
            user = await self.bot.fetch_user(int(player))
            if int(grand_prix.value) not in player_table['round'].to_list():
                undrafted_embed.add_field(name=f"{user.name}", value=f"has not drafted", inline=False)
                
        await interaction.followup.send(embed=undrafted_embed, ephemeral=True)

    @admin_group.command(name='restart', description='Shut down or restart the bot.')
    @app_commands.checks.has_role('Administrator')
    async def shutdown_command(self, interaction: discord.Interaction, shut_down: bool = False):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin restart with parameters: shut_down: {shut_down}")
        if not shut_down:
            await interaction.response.send_message(f"Restarting Fantasy Manager...", ephemeral=True)
            settings.exit_handler()
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            await interaction.response.send_message(f"Shutting down Fantasy Manager...", ephemeral=True)
            settings.exit_handler()
            await self.bot.close()

    @admin_group.command(name='send-dm', description='Send a direct message to a specified user.')
    @app_commands.checks.has_role('Administrator')
    async def send_reminder(self, interaction: discord.Interaction, user: discord.User, title: str, message: str):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin send-dm with parameters: user: {user.name}, title: {title}, message: {message}")
        embed = discord.Embed(title=f'{title}',
                              description=f"{message}",
                              colour=settings.EMBED_COLOR)

        logger.info(f"Sending DM reminder to {user.name}.")
        await user.send(embed=embed)
        await interaction.response.send_message(f"Sent DM to {user.name}.", ephemeral=True)

    @admin_group.command(name='send-reminder', description='Send a draft reminder to a specified user.')
    @app_commands.checks.has_role('Administrator')
    async def send_reminder(self, interaction: discord.Interaction, user: discord.User):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin send-reminder with parameters: user: {user.name}")
        embed = discord.Embed(title='Draft Reminder',
                              description=f"You have not yet drafted your team for the "
                                          f"**{f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, 'EventName'].item()}**! "
                                          f"Please draft your team at the earliest. You can check the drafting deadline by using the "
                                          f"**/check-deadline** command.\n If you are unable to draft yourself, you can contact a League Administrator "
                                          f"and let them know your team picks, they will draft for you. If you do not draft before the drafting deadline "
                                          f"elapses, a team will be assigned to you at random.", colour=settings.EMBED_COLOR)

        # for index, player in enumerate(sql.players.userid):
        #     player_table = sql.retrieve_player_table(int(player))
        #     user = await self.bot.fetch_user(int(player))
        #     if int(settings.F1_ROUND) not in player_table['round'].to_list():
        #         await user.send(embed=embed)
        logger.info(f"Sending DM reminder to {user.name}.")
        await user.send(embed=embed)
        await interaction.response.send_message(f"Sent DM reminder to {user.name}.", ephemeral=True)

    @admin_group.command(name='remind-undrafted', description='Send a draft reminder to undrafted users.')
    @app_commands.checks.has_role('Administrator')
    async def remind_undrafted(self, interaction: discord.Interaction):
        logger.info(
            f"\x1b[96mSLASH-COMMAND\x1b[0m {interaction.user.name} used /admin remind-undrafted")
        embed = discord.Embed(title='Draft Reminder',
                              description=f"You have not yet drafted your team for the "
                                          f"**{f1.event_schedule.loc[f1.event_schedule['RoundNumber'] == settings.F1_ROUND, 'EventName'].item()}**! "
                                          f"Please draft your team at the earliest. You can check the drafting deadline by using the "
                                          f"**/check-deadline** command.\n If you are unable to draft yourself, you can contact a League Administrator "
                                          f"and let them know your team picks, they will draft for you. If you do not draft before the drafting deadline "
                                          f"elapses, a team will be assigned to you at random.",
                              colour=settings.EMBED_COLOR)
        for index, player in enumerate(sql.players.userid):
            player_table = sql.retrieve_player_table(int(player))
            user = await self.bot.fetch_user(int(player))
            if int(settings.F1_ROUND) not in player_table['round'].to_list():
                await user.send(embed=embed)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyAdmin(bot))
