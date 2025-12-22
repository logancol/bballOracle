import requests
import pandas as pd
from scipy import stats
import os
import numpy as np
import json
from dotenv import load_dotenv

load_dotenv()

# getting players on a team and then getting their individual statistical info, this probably a good way to keep up on rostered players?
# will cross check with other sources for accuracy

def get_player_ids_team(id):
    url = "https://v2.nba.api-sports.io/players"
    headers = {
        'x-apisports-key': os.getenv("FOOTBALL-API_KEY")
    }
    params = {
        'season': '2025', # this should reference a global variable down the road
        'team': id
    }
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    player_data = data['response']
    ids = []
    for player in player_data:
        ids.append(player['id'])
    return ids



# player_df = pd.json_normalize(player_data['response'])
print(get_player_ids_team(1))
