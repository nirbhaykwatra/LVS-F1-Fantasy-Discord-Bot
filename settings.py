import pathlib
import os
import logging
from dotenv import load_dotenv

load_dotenv()

#region Fantasy Data
F1_SEASON = 2025
F1_ROUND = 1
#endregion

#region Constants
BASE_DIR = pathlib.Path(__file__).parent
CMDS_DIR = BASE_DIR/"commands"
FASTF1_CACHE_DIR = BASE_DIR/"data"/"fastf1"/"cache"

F1_IMAGE_BASE_URL = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/"
POSTGRES_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/fantasy_{F1_SEASON}'
POSTGRES_PLAYER_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/players_{F1_SEASON}'

RACE_POINTS = [22, 18, 15, 12, 10, 8, 6, 4, 2, 1]
SPRINT_POINTS = [5, 4, 3, 2, 1, -1, -2, -3, -4, -5]
CONSTRUCTOR_POINTS = [5, 4, 3, 2, 1]
WILDCARD_PTS_RACE = 3
WILDCARD_PTS_QUALI = 2
WILDCARD_PTS_RACE_SPRINT = 2
WILDCARD_PTS_QUALI_SPRINT = 1

GUILD_ID = int(os.getenv('GUILD_ID'))
TOKEN = os.getenv('TOKEN')
#endregion

EMBED_COLOR = 0xe8272a

# Create logging format for console handler
logFormat = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}',
                         datefmt='%Y-%m-%d %H:%M:%S',
                         style='{')

#TODO: Output logs to logs directory
def create_logger(name: str) -> logging.Logger:
    # Create logger object
    logger = logging.getLogger(name)

    # Set level to DEBUG for base logger object
    logger.setLevel(logging.DEBUG)

    # Create console handler object
    console = logging.StreamHandler()
    # Set level to INFO for console handler
    console.setLevel(logging.INFO)
    # Set format to logFormat for console handler
    console.setFormatter(logFormat)
    # Add console handler to logger
    logger.addHandler(console)

    return logger
