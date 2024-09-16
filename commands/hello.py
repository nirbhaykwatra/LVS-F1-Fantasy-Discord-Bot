import discord
from discord import app_commands
from discord.ext import commands
import settings

class Hello(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name='hello', description='Hello World!')
    @app_commands.guilds(discord.Object(id=settings.GUILD_ID))
    @app_commands.checks.has_role("Administrator")
    async def hello(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello!", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Hello(bot))


