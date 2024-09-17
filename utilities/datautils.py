# A module for housing a variety of data structures for miscellaneous use, to prevent clutter in other scripts.
from utilities import fastf1util as f1
from discord.app_commands import Choice
from datetime import datetime

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