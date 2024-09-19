# A library for calculating driver statistics requiring more data manipulation than usual.
# For example, calculating driver podiums, teammate battles, positions gained/lost, etc.
import settings
from utilities import fastf1util as f1

logger = settings.create_logger('driver-stats')

# Get the number of podium positions the driver has been in.
def get_driver_podiums(driver: str) -> int:
    podiums = 0
    rounds = len(f1.ergast.get_race_schedule(settings.F1_SEASON)['round'])
    for round in range(1, rounds):
        try:
            result = f1.ergast.get_race_results(settings.F1_SEASON, round).content[0]
        except IndexError as e:
            result = None
            logger.warning(f'Round {round} has no results.')

        if result is not None:

            position = result.loc[result['driverCode'] == driver, 'position'].item()

            if position <= 3:
                podiums += 1

            logger.info(f'Results for round {round}: {position}')


    return podiums

# Get either the qualifying or race teammate battle between a driver and their teammate as a ratio.
def get_driver_teammate_battle(driver: str, season: int) -> str:

    battle = "0:0"

    return battle

# Get the positions gained and lost by a driver through the season.
def get_driver_position_delta(driver: str) -> [int]:

    position_delta = [0, 0]

    return position_delta

