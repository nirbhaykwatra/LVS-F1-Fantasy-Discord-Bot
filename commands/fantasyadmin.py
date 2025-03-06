import json
import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
from utilities import postgresql as sql
from utilities import drstatslib as stats
from utilities import fastf1util as f1
from utilities import datautils as dt

logger = settings.create_logger('fantasy-admin')

class FantasyAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    admin_group = app_commands.Group(name='admin',
                                     description='A group of admin commands.',
                                     guild_ids=[settings.GUILD_ID])

    @admin_group.command(name='update-player-points', description='Update player points, as of the given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def update_player_points(self, interaction: discord.Interaction, grand_prix: Choice[str], quali_results: str, race_results: str, sprint_results: str = "none", sprint_quali_results: str = "none"):
        
        await interaction.response.defer(ephemeral=True)
        
        results = sql.results
        driver_info = f1.get_driver_info(season='current')
        
        race_results = race_results.split()
        quali_results = quali_results.split()
        sprint_results = sprint_results.split()
        sprint_quali_results = sprint_quali_results.split()
        
        for player in sql.players.userid:
            
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
            bogey_driver = player_team['bogey_driver']
            team = player_team['team']
            
            total_points = 0
            points_breakdown = {
                "driver1" : 0,
                "driver2" : 0,
                "driver3" : 0,
                "bogey_driver" : 0,
                "team" : 0,
            }
            
            constructor_points = {}
            constructor_points_sorted = {}
            
            # Add points for top 3 drivers and add constructor points
            
            #region Conventional
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
                        
                if driver == bogey_driver:
                    total_points += settings.BOGEY_POINTS[index]
                    points_breakdown[list(player_team.keys())[list(player_team.values()).index(driver)]] = settings.BOGEY_POINTS[index]
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
            if sprint_results != "none":
                for index, driver in enumerate(sprint_results):
                    if index <= 9:
                        if driver in top_three_drivers:
                            total_points += settings.SPRINT_POINTS[index]
                            points_breakdown[list(player_team.keys())[list(player_team.values()).index(driver)]] = settings.SPRINT_POINTS[index]

                    if driver == bogey_driver:
                        total_points += settings.BOGEY_POINTS_SPRINT[index]
                        points_breakdown[list(player_team.keys())[list(player_team.values()).index(driver)]] = settings.BOGEY_POINTS_SPRINT[index]
                        
            # Update database
            
            # Store dict as json for SQL table
            points_breakdown_json = json.dumps(points_breakdown)
            results.loc[results['userid'] == player, f'round{grand_prix.value}'] = total_points
            results.loc[results['userid'] == player, f'round{grand_prix.value}breakdown'] = [points_breakdown_json]
            
            logger.info(f"Points breakdown db: {results.loc[results['userid'] == player, f'round{grand_prix.value}breakdown']}")
            
            sql.update_player_points()
            sql.write_to_fantasy_database('results', results)
            sql.results = sql.import_results_table()
            sql.players = sql.import_players_table()
            
        embed_points = discord.Embed(
            title=f'Points for the {grand_prix.name} have been updated!',
            description=f'To check your points breakdown, use /points with the specified grand prix.',
            color=settings.EMBED_COLOR
        )    
        
        await interaction.followup.send(embed=embed_points, ephemeral=True)

    @admin_group.command(name='update-driver-stats', description='Update driver statistics, as of the given round.')
    @app_commands.checks.has_role('Administrator')
    async def update_driver_stats(self, interaction: discord.Interaction, round: int):
        #TODO: Add except to handle retrieval of driver standings if driver standings are not yet populated.
        # For example, if the season has not begun but the year has incremented; if the driver standings for 2025 are not available, retrieve for 2024
        try:
            for driver in f1.get_drivers_standings(settings.F1_SEASON, round)['driverCode']:
                stats.calculate_driver_stats(driver, round)

            logger.info(f'Updated driver stats for round {round} of the {settings.F1_SEASON} season: \n {sql.drivers}')
            sql.update_driver_statistics()
            sql.drivers = sql.import_drivers_table()
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
        embed = discord.Embed(title="Registered Players")

        if len(sql.players.userid) == 0:
            embed = discord.Embed(title="There are no registered players.", color=settings.EMBED_COLOR)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        for player in sql.players['username']:
            embed.add_field(name=f"{player}", value="", inline=False)

        await interaction.response.send_message(f'', embed=embed, ephemeral=True)

    @admin_group.command(name='remove-player', description='Removed specified players from the league.')
    @app_commands.checks.has_role('Administrator')
    async def remove_player(self, interaction: discord.Interaction, player: discord.User):
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
                          wildcard=dt.drivers_choice_list(),
                          team=dt.constructor_choice_list(),
                          grand_prix=dt.grand_prix_choice_list())
    async def draft(self, interaction: discord.Interaction,
                    user: discord.User,
                    driver1: Choice[str],
                    driver2: Choice[str],
                    driver3: Choice[str],
                    wildcard: Choice[str],
                    team: Choice[str],
                    grand_prix: Choice[str]):

        await interaction.response.defer(ephemeral=True)
        # TODO: Implement exhaustion

        if not any(sql.players.userid == user.id):
            unregistered_embed = discord.Embed(
                title=f"{user.name} is not registered! ",
                description=f"Please register to draft!",
                colour=settings.EMBED_COLOR
            )

            await interaction.followup.send(embed=unregistered_embed, ephemeral=True)
            return

        sql.draft_to_table(
            user_id=user.id,
            round=int(grand_prix.value),
            driver1=driver1.value,
            driver2=driver2.value,
            driver3=driver3.value,
            wildcard=wildcard.value,
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

    @admin_group.command(name='clear-team', description='Clear the drafted team for any player, in any round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(
        grand_prix=dt.grand_prix_choice_list())
    async def clear_team(self, interaction: discord.Interaction, user: discord.User, grand_prix: Choice[str]):

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
        sql.modify_timings(int(grand_prix.value), datetime_utc_naive, column)
        await interaction.response.send_message(f"New draft deadline set for {grand_prix.name}", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyAdmin(bot))
