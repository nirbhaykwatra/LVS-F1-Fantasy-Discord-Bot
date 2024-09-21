# A module for all PostgreSQL methods. Use this to retrieve and store data in a PostgreSQL database.
from typing import Literal

import sqlalchemy as sql
import pandas as pd
import settings
from utilities import fastf1util as f1
from utilities import drstatslib as stats

logger = settings.create_logger('sql')

# region Connect to database
engine = sql.create_engine(settings.POSTGRES_BASE_URL)
conn = None
try:
    conn = engine.connect()
    logger.info(
        f'Connected to {engine.url.database} database on {engine.url.username}@{engine.url.host}:{engine.url.port}')
except Exception as e:
    logger.error(f'Could not connect to PostgreSQL server! Exception: {e}')

# endregion

#region Initialize league data

def initialize_league_data():
    if conn is not None:
        #TODO:  Import database tables as pandas DataFrames during the setup_hook event on the bot.
        drivers = pd.read_sql_table('drivers', conn)
        players = pd.read_sql_table('players', conn)
        results = pd.read_sql_table('results', conn)
        teams = pd.read_sql_table('teams', conn)

        return drivers, players, results, teams

#endregion

#region Table Imports
drivers, players, results, teams = initialize_league_data()
#endregion

#region Formula 1 Data

#TODO:  Create a pandas dataframe called 'drivers' and store driver names, TLAs and statistics in it. Serialize the
#       DataFrame into the Postgres database using DataFrame.to_sql.

def update_driver_statistics():

    standings = f1.get_drivers_standings(settings.F1_SEASON)

    #region Update columns
    drivers['position'] = standings['position']
    drivers['positionText'] = standings['positionText']
    drivers['points'] = standings['points']
    drivers['wins'] = standings['wins']
    drivers['driverId'] = standings['driverId']
    drivers['driverNumber'] = standings['driverNumber']
    drivers['driverCode'] = standings['driverCode']
    drivers['driverUrl'] = standings['driverUrl']
    drivers['givenName'] = standings['givenName']
    drivers['familyName'] = standings['familyName']
    drivers['dateOfBirth'] = standings['dateOfBirth']
    drivers['driverNationality'] = standings['driverNationality']
    drivers['constructorIds'] = standings['constructorIds']
    drivers['constructorUrls'] = standings['constructorUrls']
    drivers['constructorNames'] = standings['constructorNames']
    drivers['constructorNationalities'] = standings['constructorNationalities']
    #endregion

    write_to_database('drivers', drivers, if_exists='replace')
    logger.info(f'Updated driver statistics: {drivers}')


#endregion

#region Utilities
def write_to_database(table: str, data: pd.DataFrame, if_exists: Literal["fail", "replace", "append"] = "append", index: bool = False):
    result = data.to_sql(table, conn, if_exists=if_exists, index=index)
    logger.info(f'Wrote {result.real}')
#endregion

if __name__ == '__main__':
    pass