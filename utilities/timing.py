# TODO: Implement automatic round changing and timezone conversions for all relevant
#   information methods such as grand-prix info, team and draft.
import os.path

# TODO: Implement draft deadlines and draft freeze windows
import pandas as pd
import utilities.postgresql as sql
import settings
from utilities.fastf1util import event_schedule

logger = settings.create_logger('timing')

def populate_timings_table():
    """Add all draft deadline and deadline reset UTC timestamps to the timings table."""
    buffer_series = pd.Series({'round': 0, 'deadline': pd.Timestamp.utcnow(), 'reset': pd.Timestamp.utcnow()}).to_frame().T
    timings_df = pd.DataFrame(columns=['round', 'deadline', 'reset'])
    timings_with_buffer_df = pd.concat([timings_df, buffer_series], ignore_index=True)
    populated_timings = timings_with_buffer_df
    
    for event in event_schedule['EventName']:
        round_number = event_schedule.loc[event_schedule['EventName'] == event, 'RoundNumber'].item()
        round_number = int(round_number)
        deadline_record = pd.Series({'round': round_number, 'deadline': pd.Timestamp.utcnow(), 'reset': pd.Timestamp.utcnow()})
        
        if event_schedule.loc[event_schedule['EventName'] == event, 'EventFormat'].item() == 'sprint_qualifying' :
            deadline_record = pd.Series({'round': round_number, 
                                         'deadline': event_schedule.loc[event_schedule['EventName'] == event, 'Session2DateUtc'].item(), 
                                         'reset': event_schedule.loc[event_schedule['EventName'] == event, 'Session5DateUtc'].item() + pd.Timedelta(hours=3)
                                         }).to_frame().T
        if event_schedule.loc[event_schedule['EventName'] == event, 'EventFormat'].item() == 'conventional' :
            deadline_record = pd.Series({'round': round_number,
                                         'deadline': event_schedule.loc[event_schedule['EventName'] == event, 'Session4DateUtc'].item(),
                                         'reset': event_schedule.loc[event_schedule['EventName'] == event, 'Session5DateUtc'].item() + pd.Timedelta(hours=3)
                                         }).to_frame().T
        
        populated_timings = pd.concat([populated_timings, deadline_record], ignore_index=True)
    
    sql.write_to_fantasy_database('timings', populated_timings)

def draft_deadline_passed(user_tz: str) -> bool:
    current_time = pd.Timestamp.now(tz=user_tz).tz_localize(None)
    timings_table = sql.retrieve_timings()
    
    round_deadline = timings_table.loc[timings_table['round'] == settings.F1_ROUND, 'deadline'].item()
    round_reset = timings_table.loc[timings_table['round'] == settings.F1_ROUND, 'reset'].item()
    
    round_deadline_tz = round_deadline.tz_localize(tz=user_tz)
    round_reset_tz = round_reset.tz_localize(tz=user_tz)
    
    #logger.info(f'Deadline table: {timings_table}')
    
    return round_deadline_tz < current_time < round_reset_tz


if __name__ == '__main__':
    logger.info(draft_deadline_passed(user_tz='US/Pacific'))
    #populate_timings_table()