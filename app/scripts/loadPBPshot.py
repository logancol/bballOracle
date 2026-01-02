import psycopg2
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import Season
from nba_api.stats.library.parameters import SeasonType
from nba_api.stats.endpoints import playbyplayv3
from datetime import timedelta
import isodate
import time
import re
import pandas as pd
def iso8601_to_sql_interval(duration: str) -> str:
    pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?'
    match = re.match(pattern, duration)
    if not match:
        raise ValueError(f"Invalid ISO 8601 duration: {duration}")
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = float(match.group(3) or 0)

    sec_int = int(seconds)
    microsec = int((seconds - sec_int) * 1_000_000)
    interval_str = f"{hours} hours {minutes} minutes {sec_int} seconds {microsec} microseconds"
    
    return interval_str

# Get play by play from found games 

conn = psycopg2.connect(
    database="streamd",
    user="docker",
    password="docker",
    port=5431
)

# Open cursor to perform database operations
cur = conn.cursor()

cur.execute('SELECT game_id, season_type, season_id, home_team_id, away_team_id FROM Game;')
rows = cur.fetchall()
game_ids = [row[0] for row in rows if row[2] == 22025]

num_games = len(game_ids)
count = 0

dfs = []
for row in rows:
    if row[2] == 22025:
        count += 1
        print(f'Fetching pbp info for game {count} of {num_games}')
        game_id = str(row[0]).zfill(10)
        df = playbyplayv3.PlayByPlayV3(game_id=game_id).get_data_frames()[0]
        df['season_type'] = row[1]
        df['season_id'] = row[2]
        df['home_team_id'] = row[3]
        df['away_team_id'] = row[4]
        time.sleep(0.5)
        dfs.append(df)

# -- IN THE FUTURE, SET UP SUPPORT FOR SHOT CHART DETAIL ENDPOINT WHICH WILL GIVE COORDINATES AND MORE ACCURATE SHOT LOCATION INFORMATION

final_df = pd.concat(dfs, ignore_index=True)
total = len(final_df.index)
print(final_df.columns)
count = 0
rollback_count = 0
for index, row in final_df.iterrows():
    # retooling with v3 endpoint its way better
    count += 1
    if row['isFieldGoal'] == 1:
        try:
            print(f'Storing pbp shooting event {count} of {total}')
            game_id = row['gameId']
            event_num = row['actionNumber']
            event_type = row['actionType']
            event_subtype = row['subType']
            season = row['season_id'] # must add manually
            season_type = row['season_type'] # must add manually
            period = row['period']
            clock = iso8601_to_sql_interval(row['clock'])
            posession_team_id = row['teamId']
            primary_player_id = row['personId']
            home_team_id = row['home_team_id']
            away_team_id = row['away_team_id']
            shot_x = row['xLegacy']
            shot_y = row['yLegacy']
            home_score = None if row['scoreHome'] == '' else int(row['scoreHome'])
            away_score = None if row['scoreAway'] == '' else int(row['scoreAway'])
            is_three = row['shotValue'] == 3
            shot_made = row['shotResult'] == 'Made'
            points = row['shotValue'] if row['shotResult'] == 'Made' else 0

            print(f'Inserting pbp shooting event {count} of {total} with teams {home_team_id}, and {away_team_id}')

            cur.execute("INSERT INTO pbp_raw_event_shots (game_id, event_num, event_type, " \
            "event_subtype, season, season_type, period, clock, home_team_id, away_team_id, " \
            "possession_team_id, primary_player_id, shot_x, shot_y, home_score, away_score, is_three, shot_made, points) VALUES (" \
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (game_id, event_num, event_type,
            event_subtype, season, season_type, period, clock, home_team_id, away_team_id, posession_team_id, 
            primary_player_id, shot_x, shot_y, home_score, away_score, is_three, shot_made, points))
        except psycopg2.Error as e:
            print(e)
conn.commit()

# docker exec -it streamd_db psql -U docker -d streamd