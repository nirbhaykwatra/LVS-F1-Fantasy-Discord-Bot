# A module for housing a variety of data structures for miscellaneous use, to prevent clutter in other scripts.
import pytz
import settings
from utilities import fastf1util as f1
from discord.app_commands import Choice
from datetime import datetime, timedelta
import pandas as pd
import json
import pathlib as pt

logger = settings.create_logger('data-utils')

# Use this dictionary as a translation between Ergast team names and the full team names. This can then be used in
# Choice objects and other areas where the full team name is need.
# For example, team_names_full[ergast.get_constructor_standing.constructorId]
team_names_full = {
    "red_bull"  :   "Oracle Red Bull Racing",
    "mclaren"   :   "McLaren Formula 1 Team",
    "ferrari"   :   "Scuderia Ferrari",
    "mercedes"  :   "Mercedes-AMG PETRONAS F1 Team",
    "aston_martin"  :   "Aston Martin Aramco F1 Team",
    "rb"    :   "Visa CashApp Racing Bulls Formula 1 Team",
    "haas"  :   "MoneyGram Haas F1 Team",
    "williams"  :   "Atlassian Williams Racing",
    "alpine":   "BWT Alpine F1 Team",
    "sauber"    :   "Stake F1 Team Kick Sauber"
}

circuit_map = {
    "1": "albert_park", "2": "shanghai", "3": "suzuka", "4": "bahrain",
    "5": "jeddah", "6": "miami", "7": "imola", "8": "monaco",
    "9": "catalunya", "10": "villeneuve", "11": "red_bull_ring", "12": "silverstone",
    "13": "spa", "14": "hungaroring", "15": "zandvoort", "16": "monza",
    "17": "baku", "18": "marina_bay", "19": "americas", "20": "rodriguez",
    "21": "interlagos", "22": "vegas", "23": "losail", "24": "yas_marina"
}

img_url_map = {
    "1": "Australia", "2": "China", "3": "Japan", "4": "Bahrain",
    "5": "Saudi_Arabia", "6": "Miami", "7": "Emilia_Romagna", "8": "Monaco",
    "9": "Spain", "10": "Canada", "11": "Austria", "12": "Great_Britain",
    "13": "Belgium", "14": "Hungary", "15": "Netherlands", "16": "Italy",
    "17": "Baku", "18": "Singapore", "19": "USA", "20": "Mexico",
    "21": "Brazil", "22": "Las_Vegas", "23": "Qatar", "24": "Abu_Dhabi"
}
constructors_color_map = {
    "red_bull"  :   "0x00298f",
    "mclaren"   :   "0xcc6600",
    "ferrari"   :   "0xba001a",
    "mercedes"  :   "0x09b8a2",
    "aston_martin"  :   "0x1b7a5a",
    "rb"    :   "0x2b5a9e",
    "haas"  :   "0x3f4547",
    "williams"  :   "0x1353af",
    "alpine":   "0x0081ba",
    "sauber"    :   "0x01d800"
}

points_table_rename_map = {
    'round1': 'R1', 'round2': 'R2', 'round3': 'R3', 'round4': 'R4',
    'round5': 'R5', 'round6': 'R6', 'round7': 'R7', 'round8': 'R8',
    'round9': 'R9', 'round10': 'R10', 'round11': 'R11', 'round12': 'R12',
    'round13': 'R13', 'round14': 'R14', 'round15': 'R15', 'round16': 'R16',
    'round17': 'R17', 'round18': 'R18', 'round19': 'R19', 'round20': 'R20',
    'round21': 'R21', 'round22': 'R22', 'round23': 'R23', 'round24': 'R24'
}

weather_icon_map = {
    "01d": "☀️", "02d":"⛅️", "03d": "🌥", "04d": "☁️", "09d": "🌧", "10d": "🌦", "11d": "⛈", "13d":"❄️", "50d":"🌫️",
    "01n":"🌙", "02n":"⛅️", "03n":"🌥", "04n": "☁️", "09n": "🌧", "10n": "🌦", "11n": "⛈", "13n": "❄️", "50n": "🌫️"
}

driver_current_teams = {
    'lawson': 'rb',
    'tsunoda': 'red_bull'
}
driver_current_teammates = {
    'LAW': 'HAD',
    'TSU': 'VER'
}
td = timedelta()
all_tz = pytz.all_timezones

start_reminder_loop = False

excluded_driver_path = pt.Path(settings.BASE_DIR) / 'data' / 'drivers' / 'excluded_drivers.json'

with open(excluded_driver_path) as file:
    exclude_drivers = json.load(file)
file.close()

def write_excluded_drivers():
    with open(excluded_driver_path, "w") as out_file:
        json.dump(exclude_drivers, out_file)
    out_file.close()

def get_full_team_name(team: str):
    return team_names_full[team]

def timezone_choice_list() -> []:
    return [
        Choice(name="Pacific Standard Time", value="America/Los_Angeles"),
        Choice(name="Eastern Standard Time", value="America/New_York"),
        Choice(name="Indian Standard Time", value="Asia/Kolkata"),
        Choice(name="Atlantic Standard Time", value="America/Halifax"),
            ]

def drivers_choice_list(info: bool = False) -> []:
    drivers_list = []
    try:
        driver_info = f1.get_driver_info(season='current')
    except IndexError as e:
        driver_info = f1.get_driver_info(season=settings.F1_SEASON - 1)
        logger.warning(f"Unable to retrieve driver standings for the year {datetime.now().year}! Retrieved driver standings for the year {datetime.now().year - 1} instead.")
    family_names = driver_info.familyName
    given_names = driver_info.givenName
    driver_codes = driver_info.driverCode

    for driver in range(0, driver_info.driverNumber.count()):
        last_name = family_names.get(driver)
        first_name = given_names.get(driver)
        driver_code = driver_codes.get(driver)
        if info is False:
            if driver_code in exclude_drivers:
                continue
            drivers_list.append(Choice(name=f"{first_name} {last_name}", value=driver_code))
        else:
            drivers_list.append(Choice(name=f"{first_name} {last_name}", value=driver_code))

    return drivers_list

def constructor_choice_list() -> []:
    constructors_list = []
        
    constructors = f1.ergast.get_constructor_info(season='current').constructorId

    for team in constructors:
        constructors_list.append(Choice(name=team_names_full[team], value=team))

    return constructors_list

def grand_prix_choice_list() -> []:
    grand_prixs_list = []
    grand_prix_names: pd.DataFrame = f1.event_schedule

    for grand_prix in grand_prix_names.EventName:
        grand_prixs_list.append(Choice
            (
            name=f"{grand_prix}",
            value=str(grand_prix_names.loc[grand_prix_names['EventName'] == grand_prix, 'RoundNumber'].item())
            )
        )

    return grand_prixs_list

if __name__ == '__main__':
    logger.info(f"")
    pass