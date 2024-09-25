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
    #TODO: Replace round int with Grand Prix choices, Choice(name=grand_prix_full_name, value=gp_round_int)
    async def update_player_points(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        for player in sql.players.userid:
            player_table = sql.retrieve_player_table(int(player))
            try:
                results = f1.ergast.get_race_results(settings.F1_SEASON, grand_prix.value).content[0]
            except IndexError as e:
                results = None
                logger.warning(f'{grand_prix.value} has no results. Try updating points later!')
                await interaction.response.send_message(f'{grand_prix.value} has no results. Try updating points later!')
                return

            #logger.info(f"Player table: {player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1']}")

            player_team = {
                # "driver1": player_table.loc[player_table['round'] == int(grand_prix.value), 'driver1'].item(),
                # "driver2": player_table.loc[player_table['round'] == int(grand_prix.value), 'driver2'].item(),
                # "driver3": player_table.loc[player_table['round'] == int(grand_prix.value), 'driver3'].item(),
                # "wildcard": player_table.loc[player_table['round'] == int(grand_prix.value), 'wildcard'].item(),
                # "constructor": player_table.loc[player_table['round'] == int(grand_prix.value), 'constructor'].item()
            }

            results_drivers = results.driverCode
            drivers_top10 = results_drivers.head(10)

            logger.info(f'Top 10 drivers for {grand_prix.name}: {drivers_top10}')

    @admin_group.command(name='update-driver-stats', description='Update driver statistics, as of the given round.')
    @app_commands.checks.has_role('Administrator')
    async def update_driver_stats(self, interaction: discord.Interaction, round: int):
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
        sql.write_to_database('players', sql.players)
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

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyAdmin(bot))
