import psycopg2
from nba_api.stats.static import teams
from nba_api.stats.static import players
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.stats.library.parameters import Season
from nba_api.stats.library.parameters import SeasonType
from nba_api.stats.endpoints import playerindex
import time
import re
import pandas as pd

conn = psycopg2.connect(
    database="streamd",
    user="docker",
    password="docker",
    port=5431
)
cur = conn.cursor()

historical_team_abbreviations = [
    # historical teams in play-by-play era
    "NJN",  # New Jersey Nets (pre-Brooklyn)
    "CHB",  # CHARLOTTE BOBCATS
    "VAN",  # Vancouver Grizzlies
    "SEA"   # Seattle SuperSonics
    
]

all_teams = teams._get_teams()
for team in all_teams:
    id = team['id']
    full_name = team['full_name']
    abbreviation = team['abbreviation']
    nickname = team['nickname']
    city = team['city']
    cur.execute("INSERT INTO Team (team_id, team_full_name, team_abbreviation, team_nickname, team_city) VALUES (%s, %s, %s, %s, %s);", (id, full_name, abbreviation, nickname, city))

cur.execute("INSERT INTO Team (team_id, team_full_name, team_abbreviation, team_nickname, team_city) VALUES (%s, %s, %s, %s, %s);", (1, "New Jersey Nets", "NJN", "Nets", "New Jersey"))
cur.execute("INSERT INTO Team (team_id, team_full_name, team_abbreviation, team_nickname, team_city) VALUES (%s, %s, %s, %s, %s);", (2, "Charlotte Bobcats", "CHB", "Bobcats", "Charlotte"))
cur.execute("INSERT INTO Team (team_id, team_full_name, team_abbreviation, team_nickname, team_city) VALUES (%s, %s, %s, %s, %s);", (3, "Vancouver Grizzlies", "VAN", "Grizzlies", "Vancouver"))
cur.execute("INSERT INTO Team (team_id, team_full_name, team_abbreviation, team_nickname, team_city) VALUES (%s, %s, %s, %s, %s);", (4, "Seattle SuperSonics", "SEA", "SuperSonics", "Seattle"))
conn.commit()