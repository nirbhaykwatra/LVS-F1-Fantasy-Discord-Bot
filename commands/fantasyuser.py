import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
from utilities import datautils as dt
from utilities import postgresql as sql
from utilities import fastf1util as f1
import pandas as pd

logger = settings.create_logger('fantasy-user')

class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    #region Basic functions
    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(timezone=dt.timezone_choice_list())
    async def register(self, interaction: discord.Interaction,  timezone: dt.Choice[str], team_name: str, team_motto: str = "The one and only!"):

        if any(sql.players.userid == interaction.user.id):
            logger.error(f'User {interaction.user.name} with {interaction.user.id} already registered.')
            await interaction.response.send_message(f'{interaction.user.name} is already registered!', ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        #region Create new player Series
        player_record = pd.Series({'username': interaction.user.name,
                         'userid': interaction.user.id,
                         'teamname': f"{team_name}",
                         'teammotto': f"{team_motto}",
                         'timezone': timezone.value})
        #endregion

        sql.players = pd.concat([sql.players, player_record.to_frame().T], ignore_index=True)
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

        user_row = sql.results.loc[sql.results['userid'] == interaction.user.id].drop(labels=['userid','username','teamname','teammotto','timezone'],
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
        sql.write_to_database('players', sql.players)
        sql.import_players_table()

        await interaction.followup.send(f'Registered player {interaction.user.name}!', embed=embed, ephemeral=True)

    @app_commands.command(name='draft', description='Draft your team!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.choices(driver1=dt.drivers_choice_list(),
                          driver2=dt.drivers_choice_list(),
                          driver3=dt.drivers_choice_list(),
                          wildcard=dt.drivers_choice_list(),
                          team=dt.constructor_choice_list(),
                          )
    async def draft(self, interaction: discord.Interaction,
                    driver1: Choice[str],
                    driver2: Choice[str],
                    driver3: Choice[str],
                    wildcard: Choice[str],
                    team: Choice[str]):

        await interaction.response.defer(ephemeral=True)
        # TODO: Implement exhaustion, implement response if user is not registered

        if not any(sql.players.userid == interaction.user.id):

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

        sql.draft_to_table(
            user_id=interaction.user.id,
            round=int(grand_prix.value),
            driver1=driver1.value,
            driver2=driver2.value,
            driver3=driver3.value,
            wildcard=wildcard.value,
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
                        value="Wildcard", inline=True)
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
                            value="Wildcard", inline=True)
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
    async def exhausted(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'exhausted command triggered', ephemeral=True)
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

    @app_commands.command(name='points-table', description='View the points table.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def points_table(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'points-table command triggered', ephemeral=True)
    #endregion

    @app_commands.command(name='edit-motto', description='Edit your team motto.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_motto(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Team motto changed.', ephemeral=True)

    @app_commands.command(name='edit-team-name', description='Edit your team name.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def edit_team_name(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Team name changed.', ephemeral=True)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))

if __name__ == '__main__':
    # user_points = sql.players.loc[sql.players['userid'] == 12345, 'points']
    # logger.info(user_points.empty)
    pass
