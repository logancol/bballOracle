import psycopg2
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import Season
from nba_api.stats.library.parameters import SeasonType
from nba_api.stats.endpoints import playbyplay
import time
import re
import pandas as pd

# Getting orlando magic team id

nba_teams = teams.get_teams()
magic = [team for team in nba_teams if team['abbreviation'] == 'ORL'][0]
magic_id = magic['id']
print(f'magic id: {magic_id}')

# Getting games from this season (regular season games from this year)

gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=magic_id,
                            season_nullable=Season.default,
                            season_type_nullable=SeasonType.regular)  
games_dict = gamefinder.get_normalized_dict()
games = games_dict['LeagueGameFinderResults']

# Get play by play from found games 

dfs = []
for game in games:
    dfs.append(playbyplay.PlayByPlay(game['GAME_ID']).get_data_frames()[0])
    time.sleep(1) # avoid hitting rate limit

# connect to database

conn = psycopg2.connect(
    database="streamd",
    user="docker",
    password="docker",
    port=5431
)

# Open cursor to perform database operations
cur = conn.cursor()

# --- EVENT CODES ---
# 1 - made shot
# 2 - missed shot
# 3 - free throw, missed free throw starts with MISS
# 4 - rebound, denoting offensive or defensive
# 5 - steals and turnovers
# 6 - foul perpretrator and fouled
# 7 - goaltending?
# 8 - substitution

# final_df contains all of the playbyplay info for the specified timeframe that we need to go through

# https://github.com/swar/nba_api/blob/master/docs/examples/PlayByPlay.ipynb sourced for play by play endpoint usage

# -- IN THE FUTURE, SET UP SUPPORT FOR SHOT CHART DETAIL ENDPOINT WHICH WILL GIVE COORDINATES AND MORE ACCURATE SHOT LOCATION INFORMATION


final_df = pd.concat(dfs, ignore_index=True)
for index, row in final_df.iterrows():
    if row['EVENTMSGTYPE'] == 1:
        # made shot
        game_id = row['GAME_ID']
        event_num = row['EVENTNUM']
        event_type = "MADE SHOT"
        event_subtype = "UNKNOWN"
        shot_distance = None

        # used to search for event subtype 
        p = re.compile(r"(\s{2}|\' )([\w+ ]*)")
        description = row['HOMEDESCRIPTION'] or row['VISITORDESCRIPTION']
        if description:
            match = p.search(description)
            if match:
                event_subtype = match.group(2).rstrip().replace(' ', '_').upper()
            foot_match = re.search(r"(\d+)'", description)
            if foot_match:
                shot_distance = int(foot_match.group(1))
            elif "3PT" in description: # for now, I'm going to use a stand in value for 3 point shots with unkown distancee
                shot_distance = 24

        season = row['SEASON']
        season_type = row['SEASON_TYPE']
        period = row['PERIOD']
        clock = row['PCTIMESTRING']
        home_team_id = row['HOME_TEAM_ID']
        away_team_id = row['AWAY_TEAM_ID']
        possession_team_id = row['POSESSION_TEAM_ID']
        primary_player_id = row['PRIMARY_PLAYER_ID']

        # then add to database
        # this gives us shot distances, made shots, can ask questions like which player has scored the most shots on the pacers this year within 12 feet

        # for this we also need a table that links players to ids and teams to ids so lets figure that out






#cur.execute("INSERT INTO Games (game_id, season) VALUES (%s, %s)", (1929, 20002))
#cur.execute("SELECT * FROM Games")
#rows = cur.fetchall()
#conn.commit()
#print(rows)

# Query the databse
# docker exec -it streamd_db psql -U docker -d streamd lets you work with the db from command line