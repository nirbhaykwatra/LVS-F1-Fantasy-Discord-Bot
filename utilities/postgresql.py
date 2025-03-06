# A module for all PostgreSQL methods. Use this to retrieve and store data in a PostgreSQL database.
import traceback
from typing import Literal
import sqlalchemy as sql
from sqlalchemy_utils import database_exists, create_database
import pandas as pd
import settings
from utilities import fastf1util as f1

logger = settings.create_logger('sql')


#region Utilities
def write_to_fantasy_database(table: str, data: pd.DataFrame, if_exists: Literal["fail", "replace", "append"] = "replace", index: bool = False):
    result = data.to_sql(table, conn, if_exists=if_exists, index=index)
    logger.info(f'Wrote to fantasy database: {data.info}')

def write_to_player_database(table: str, data: pd.DataFrame, if_exists: Literal["fail", "replace", "append"] = "replace", index: bool = False):
    result = data.to_sql(table, player_conn, if_exists=if_exists, index=index)
    logger.info(f'Wrote to player database: {data.info}')
#endregion

# region Connect to fantasy database
engine = sql.create_engine(settings.POSTGRES_BASE_URL)
if not database_exists(engine.url):
    create_database(engine.url)
    logger.info(f'Fantasy database not found. Created new database: {engine.url}.')
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
if not database_exists(player_engine.url):
    create_database(player_engine.url)
    logger.info(f'Player database not found. Created new database: {player_engine.url}.')
player_conn = None
try:
    player_conn = player_engine.connect()
    logger.info(
        f'Connected to {player_engine.url.database} database on {player_engine.url.username}@{player_engine.url.host}:{player_engine.url.port}')
    player_metadata = sql.MetaData()
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
    
def remove_player_table(user_id: int):
    player_table = sql.Table(str(user_id), player_metadata)
    player_table.drop(player_engine, checkfirst=True)
    #sql_query = 'DROP TABLE IF EXISTS :user'
    #result = player_conn.execute(text(sql_query), {'user': user_id})

#endregion

def create_timings_table():
    timings_db = pd.DataFrame(columns=['round', 'deadline', 'reset'])
    write_to_fantasy_database("timings", timings_db, if_exists='replace')

#region Fantasy DB Table Import Methods

def import_players_table() -> pd.DataFrame:
    if conn is not None:
        try:
            players = pd.read_sql_table('players', conn)
        except ValueError as e:
            write_to_fantasy_database('players', pd.DataFrame(), if_exists='replace')
            players = pd.read_sql_table('players', conn)
        logger.info(f'Imported players table')
        return players
    else:
        logger.error(f'Could not import players table as there is no connection to PostgreSQL.')

def import_results_table() -> pd.DataFrame:
    if conn is not None:
        try:
            results = pd.read_sql_table('results', conn)
        except ValueError as e:
            write_to_fantasy_database('results', pd.DataFrame(), if_exists='replace')
            results = pd.read_sql_table('results', conn)
        logger.info(f'Imported results table')
        return results
    else:
        logger.error(f'Could not import results table as there is no connection to PostgreSQL.')
        
def import_timings_table() -> pd.DataFrame:
    if conn is not None:
        try:
            timings = pd.read_sql_table('timings', conn)
            return timings
        except ValueError as e:
            logger.info(f'Could not import timings table as it does not exist.')
    else:
        logger.error(f'Could not import timings table as there is no connection to PostgreSQL.')

#endregion

#region Table Imports

players = import_players_table()
results = import_results_table()
timings = import_timings_table()

#endregion

def retrieve_timings() -> pd.DataFrame:
    return timings

def modify_timings(round_number: int, timestamp: str, column: str):
    timings.loc[timings['round'] == round_number, column] = pd.Timestamp(ts_input=timestamp)
    write_to_fantasy_database('timings', timings, if_exists='replace')

#region Fantasy Table Validation
def initialise_results(frame: pd.DataFrame) -> pd.DataFrame:
    frame_columns = ['userid', 'username', 'teamname']
    for rounds in f1.ergast.get_race_schedule(season='current')['round']:
        frame_columns.append(f'round{rounds}')
        frame_columns.append(f'round{rounds}breakdown')
    frame[frame_columns] = None
    return frame

def initialise_players(frame: pd.DataFrame) -> pd.DataFrame:
    frame_columns = ['userid', 'username', 'teamname', 'teammotto','points', 'timezone']
    frame[frame_columns] = None
    return frame

bIsPlayersEmpty = players.empty
bIsResultsEmpty = results.empty

if bIsPlayersEmpty:
    players = initialise_players(players)
    write_to_fantasy_database('players', players, if_exists='replace')
    logger.info(f'Initialised players table: {players}')

if bIsResultsEmpty:
    results = initialise_results(results)
    write_to_fantasy_database('results', results, if_exists='replace')
    logger.info(f'Initialised results table: {results}')

#endregion

#region Formula 1 Data

def update_player_points():
    for player in players.userid:
        total_points = 0
        for round_number in f1.event_schedule.RoundNumber:
            total_points += results.loc[results['userid'] == player, f'round{round_number}'].item()
            
        players.loc[players['userid'] == player, 'points'] = total_points
        write_to_fantasy_database('players', players, if_exists='replace')
        logger.info(f"Updated {players.loc[players['userid'] == player, 'username'].item()}'s season points! ({total_points} points)")

#endregion



if __name__ == '__main__':
    update_player_points()
    pass