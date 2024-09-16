import pathlib
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = pathlib.Path(__file__).parent
CMDS_DIR = BASE_DIR/"commands"

GUILD_ID = int(os.getenv('GUILD_ID'))
TOKEN = os.getenv('TOKEN')
