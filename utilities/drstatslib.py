# A library for calculating driver statistics requiring more data manipulation than usual.
# For example, calculating driver podiums, teammate battles, positions gained/lost, etc.
import settings
from utilities import fastf1util as f1
from utilities import postgresql as sql

logger = settings.create_logger('driver-stats')

#region Retroactive methods
# These methods should be used only to calculate statistics based on previous data and not on a per-race basis.

# Get the number of podium positions the driver has been in.
def get_driver_podiums(driver: str) -> int:
    podiums = 0
    rounds = len(f1.ergast.get_race_schedule(settings.F1_SEASON)['round'])
    for round in range(1, rounds):
        try:
            result = f1.ergast.get_race_results(settings.F1_SEASON, round).content[0]
        except IndexError as e:
            result = None
            logger.warning(f'Round {round} has no race results.')

        try:
            sprint_result = f1.ergast.get_sprint_results(settings.F1_SEASON, round).content[0]
        except IndexError as e:
            sprint_result = None
            logger.warning(f'Round {round} has no sprint results.')

        if result is not None:
            try:
                position = result.loc[result['driverCode'] == driver, 'position'].item()

                if position <= 3:
                    podiums += 1
            except ValueError or UnboundLocalError as e:
                pass

            try:
                logger.info(f'{driver} position in race round {round}: {position}')
            except UnboundLocalError as e:
                logger.warning(f"Could not find driver {driver} in race round {round}.")

            if sprint_result is not None:
                try:
                    sprint_position = result.loc[result['driverCode'] == driver, 'position'].item()

                    if sprint_position <= 3:
                        podiums += 1
                except ValueError or UnboundLocalError as e:
                    pass

                try:
                    logger.info(f'{driver} position in sprint round {round}: {sprint_position}')
                except UnboundLocalError as e:
                    logger.warning(f"Could not find driver {driver} in sprint round {round}.")

    return podiums

# Get either the qualifying or race teammate battle between a driver and their teammate as a ratio.
def get_driver_teammate_battle(driver: str, season: int) -> str:

    battle = "0:0"

    return battle

# Get the positions gained and lost by a driver through the season.
def get_driver_position_delta(driver: str) -> [int]:

    position_delta = [0, 0]

    return position_delta
#endregion

#region Per-Race methods

def calculate_driver_stats(driver: str, round: int):

    # Update driver podiums
    if did_driver_podium(driver, round):
        sql.drivers.loc[sql.drivers['driverCode'] == driver, 'podiums'] += 1

def did_driver_podium(driver: str, round: int) -> bool:
    try:
        result = f1.ergast.get_race_results(settings.F1_SEASON, round).content[0]
    except IndexError as e:
        result = None
        logger.warning(f'Round {round} has no race results yet. Try again later!')
        return False

    try:
        sprint_result = f1.ergast.get_sprint_results(settings.F1_SEASON, round).content[0]
    except IndexError as e:
        sprint_result = None
        logger.warning(f'Round {round} has no sprint results.')

    if result is not None:
        try:
            position = result.loc[result['driverCode'] == driver, 'position'].item()

            if position <= 3:
                return True
        except ValueError or UnboundLocalError as e:
            pass

        try:
            logger.info(f'{driver} position in round {round}: {position}')
        except UnboundLocalError as e:
            logger.warning(f"Could not find driver {driver} in round {round}.")


def calculate_teammate_battle(driver: str):
    pass

#endregion

if __name__ == "__main__":
    logger.info(f'Podiums: {get_driver_podiums("VER")}')
    # logger.info(f'Battle: {get_driver_teammate_battle("VER", settings.F1_SEASON)}')
    # logger.info(f'Position delta: {get_driver_position_delta("VER")}')
    pass
