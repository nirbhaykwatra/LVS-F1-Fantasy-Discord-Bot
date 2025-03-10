import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
import json
from utilities import postgresql as sql
from utilities import fastf1util as f1
from utilities import datautils as dt

logger = settings.create_logger('fantasy-debug')

class FantasyDebug(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    debug_group = app_commands.Group(name='debug',
                                     description='A group of debug commands.',
                                     guild_ids=[settings.GUILD_ID])

    @debug_group.command(name='show-excluded-drivers', description='Show drivers excluded from driver choice list.')
    @app_commands.checks.has_role('Administrator')
    async def show_excluded_drivers(self, interaction: discord.Interaction):
        excluded_drivers = dt.exclude_drivers
        logger.info(f'Excluded drivers: {excluded_drivers}')

        embed = discord.Embed(
            title='Excluded Drivers',
            description='Drivers excluded from driver choice list.'
        )

        embed.set_author(name="Debug")

        for driver in excluded_drivers:
            if driver is not None:
                embed.add_field(
                    name=driver,
                    value=''
                )
            else:
                embed.add_field(name='There are no excluded drivers.', value="")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug_group.command(name='remove-season-events', description='Remove all season events from server calendar.')
    @app_commands.checks.has_role('Administrator')
    async def remove_season_events(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = self.bot.get_guild(settings.GUILD_ID)

        if guild is not None:

            events = guild.scheduled_events

            for event in events:
                await event.delete()

            await interaction.followup.send(f"Season events removed.", ephemeral=True)

        else:
            await interaction.followup.send(f"Could not retrieve guild! Perhaps the guild ID is incorrect?")

    @debug_group.command(name='remove-player-database', description='Remove selected user table from database.')
    @app_commands.checks.has_role('Administrator')
    async def remove_player_database(self, interaction: discord.Interaction, user: discord.User):
        sql.remove_player_table(user.id)
        await interaction.response.send_message(f"Successfully removed {user.name}'s Player Database.", ephemeral=True)

    @debug_group.command(name='set-current-round', description='Set the current round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def set_current_round(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        settings.F1_ROUND = grand_prix.value
        settings.settings['round'] = grand_prix.value
        await interaction.response.send_message(f'Current round set to round {settings.F1_ROUND}', ephemeral=True)

    @debug_group.command(name='show-current-round', description='Show the current round.')
    @app_commands.checks.has_role('Administrator')
    async def show_current_round(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Current round is round {settings.F1_ROUND}', ephemeral=True)
        
    @debug_group.command(name='increment-round', description='Increment the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def increment_round(self, interaction: discord.Interaction, number_of_rounds: int):
        initial_round = settings.F1_ROUND
        settings.F1_ROUND += number_of_rounds
        settings.settings['round'] = int(settings.settings['round']) + number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round + number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='decrement-round', description='Decrement the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def decrement_round(self, interaction: discord.Interaction, number_of_rounds: int):
        initial_round = settings.F1_ROUND
        settings.F1_ROUND -= number_of_rounds
        settings.settings['round'] = int(settings.settings['round']) - number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round - number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='check-driver-teams', description='Check if two or more drivers are in the same team.')
    @app_commands.checks.has_role('Administrator')
    async def check_driver_teams(self, interaction: discord.Interaction, driver1: str, driver2: str, driver3: str, driver4: str):
        selected_drivers = [driver1, driver2, driver3, driver4]
        driver_info = f1.get_driver_info(settings.F1_SEASON)
        logger.info(f'Driver Info: {driver_info}')
        
        await interaction.response.send_message(f"check-driver-teams command executed.", ephemeral=True)

    @debug_group.command(name='check-deadline', description='Check deadlines for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def check_deadline(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        timings = sql.retrieve_timings()
        deadline = timings.loc[timings['round'] == int(grand_prix.value), 'deadline'].to_list()
        reset = timings.loc[timings['round'] == int(grand_prix.value), 'reset'].to_list()
        counterpick = timings.loc[timings['round'] == int(grand_prix.value), 'counterpick_deadline'].to_list()
        await interaction.response.send_message(f"Draft deadline for {grand_prix.name} is {deadline[0]}\n Reset deadline is {reset[0]}\n Counter-pick deadline is {counterpick}", ephemeral=True)

    @debug_group.command(name='reset-round-points', description='Reset the points for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def reset_round_points(self, interaction: discord.Interaction, grand_prix: Choice[str], user: discord.User = None):
        if user is None:
            for player in sql.results.userid:
                sql.results.loc[sql.results.userid == player, f'round{grand_prix.value}'] = 0
                sql.results.loc[sql.results.userid == player, f'round{grand_prix.value}breakdown'] = None
        else:
            sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}'] = 0
            sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}breakdown'] = None
            
        sql.write_to_fantasy_database('results', sql.results)
        sql.results = sql.import_results_table()
        sql.update_player_points()
        sql.players = sql.import_players_table()
        
        await interaction.response.send_message(f"Reset points for {grand_prix.name}", ephemeral=True)

    @debug_group.command(name='clear-counter-pick', description='Remove counterpick for a given round and user.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def clear_counter_pick(self, interaction: discord.Interaction, user: discord.User, grand_prix: Choice[str]):
        
        counterpick = sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == user.id)]

        sql.counterpick = sql.counterpick.drop(counterpick.index.values)

        sql.write_to_fantasy_database('counterpick', sql.counterpick)
        sql.counterpick = sql.import_counterpick_table()
        
        await interaction.response.send_message(f"Removed counterpick for {user.name} at the {grand_prix.name}", ephemeral=True)

    @debug_group.command(name='points-breakdown', description='View points breakdown for given grand prix.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def points_breakdown(self, interaction: discord.Interaction, grand_prix: Choice[str], user:discord.User):
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

        embed_points = discord.Embed(
            title=f"Points Breakdown for the {grand_prix.name}",
            colour=settings.EMBED_COLOR
        )

        embed_points.set_author(name=f"Round {grand_prix.value}")

        embed_points.add_field(name=f"{sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}'].item()} points", value=f"Total Points")
        breakdown_json = sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}breakdown'].item()
        breakdown = json.loads(breakdown_json)

        embed_points.add_field(name=f"Race", value="------------------------", inline=False)
        embed_points.add_field(value=f"{breakdown['driver1']} points", name=f"Driver 1", inline=True)
        embed_points.add_field(value=f"{breakdown['driver2']} points", name=f"Driver 2", inline=True)
        embed_points.add_field(value=f"{breakdown['driver3']} points", name=f"Driver 3", inline=True)
        embed_points.add_field(value=f"{breakdown['bogey_driver']} points", name=f"Bogey Driver", inline=True)
        embed_points.add_field(value=f"{breakdown['team']} points", name=f"Constructor", inline=True)

        embed_points.add_field(name="Qualifying", value="------------------------", inline=False)
        embed_points.add_field(value=f"{breakdown['driver1quali']} points", name=f"Driver 1", inline=True)
        embed_points.add_field(value=f"{breakdown['driver2quali']} points", name=f"Driver 2", inline=True)
        embed_points.add_field(value=f"{breakdown['driver3quali']} points", name=f"Driver 3", inline=True)

        if event_schedule.loc[event_schedule['RoundNumber'] == int(grand_prix.value), "EventFormat"].item() == 'sprint_qualifying':
            embed_points.add_field(name="Sprint Race", value="------------------------", inline=False)
            embed_points.add_field(value=f"{breakdown['driver1sprint']} points", name=f"Driver 1", inline=True)
            embed_points.add_field(value=f"{breakdown['driver2sprint']} points", name=f"Driver 2", inline=True)
            embed_points.add_field(value=f"{breakdown['driver3sprint']} points", name=f"Driver 3", inline=True)
            embed_points.add_field(value=f"{breakdown['bogey_driver_sprint']} points", name=f"Bogey Driver", inline=True)

            embed_points.add_field(name="Sprint Qualifying", value="------------------------", inline=False)
            embed_points.add_field(value=f"{breakdown['driver1sprintquali']} points", name=f"Driver 1", inline=True)
            embed_points.add_field(value=f"{breakdown['driver2sprintquali']} points", name=f"Driver 2", inline=True)
            embed_points.add_field(value=f"{breakdown['driver3sprintquali']} points", name=f"Driver 3", inline=True)

        await interaction.followup.send(embed=embed_points, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyDebug(bot))
