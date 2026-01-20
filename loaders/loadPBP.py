import psycopg
from time import sleep
from nba_api.live.nba.endpoints import PlayByPlay
import re
from datetime import timedelta, date
from app.core.config import settings
import sys
import pandas as pd
import random
import logging

class PBPDataLoader:
    # --- Configure db connection and logging ---
    def __init__(self, db_connection, update: bool, whole_current_season: bool):
        self.conn = db_connection
        self.logger = logging.getLogger(__name__)
        self.whole_current_season = whole_current_season
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            stream_handler = logging.StreamHandler(sys.stdout)
            log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
            stream_handler.setFormatter(log_formatter)
            self.logger.addHandler(stream_handler)
        self.update = update
        try:
            self.logger.info(f"FETCHING UNIQUE PLAYER IDS")
            with self.conn.cursor() as cur:
                cur.execute("SELECT DISTINCT id FROM player;")
                rows = cur.fetchall()
            self.player_ids = {int(row[0]) for row in rows}
        except Exception as e:
            raise RuntimeError(f"PROBLEM LOADING PLAYER IDS") from e
        
    # --- retries to be robust against nba_api errors and rate limiting
    def _with_retry(self, fn, desc: str, max_attempts: int = 6, base_sleep: float = 0.5, max_sleep: float = 60.0):
        delay = base_sleep
        for call_attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except Exception as e:
                if call_attempt == max_attempts:
                    self.logger.error(f"FATAL ERROR WORKING WITH NBA API, ROLLING BACK")
                    raise
                else:
                    self.logger.warning(f"Problem with NBA API fetching {desc} Attempt {call_attempt} out of {max_attempts}: {e}")
                jitter = random.uniform(0, 0.5 * delay)
                sleep(delay + jitter)
                delay = min(delay * 2, max_sleep)

    # --- helper to convert the iso8601 timestamps (shot clock) to intervals for storage in db
    def iso8601_to_sql_interval(self, duration: str) -> str:
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
    
    # --- helps validate type saftey for player ids, they occasionally come back as int, string, float, none
    def _player_id_or_none(self, id):
        if pd.isna(id):
            return None
        try:
            pid = int(float(id))
        except:
            return None
        return pid if pid in self.player_ids else None

    # ---  pbp data loader, either updates current season pbp data or fetches data for all years as part of init
    def load_pbp_data(self):    
        if self.whole_current_season:
            season_ids = [22025, 42025]
        elif self.update:
            season_ids = [22025, 42025]
        else:
            season_ids = [21996, 41996, 21997, 41997, 21998, 41998, 21999, 41999, 22000, 42000, 22001, 42001, 
                          22002, 42002, 22003, 42003, 22004, 42004, 22005, 42005, 22006, 42006, 22007, 42007, 
                          22008, 42008, 22009, 42009, 22010, 42010, 22011, 42011, 22012, 42012, 22013, 42013, 
                          22014, 42014, 22015, 42015, 22016, 42016, 22017, 42017, 22018, 42018, 22019, 42019, 
                          22020, 42020, 22021, 42021, 22022, 42022, 22023, 42023, 22024, 42024, 22025]

        # Fetch games logged in the database
        try:
            with self.conn.cursor() as cur:
                cur.execute('SELECT id, season_type, season_id, home_team_id, away_team_id, home_team_abrev, away_team_abrev, date FROM game;') 
                rows = cur.fetchall()
        except psycopg.Error as e:
            self.logger.error(f"ERROR FETCHING GAME INFO: {e}")
            raise

        relevant_games = [row for row in rows if row[2] in season_ids]
        if self.update: # if updating, only look at pbp data from the past few days, although updates are nightly, this helps account for revised data and failed jobs
            relevant_games = [row for row in relevant_games if row[7] > (date.today() - timedelta(days=3))]
        num_games = len(relevant_games)

        # getting pbp dfs for each fetched game, processing, inserting into dataframe
        for count, row in enumerate(relevant_games, start=1):
            self.logger.info(f'FETCHING AND STORING PBP INFO FOR GAME: {count} OF {num_games}')
            with self.conn.transaction():
                with self.conn.cursor() as cur:
                    count += 1
                    game_id = str(row[0]).zfill(10) # standardizing id size to 10 to align with nba_api
                    pbp = self._with_retry(
                        lambda: PlayByPlay(game_id = game_id),
                        desc=f"PBP Data for game with id: {game_id}"
                    )  
                    df = pd.DataFrame(pbp.actions.get_dict()) 
                    game_id = int(game_id)
                    season_type = row[1] # append season type string manually
                    season_id = row[2] # append season id manually
                    home_team_id = row[3] 
                    away_team_id = row[4]
                    home_team_abrev = row[5]
                    away_team_abrev = row[6]
                    
                    for _, event in df.iterrows():
                        # non-conditional on event type
                        event_num = event['actionNumber']
                        event_type = event['actionType']
                        event_subtype = event['subType']
                        home_score = event['scoreHome']
                        away_score = event['scoreAway']
                        period = event['period']
                        clock = None 
                        if pd.notna(event['clock']):
                            clock = self.iso8601_to_sql_interval(event['clock'])
                        home_team_id = row[3]
                        away_team_id = row[4]
                        possession_team_abrev = None
                        possession_team_id = None
                        event_team_id = None
                        event_team_abrev = None
                        if pd.notna(event['teamId']):
                            event_team_id = int(float(event['teamId']))
                        if pd.notna(event['teamTricode']):
                            event_team_abrev = event['teamTricode']
                        if pd.notna(event['possession']):
                            possession_team_id = int(float(event['possession']))
                            if possession_team_id == home_team_id:
                                possession_team_abrev = home_team_abrev
                            elif possession_team_id == away_team_id:
                                possession_team_abrev = away_team_abrev
                            else:
                                possession_team_abrev = None
                        is_overtime = period > 4

                        # conditional on event
                        shooter_id = None
                        assister_id = None
                        jump_ball_winner_id = None
                        jump_ball_loser_id = None
                        jump_ball_recovered_id = None
                        rebounder_id = None
                        foul_drawn_id = None
                        fouler_id = None
                        stealer_id = None
                        team_rebound = None
                        team_turnover = None
                        blocker_id = None
                        sub_in_id = None
                        sub_out_id = None
                        turnover_id = None
                        foul_is_technical = None
                        foul_is_personal = None
                        foul_is_offensive = None
                        offensive_rebound = None
                        side = None
                        descriptor = None
                        area = None
                        area_detail = None
                        shot_distance = None
                        shot_made = None
                        shot_value = None
                        shot_x = None            
                        shot_y = None

                        # filling conditional on event type
                        if pd.notna(event['actionType']) and event['actionType'] == 'freethrow':
                            shot_value = 1
                            shooter_id = self._player_id_or_none(event.get('personId'))
                            shot_made = True if event['shotResult'] == 'Made' else False

                        # heave game id logged in google doc
                        elif event.get('isFieldGoal') == 1: # nba_api does not properly support logging made heaves at the moment, I should do this an an open source contribution, ignoring for now
                            if event['actionType'] == '2pt':
                                shot_value = 2
                            else:
                                shot_value = 3
                            side = event['side']
                            descriptor = event['descriptor']
                            shot_x = event['x']
                            shot_y = event['y']
                            area = event['area']
                            area_detail = event['areaDetail']
                            shot_distance = event['shotDistance']
                            shooter_id = self._player_id_or_none(event.get('personId'))
                            assister_id = self._player_id_or_none(event.get('assistPersonId'))
                            shot_made = True if event['shotResult'] == 'Made' else False
                            if not shot_made:
                                blocker_id = self._player_id_or_none(event.get('blockPersonId'))

                        elif event['actionType'] == 'jumpball':
                            jump_ball_loser_id = self._player_id_or_none(event.get('jumpBallLostPersonId'))
                            jump_ball_winner_id = self._player_id_or_none(event.get('jumpBallWonPersonId'))
                                
                        elif event.get('actionType') == 'turnover':
                            turnover_id = self._player_id_or_none(event.get('personId'))
                            team_turnover = pd.isna(event.get('personId'))
                            if pd.notna(event.get('area')):
                                area = event['area']
                            area_detail = event.get('areaDetail')
                            stealer_id = self._player_id_or_none(event.get('stealPersonId'))

                        elif event['actionType'] == 'foul':
                            foul_is_technical = event['subType'] == 'technical'
                            foul_is_offensive = event['subType'] == 'offensive'
                            foul_is_personal = event['subType'] == 'personal' or event['subType'] == 'offensive'
                            foul_drawn_id = self._player_id_or_none(event.get('foulDrawnPersonId'))
                            fouler_id = self._player_id_or_none(event.get('personId'))

                        elif event['actionType'] == 'substitution':
                            if event.get('subType') == 'out':
                                sub_out_id = self._player_id_or_none(event.get('personId'))
                            if event.get('subType') == 'in':
                                sub_in_id = self._player_id_or_none(event.get('personId'))

                        elif event['actionType'] == 'rebound':
                            rebounder_id = self._player_id_or_none(event.get('personId'))
                            team_rebound = rebounder_id is None
                            offensive_rebound = event.get('subType') == 'offensive'

                        elif event['actionType'] == 'violation':
                            qualifiers = event.get('qualifiers')
                            team_turnover = isinstance(qualifiers, (list, tuple, set, str)) and ('team' in qualifiers)

                        values = [game_id, season_id, season_type, event_num, event_type, event_subtype,
                                    home_score, away_score, period, clock,
                                    home_team_id, away_team_id, home_team_abrev, away_team_abrev,
                                    possession_team_id, possession_team_abrev, event_team_id, event_team_abrev, is_overtime,
                                    shooter_id, assister_id, jump_ball_winner_id, jump_ball_loser_id, jump_ball_recovered_id,
                                    rebounder_id, turnover_id, foul_drawn_id, fouler_id, stealer_id, blocker_id, sub_in_id, sub_out_id,
                                    foul_is_technical, foul_is_personal, foul_is_offensive, team_turnover, team_rebound, offensive_rebound,
                                    side, descriptor, area, area_detail, shot_distance, shot_made, shot_value, shot_x, shot_y]
                        try:
                            cur.execute(
                                """
                                INSERT INTO pbp_raw_event (
                                    game_id, season_id, season_type, event_num, event_type, event_subtype,
                                    home_score, away_score, period, clock,
                                    home_team_id, away_team_id, home_team_abrev, away_team_abrev,
                                    possession_team_id, possession_team_abrev, event_team_id, event_team_abrev, is_overtime,
                                    shooter_id, assister_id, jump_ball_winner_id, jump_ball_loser_id, jump_ball_recovered_id,
                                    rebounder_id, turnover_id, foul_drawn_id, fouler_id, stealer_id, blocker_id, sub_in_id, sub_out_id,
                                    foul_is_technical, foul_is_personal, foul_is_offensive, team_turnover, team_rebound, offensive_rebound,
                                    side, descriptor, area, area_detail, shot_distance, shot_made, shot_value, shot_x, shot_y
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s,
                                    %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (game_id, event_num) DO NOTHING;
                                """,
                                tuple(values)
                            )
                        except psycopg.Error as e:
                            self.logger.error(f"PBP STORAGE ERROR: {e} FOR GAME {game_id}, EVENT {event_num}")
                            raise
