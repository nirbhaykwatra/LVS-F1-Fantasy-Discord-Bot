# A module for getting easily getting data from FastF1 without cluttering any other cogs.
from typing import (
    Literal,
    Optional,
    Union
)
import settings
import fastf1
import fastf1.core as core
from fastf1.ergast import Ergast
import pandas as pd

logger = settings.create_logger('fastf1utils')

#region Initialize FastF1
fastf1.ergast.interface.BASE_URL = "https://api.jolpi.ca/ergast/f1"
fastf1.Cache.enable_cache(settings.FASTF1_CACHE_DIR)
ergast = Ergast()
#endregion

event_schedule = fastf1.get_event_schedule(year=settings.F1_SEASON, include_testing=False)

#region Basic Data
def get_drivers_standings(season: Optional[Union[Literal['current'], int]] = None,
                          round: Optional[Union[Literal['last'], int]] = None,
                          driver: Optional[str] = None,
                          standings_position: Optional[int] = None,
                          result_type: Optional[Literal['pandas', 'raw']] = None,
                          auto_cast: Optional[bool] = None,
                          limit: Optional[int] = None,
                          offset: Optional[int] = None) -> pd.DataFrame:
    """Get drivers' standings as a pandas DataFrame"""
    return ergast.get_driver_standings(season, round, driver, standings_position, result_type, auto_cast, limit, offset).content[0]

def get_driver_info(season: Optional[Union[Literal['current'], int]] = None,
                    round: Optional[Union[Literal['last'], int]] = None,
                    circuit: Optional[str] = None,
                    constructor: Optional[str] = None,
                    driver: Optional[str] = None,
                    grid_position: Optional[int] = None,
                    results_position: Optional[int] = None,
                    fastest_rank: Optional[int] = None,
                    status: Optional[str] = None,
                    result_type: Optional[Literal['pandas', 'raw']] = None,
                    auto_cast: Optional[bool] = None,
                    limit: Optional[int] = None,
                    offset: Optional[int] = None) -> pd.DataFrame:
    """Get driver information as a pandas DataFrame"""
    return ergast.get_driver_info(season, round, circuit, constructor, driver, grid_position, results_position,
                    fastest_rank, status, result_type, auto_cast, limit, offset)


#endregion

#region Session Data
def get_session(year: int,
                gp: Union[str, int],
                identifier: Optional[Union[int, str]] = None,
                *,
                backend: Optional[Literal['fastf1', 'f1timing', 'ergast']] = None,
                force_ergast: bool = False,
) -> core.Session:
    return fastf1.get_session(year, gp, identifier, backend=backend, force_ergast=force_ergast )
#endregion

if __name__=="__main__":
    driver_info = get_driver_info(season='current')
    logger.info(f"Got driver info: {driver_info.any()}")
    constructor_info = ergast.get_constructor_info(season='current')
    logger.info(f"Got constructor info: {constructor_info.any()}")
    bogey_id = driver_info.loc[driver_info['driverCode'] == 'LAW', ['driverId']].squeeze()
    logger.info(f"Bogey ID: {bogey_id}")
    bogey_constructor = ergast.get_constructor_info(season='current', driver=bogey_id).constructorId.squeeze()
    logger.info(f"Bogey constructor: {bogey_constructor}")
    constructor_drivers = ergast.get_driver_info(season='current',
                                                    constructor=bogey_constructor.iat[-1]).driverCode.to_list()
    logger.info(f"Constructor drivers: {constructor_drivers}")
    bogey_teammate = constructor_drivers[0] if constructor_drivers[0] != 'LAW' else constructor_drivers[1]
    logger.info(f"Bogey teammate: {bogey_teammate}")
    pass
        
