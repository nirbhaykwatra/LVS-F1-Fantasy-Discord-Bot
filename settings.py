import json
import pathlib
import os
import logging
import time

import discord
from discord.utils import stream_supports_colour
from dotenv import load_dotenv
import atexit

class _ColourFormatter(logging.Formatter):

    # ANSI codes are a bit weird to decipher if you're unfamiliar with them, so here's a refresher
    # It starts off with a format like \x1b[XXXm where XXX is a semicolon separated list of commands
    # The important ones here relate to colour.
    # 30-37 are black, red, green, yellow, blue, magenta, cyan and white in that order
    # 40-47 are the same except for the background
    # 90-97 are the same but "bright" foreground
    # 100-107 are the same as the bright ones but for the background.
    # 1 means bold, 2 means dim, 0 means reset, and 4 means underline.

    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[91m%(name)s\x1b[0m %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output

# Create logging format for console handler
def create_logger(name: str) -> logging.Logger:
    # Create logger object
    logger = logging.getLogger(name)
    
    logging.basicConfig(
        filename=pathlib.Path(__file__).parent /'logs' / 'latest.log',
        filemode='a',
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO
    )

    # Set level to DEBUG for base logger object
    logger.setLevel(logging.DEBUG)

    # Create console handler object
    console = logging.StreamHandler()
    # Set level to INFO for console handler
    console.setLevel(logging.INFO)
    # Set format to logFormat for console handler
    if isinstance(console, logging.StreamHandler):
        logFormat = _ColourFormatter()
    else:
        dt_fmt = '%Y-%m-%d %H:%M:%S'
        logFormat = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')
    console.setFormatter(logFormat)
    
    # Add console handler to logger
    logger.addHandler(console)

    return logger

logger = create_logger(__name__)

load_dotenv()
logger.info(f"Environment variables loaded.")

BASE_DIR = pathlib.Path(__file__).parent
CMDS_DIR = BASE_DIR/"commands"
FASTF1_CACHE_DIR = BASE_DIR/"data"/"fastf1"/"cache"
BROWSER_DIR = os.getenv('BROWSER_PATH')

#region Fantasy Data
with open(BASE_DIR / "settings.json", "r", encoding="utf-8") as settings_file:
    settings = json.load(settings_file)
    logger.info(f"Settings loaded from {BASE_DIR / 'settings.json'}.")

F1_SEASON = int(settings["season"])
F1_ROUND = int(settings["round"])
EMBED_COLOR = discord.Colour.from_rgb(settings["embed_color"][0], settings["embed_color"][1], settings["embed_color"][2])
#endregion

#region Constants
F1_IMAGE_BASE_URL = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/"
POSTGRES_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/fantasy_{F1_SEASON}'
POSTGRES_PLAYER_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/players_{F1_SEASON}'
POSTGRES_STATS_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/stats_{F1_SEASON}'

RACE_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
QUALI_POINTS = [5, 4, 3, 2, 1]
SPRINT_POINTS = [5, 4, 3, 2, 1, -1, -2, -3, -4, -5]
SPRINT_QUALI_POINTS = [3, 2, 1]
CONSTRUCTOR_POINTS = [5, 4, 3, 2, 1]
BOGEY_POINTS = [0, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10]
BOGEY_POINTS_SPRINT = [0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 7]
COUNTERPICK_LIMIT = 3
DRIVER_BAN_LIMIT = 2

WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
TOKEN = os.getenv('TOKEN')
DEV_TOKEN = os.getenv('DEV_TOKEN')
MODE = os.getenv('MODE')
if MODE == "PRODUCTION":
    GUILD_ID = int(os.getenv('GUILD_ID'))
elif MODE == "DEVELOPMENT":
    GUILD_ID = int(os.getenv('DEV_GUILD_ID'))
#endregion

def exit_handler():
    with open(BASE_DIR/"settings.json", "w") as out_file:
        settings_dict = {
            "season": F1_SEASON,
            "round": F1_ROUND,
            "embed_color": EMBED_COLOR.to_rgb(),
        }
        json.dump(settings_dict, out_file)
        out_file.close()   
    logger.info(f'Settings saved to {BASE_DIR / "settings.json"}')

    os.rename(BASE_DIR/"logs" / "latest.log", BASE_DIR / "logs"/ f"{time.strftime("%Y-%m-%d %H-%M-%S.log")}")
    with open(BASE_DIR/"logs" / "latest.log", "w") as out_file:
        out_file.write("")
        out_file.close()
        
atexit.register(exit_handler)
