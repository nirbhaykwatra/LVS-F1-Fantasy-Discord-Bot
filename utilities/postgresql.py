# A module for all PostgreSQL methods. Use this to retrieve and store data in a PostgreSQL database.
import psycopg as ps
import sqlalchemy as sql
from sqlalchemy import delete
from sqlalchemy.sql import text
import pandas as pd
import settings
from utilities import fastf1util

logger = settings.create_logger('sql')

#region Connect to database
engine = sql.create_engine(settings.POSTGRES_BASE_URL)
try:
    conn = engine.connect()
    logger.info(f'Connected to {engine.url.database} database on {engine.url.username}@{engine.url.host}:{engine.url.port}')
except Exception as e:
    logger.error(f'Could not connect to PostgreSQL server! Exception: {e}')
#endregion

#region Formula 1 Data

#endregion

if __name__ == '__main__':
    pass