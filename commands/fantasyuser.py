import discord
from discord import app_commands
from discord.ext import commands
import settings


class FantasyUser(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='draft', description='Draft your team!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def draft(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'draft command triggered', ephemeral=True)

    @app_commands.command(name='team', description='View your team.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def team(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'team command triggered', ephemeral=True)

    @app_commands.command(name='exhausted', description='View your team exhaustions.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def exhausted(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'exhausted command triggered', ephemeral=True)

    @app_commands.command(name='leaderboard', description='View the leaderboard.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'leaderboard command triggered', ephemeral=True)

    @app_commands.command(name='points-table', description='View the points table.')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def points_table(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'points-table command triggered', ephemeral=True)

    @app_commands.command(name='register', description='Register for the league!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    async def register(self, interaction: discord.Interaction):
        await interaction.response.send_message(f'Register command triggered', ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FantasyUser(bot))
