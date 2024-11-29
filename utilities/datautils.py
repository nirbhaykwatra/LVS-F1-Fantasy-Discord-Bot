# A module for housing a variety of data structures for miscellaneous use, to prevent clutter in other scripts.
import settings
from utilities import fastf1util as f1
from discord.app_commands import Choice
from datetime import datetime
import pandas as pd
import json
import os

logger = settings.create_logger('data-utils')

# Use this dictionary as a translation between Ergast team names and the full team names. This can then be used in
# Choice objects and other areas where the full team name is need.
# For example, team_names_full[ergast.get_constructor_standing.constructorId]
team_names_full = {
    "Red Bull"  :   "Oracle Red Bull Racing",
    "McLaren"   :   "McLaren Formula 1 Team",
    "Ferrari"   :   "Scuderia Ferrari",
    "Mercedes"  :   "Mercedes-AMG PETRONAS F1 Team",
    "Aston Martin"  :   "Aston Martin Aramco F1 Team",
    "RB F1 Team"    :   "Visa CashApp RB Formula 1 Team",
    "Haas F1 Team"  :   "MoneyGram Haas F1 Team",
    "Williams"  :   "Williams Racing",
    "Alpine F1 Team":   "BWT Alpine F1 Team",
    "Sauber"    :   "Stake F1 Team Kick Sauber"
}

with open(f"{os.getcwd()}\\data\\drivers\\excluded_drivers.json") as file:
    exclude_drivers = json.load(file)
file.close()

def write_excluded_drivers():
    with open(f"{os.getcwd()}\\data\\drivers\\excluded_drivers.json", "w") as out_file:
        json.dump(exclude_drivers, out_file)
    file.close()

def get_full_team_name(team: str):
    return team_names_full[team]

def timezone_choice_list() -> []:
    return [
        Choice(name="Pacific Standard Time", value="America/Los_Angeles"),
        Choice(name="Eastern Standard Time", value="America/New_York"),
        Choice(name="Indian Standard Time", value="Asia/Kolkata")
            ]

def drivers_choice_list(info: bool = False) -> []:
    drivers_list = []
    driver_standings = f1.get_drivers_standings(datetime.now().year)
    family_names = driver_standings.familyName
    given_names = driver_standings.givenName
    driver_codes = driver_standings.driverCode

    for driver in range(0, driver_standings.position.count()):
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
    constructor_standings = f1.ergast.get_constructor_standings(settings.F1_SEASON).content[0]
    constructor_names = constructor_standings.constructorName

    for team in constructor_names:
        constructors_list.append(Choice(name=team_names_full[team], value=team))

    return constructors_list

def grand_prix_choice_list() -> []:
    grand_prixs_list = []
    grand_prix_names: pd.DataFrame = f1.event_schedule

    for grand_prix in grand_prix_names.EventName:
        grand_prixs_list.append(Choice
            (
            name=grand_prix,
            value=str(grand_prix_names.loc[grand_prix_names['EventName'] == grand_prix, 'RoundNumber'].item())
            )
        )

    return grand_prixs_list

if __name__ == '__main__':
    logger.info(f"{constructor_choice_list()}")
    pass