# A module for all PostgreSQL methods. Use this to retrieve and store data in a PostgreSQL database.
import traceback
from typing import Literal
import sqlalchemy as sql
import pandas as pd
import settings
from utilities import fastf1util as f1

logger = settings.create_logger('sql')

# region Connect to fantasy database
engine = sql.create_engine(settings.POSTGRES_BASE_URL)
conn = None
try:
    conn = engine.connect()
    logger.info(
        f'Connected to {engine.url.database} database on {engine.url.username}@{engine.url.host}:{engine.url.port}')
except Exception as e:
    logger.error(f'Could not connect to {engine.url.database} database! Exception: {traceback.format_exc()}')
# endregion

#region Connect to player database
player_engine = sql.create_engine(settings.POSTGRES_PLAYER_BASE_URL)
player_conn = None
try:
    player_conn = player_engine.connect()
    logger.info(
        f'Connected to {player_engine.url.database} database on {player_engine.url.username}@{player_engine.url.host}:{player_engine.url.port}')
except Exception as e:
    logger.error(f'Could not connect to {player_engine.url.database} database! Exception: {traceback.format_exc()}')
#endregion

#region Player Table methods

def create_player_table(user_id: int):
    player_db = pd.DataFrame(
        columns=['round', 'driver1', 'driver2', 'driver3', 'wildcard', 'constructor']
    )

    write_to_player_database(str(user_id), player_db, if_exists='replace')

def retrieve_player_table(user_id: int) -> pd.DataFrame:
    player_table = pd.read_sql_table(str(user_id), con=player_conn)
    return player_table

def draft_to_table(user_id: int, round: int, driver1: str, driver2: str, driver3: str, wildcard: str, team: str):

    draft_df = retrieve_player_table(user_id)

    draft_series = pd.Series({
        'round': round,
        'driver1': driver1,
        'driver2': driver2,
        'driver3': driver3,
        'wildcard': wildcard,
        'constructor': team
    })

    if any(draft_df['round'] == round):
        draft_df.loc[draft_df['round'] == round, 'driver1'] = driver1
        draft_df.loc[draft_df['round'] == round, 'driver2'] = driver2
        draft_df.loc[draft_df['round'] == round, 'driver3'] = driver3
        draft_df.loc[draft_df['round'] == round, 'wildcard'] = wildcard
        draft_df.loc[draft_df['round'] == round, 'constructor'] = team
        write_to_player_database(str(user_id), draft_df, if_exists='replace')
        return

    draft_table = pd.concat([draft_df, draft_series.to_frame().T], ignore_index=True)
    write_to_player_database(str(user_id), draft_table, if_exists='replace')

#endregion

#region Table Import Methods

def import_drivers_table() -> pd.DataFrame:
    if conn is not None:
        drivers = pd.read_sql_table('drivers', conn)
        logger.info(f'Imported drivers table')
        return drivers
    else:
        logger.error(f'Could not import drivers table as there is no connection to PostgreSQL.')


def import_players_table() -> pd.DataFrame:
    if conn is not None:
        players = pd.read_sql_table('players', conn)
        logger.info(f'Imported players table')
        return players
    else:
        logger.error(f'Could not import players table as there is no connection to PostgreSQL.')

def import_results_table() -> pd.DataFrame:
    if conn is not None:
        results = pd.read_sql_table('results', conn)
        logger.info(f'Imported results table')
        return results
    else:
        logger.error(f'Could not import results table as there is no connection to PostgreSQL.')

def import_teams_table() -> pd.DataFrame:
    if conn is not None:
        teams = pd.read_sql_table('teams', conn)
        logger.info(f'Imported teams table')
        return teams
    else:
        logger.error(f'Could not import teams table as there is no connection to PostgreSQL.')

#endregion

#region Table Imports

drivers = import_drivers_table()
players = import_players_table()
results = import_results_table()
teams = import_teams_table()

#endregion

#region Formula 1 Data

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

def update_player_points():
    for player in players.userid:
        player_results = results.loc[results['userid'] == player].drop(labels=['userid','teamname'], axis=1).squeeze()
        players.loc[players['userid'] == player, 'points'] = player_results.sum()
        logger.info(f"Updated {players.loc[players['userid'] == player, 'username'].item()}'s season points! ({players.points.item()} points)")

def populate_results():
    #TODO: Solve the problem of adding new entries to the results database, as it is currently unpopulated.
    # Create a series with all the requisite column values and append it to the results dataframe.
    # Update individual round scores by accessing the score using the userid and round_[round number here] fields within a DataFrame search.

    # empty_results = results[0:0]
    # new_results = empty_results

    logger.info(f"Results: {results}")

    for player in players.userid:
        # TODO: Add rounds to series using loop, with the number of iterations being the number of rounds from jolpica. DO NOT hard code the number of rounds.
        result_record = pd.Series({
            'userid': player,
            'username': players.loc[players['userid'] == player, 'username'].item(),
            'teamname': players.loc[players['userid'] == player, 'teamname'].item(),
            'round1': 0,
            'round2': 0,
            'round3': 0,
            'round4': 0,
            'round5': 0,
            'round6': 0,
            'round7': 0,
            'round8': 0,
            'round9': 0,
            'round10': 0,
            'round11': 0,
            'round12': 0,
            'round13': 0,
            'round14': 0,
            'round15': 0,
            'round16': 0,
            'round17': 0,
            'round18': 0,
            'round19': 0,
            'round20': 0,
            'round21': 0,
            'round22': 0,
            'round23': 0,
            'round24': 0})

        new_results = pd.concat([results, result_record.to_frame().T], ignore_index=True)

        logger.info(f"New results: {new_results}")
        write_to_database('results', new_results, if_exists='replace')

def update_player_result(user_id: int, round: int, points: float):
    if any(user_id == results.userid):
        results.loc[results.index[results['userid'] == user_id], f'round_{round}'] = points
        write_to_database('results', results, if_exists='replace')
        logger.info(f"Updated {players.loc[players['userid'] == user_id, 'username'].item()}'s results: {results}")
    else:
        try:
            # TODO: Add rounds to series using loop, with the number of iterations being the number of rounds from jolpica. DO NOT hard code the number of rounds.
            result_record = pd.Series({
                'userid': user_id,
                'username': players.loc[players['userid'] == user_id, 'username'].item(),
                'teamname': players.loc[players['userid'] == user_id, 'teamname'].item(),
                'round1': 0,
                'round2': 0,
                'round3': 0,
                'round4': 0,
                'round5': 0,
                'round6': 0,
                'round7': 0,
                'round8': 0,
                'round9': 0,
                'round10': 0,
                'round11': 0,
                'round12': 0,
                'round13': 0,
                'round14': 0,
                'round15': 0,
                'round16': 0,
                'round17': 0,
                'round18': 0,
                'round19': 0,
                'round20': 0,
                'round21': 0,
                'round22': 0,
                'round23': 0,
                'round24': 0})
        except ValueError as e:
            logger.error(f"User with id {user_id} does not exist! Please register the user before updating points.")
            return

        new_results = pd.concat([results, result_record.to_frame().T], ignore_index=True)
        new_results.loc[new_results.index[new_results['userid'] == user_id], f'round{round}'] = points
        write_to_database('results', new_results, if_exists='replace')
        logger.info(f"New results: {new_results}")

#endregion

#region Utilities
def write_to_database(table: str, data: pd.DataFrame, if_exists: Literal["fail", "replace", "append"] = "replace", index: bool = False):
    result = data.to_sql(table, conn, if_exists=if_exists, index=index)
    logger.info(f'Wrote to fantasy database: {data.info}')

def write_to_player_database(table: str, data: pd.DataFrame, if_exists: Literal["fail", "replace", "append"] = "replace", index: bool = False):
    result = data.to_sql(table, player_conn, if_exists=if_exists, index=index)
    logger.info(f'Wrote to player database: {data.info}')
#endregion

if __name__ == '__main__':
    #update_player_result(867434834120540180, 17, 57)
    pass