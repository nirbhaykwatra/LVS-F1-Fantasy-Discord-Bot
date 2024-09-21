# A module for housing a variety of data structures for miscellaneous use, to prevent clutter in other scripts.
from utilities import fastf1util as f1
from discord.app_commands import Choice
from datetime import datetime

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

def get_full_team_name(team: str):
    return team_names_full[team]

def drivers_choice_list() -> []:
    drivers_list = []
    driver_standings = f1.get_drivers_standings(datetime.now().year)
    family_names = driver_standings.familyName
    given_names = driver_standings.givenName
    driver_codes = driver_standings.driverCode

    for driver in range(0, driver_standings.position.count()):
        last_name = family_names.get(driver)
        first_name = given_names.get(driver)
        driver_code = driver_codes.get(driver)
        drivers_list.append(Choice(name=f"{first_name} {last_name}", value=driver_code))

    return drivers_list

if __name__ == '__main__':
    print()