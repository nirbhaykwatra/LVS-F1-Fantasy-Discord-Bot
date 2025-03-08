import json
import pathlib
import os
import logging
from dotenv import load_dotenv
import atexit

logFormat = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}',
                              datefmt='%Y-%m-%d %H:%M:%S',
                              style='{')

# Create logging format for console handler
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

logger = create_logger(__name__)

load_dotenv()
logger.info(f"Environment variables loaded.")

BASE_DIR = pathlib.Path(__file__).parent
CMDS_DIR = BASE_DIR/"commands"
FASTF1_CACHE_DIR = BASE_DIR/"data"/"fastf1"/"cache"

#region Fantasy Data
with open(BASE_DIR / "settings.json", "r", encoding="utf-8") as settings_file:
    settings = json.load(settings_file)
    logger.info(f"Settings loaded from {BASE_DIR / 'settings.json'}.")

F1_SEASON = settings["season"]
F1_ROUND = settings["round"]
EMBED_COLOR = settings["embed_color"]
#endregion

#region Constants
F1_IMAGE_BASE_URL = "https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/"
POSTGRES_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/fantasy_{F1_SEASON}'
POSTGRES_PLAYER_BASE_URL = f'postgresql://{os.getenv('SQLUSER')}:{os.getenv('SQLPASS')}@{os.getenv('SQLHOST')}/players_{F1_SEASON}'
RACE_POINTS = [22, 18, 15, 12, 10, 8, 6, 4, 2, 1]

SPRINT_POINTS = [5, 4, 3, 2, 1, -1, -2, -3, -4, -5]
CONSTRUCTOR_POINTS = [5, 4, 3, 2, 1]
BOGEY_POINTS = [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, -0.5, -1, -1.5, -2, -2.5, -3, -3.5, -4, -4.5, -5]
BOGEY_POINTS_SPRINT = [5, 5, 4, 4, 3, 3, 2, 2, 1, 1, -0.5, -0.5, -1, -1, -1.5, -1.5, -2, -2, -2.5, -2.5]
GUILD_ID = int(os.getenv('GUILD_ID'))

TOKEN = os.getenv('TOKEN')
#endregion

def exit_handler():
    with open(BASE_DIR/"settings.json", "w") as out_file:
        settings_dict = {
            "season": F1_SEASON,
            "round": F1_ROUND,
            "embed_color": EMBED_COLOR,
        }
        json.dump(settings_dict, out_file)
        out_file.close()
        
    logger.info(f'Settings saved to {BASE_DIR / "settings.json"}')
        
atexit.register(exit_handler)