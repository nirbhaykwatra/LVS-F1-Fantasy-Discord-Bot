import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
import json
import pandas as pd
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
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug show-excluded-drivers")
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
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug remove-season-events")
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
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug remove-player-database with parameters: user: {user.name}")
        sql.remove_player_table(user.id)
        await interaction.response.send_message(f"Successfully removed {user.name}'s Player Database.", ephemeral=True)

    @debug_group.command(name='set-current-round', description='Set the current round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def set_current_round(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug set-current-round with parameters: grand_prix: {grand_prix.name}")
        settings.F1_ROUND = grand_prix.value
        settings.settings['round'] = grand_prix.value
        await interaction.response.send_message(f'Current round set to round {settings.F1_ROUND}', ephemeral=True)

    @debug_group.command(name='show-current-round', description='Show the current round.')
    @app_commands.checks.has_role('Administrator')
    async def show_current_round(self, interaction: discord.Interaction):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug show-current-round")
        await interaction.response.send_message(f'Current round is round {settings.F1_ROUND}', ephemeral=True)
        
    @debug_group.command(name='increment-round', description='Increment the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def increment_round(self, interaction: discord.Interaction, number_of_rounds: int):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug increment-round with parameters: number_of_rounds: {number_of_rounds}")
        initial_round = settings.F1_ROUND
        settings.F1_ROUND += number_of_rounds
        settings.settings['round'] = int(settings.settings['round']) + number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round + number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='decrement-round', description='Decrement the current round number.')
    @app_commands.checks.has_role('Administrator')
    async def decrement_round(self, interaction: discord.Interaction, number_of_rounds: int):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug decrement-round with parameters: number_of_rounds: {number_of_rounds}")
        initial_round = settings.F1_ROUND
        settings.F1_ROUND -= number_of_rounds
        settings.settings['round'] = int(settings.settings['round']) - number_of_rounds
        await interaction.response.send_message(f"Current round set to {initial_round - number_of_rounds}.", ephemeral=True)

    @debug_group.command(name='check-deadline', description='Check deadlines for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def check_deadline(self, interaction: discord.Interaction, grand_prix: Choice[str]):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug check-deadline with parameters: grand_prix: {grand_prix.name}")
        draft_timestamp = sql.timings.loc[sql.timings['round'] == int(grand_prix.value), 'deadline'].item()
        reset_timestamp = sql.timings.loc[sql.timings['round'] == int(grand_prix.value), 'reset'].item()
        counterpick_timestamp = sql.timings.loc[sql.timings['round'] == int(grand_prix.value), 'counterpick_deadline'].item()

        draft: pd.Timestamp = draft_timestamp.tz_localize('UTC')
        reset: pd.Timestamp = reset_timestamp.tz_localize('UTC')
        counterpick: pd.Timestamp = counterpick_timestamp.tz_localize('UTC')
        
        embed = discord.Embed(title=f"Deadlines for the {grand_prix.name}", colour=settings.EMBED_COLOR)
        embed.add_field(name=f"Draft Deadline", value=f"{draft.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}")
        embed.add_field(name=f"Reset Deadline", value=f"{reset.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}")
        embed.add_field(name=f"Counter-Pick Deadline", value=f"{counterpick.astimezone(sql.players.loc[sql.players['userid'] == interaction.user.id, 'timezone'].item()).strftime('%d %B %Y at %I:%M %p')}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug_group.command(name='reset-round-points', description='Reset the points for a given round.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def reset_round_points(self, interaction: discord.Interaction, grand_prix: Choice[str], user: discord.User = None):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug reset-round-points with parameters: user: {user.name}, grand_prix: {grand_prix.name}")
        if user is None:
            for player in sql.results.userid:
                sql.results.loc[sql.results.userid == player, f'round{grand_prix.value}'] = 0
                sql.results.loc[sql.results.userid == player, f'round{grand_prix.value}breakdown'] = None
        else:
            sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}'] = 0
            sql.results.loc[sql.results['userid'] == user.id, f'round{grand_prix.value}breakdown'] = None
            
        sql.write_to_fantasy_database('results', sql.results)
        sql.results = sql.import_results_table()
        sql.update_all_player_points()
        sql.players = sql.import_players_table()
        
        await interaction.response.send_message(f"Reset points for {grand_prix.name}", ephemeral=True)

    @debug_group.command(name='clear-counter-pick', description='Remove counterpick for a given round and user.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def clear_counter_pick(self, interaction: discord.Interaction, picking_user: discord.User, grand_prix: Choice[str]):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug clear-counter-pick with parameters: picking_user: {picking_user.name}, grand_prix: {grand_prix.name}")
        counterpick = sql.counterpick.loc[(sql.counterpick['round'] == int(grand_prix.value)) & (sql.counterpick['pickinguser'] == picking_user.id)]

        sql.counterpick = sql.counterpick.drop(counterpick.index.values)

        sql.write_to_fantasy_database('counterpick', sql.counterpick)
        sql.counterpick = sql.import_counterpick_table()
        
        await interaction.response.send_message(f"Removed counterpick for {picking_user.name} at the {grand_prix.name}", ephemeral=True)

    @debug_group.command(name='points-breakdown', description='View points breakdown for given grand prix.')
    @app_commands.checks.has_role('Administrator')
    @app_commands.choices(grand_prix=dt.grand_prix_choice_list())
    async def points_breakdown(self, interaction: discord.Interaction, grand_prix: Choice[str], user:discord.User):
        logger.info(
            f"[SLASH-COMMAND] {interaction.user.name} used /debug points-breakdown with parameters: user: {user.name}, grand_prix: {grand_prix.name}")
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
