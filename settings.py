import pathlib
import os
import logging
from dotenv import load_dotenv

load_dotenv()

#region Fantasy Data
F1_SEASON = 2024
F1_ROUND = 18
#endregion

#region Constants
BASE_DIR = pathlib.Path(__file__).parent
CMDS_DIR = BASE_DIR/"commands"
FASTF1_CACHE_DIR = BASE_DIR/"data"/"fastf1"/"cache"

F1_IMAGE_BASE_URL = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/"
POSTGRES_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/lvs_fantasy'

GUILD_ID = int(os.getenv('GUILD_ID'))
TOKEN = os.getenv('TOKEN')
#endregion

# Create logging format for console handler
logFormat = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}',
                         datefmt='%Y-%m-%d %H:%M:%S',
                         style='{')

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
