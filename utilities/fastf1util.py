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

event_schedule = fastf1.get_event_schedule(settings.F1_SEASON, include_testing=False)

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
    logger.info(event_schedule)
