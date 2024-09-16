import discord
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
import settings
import fastf1
from fastf1.ergast import Ergast
import pandas as pd

#region Initialize FastF1
logger = settings.create_logger('fantasy-fastf1')
fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
ergast = Ergast()
fastf1.Cache.enable_cache(f'G:\\projects\\personal\\programming\\LVS-F1-Fantasy-Discord-Bot\\data\\fastf1\\cache')
#endregion

#region FastF1 Data
def fastf1_run():

    print_var = ergast.get_driver_standings(2024).content[0]
    logger.info(drivers())

#endregion

