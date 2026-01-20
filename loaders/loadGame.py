import psycopg
from time import sleep
import pandas as pd
import random
import sys
import logging
from app.core.config import settings
from nba_api.stats.endpoints import leaguegamefinder
from datetime import datetime, timedelta, date

class GameLoader:
    def __init__(self, db_connection, update: bool, whole_current_season: bool):
        # Configure database connection, logger
        self.conn = db_connection
        self.update = update
        self.whole_current_season = whole_current_season
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            stream_handler = logging.StreamHandler(sys.stdout)
            log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
            stream_handler.setFormatter(log_formatter)
            self.logger.addHandler(stream_handler)
        try:
            self.logger.info(f"FETCHING UNIQUE TEAM IDS")
            with self.conn.cursor() as cur:
                cur.execute("SELECT DISTINCT id FROM modern_team_index;")
                rows = cur.fetchall()
            self.team_ids = [row[0] for row in rows]
        except Exception:
            raise RuntimeError("PROBLEM LOADING TEAM IDS")

        # abreviation to team id conversions for the play by play era
        self.abrev_id_map = {'ATL': 1610612737, 'BKN': 1610612751,'BOS': 1610612738,'CHA': 1610612766,'CHH': 1610612766,'CHI': 1610612741,'CLE': 1610612739,
                             'DAL': 1610612742,'DEN': 1610612743,'DET': 1610612765,'GSW': 1610612744,'HOU': 1610612745,'IND': 1610612754,'LAC': 1610612746,
                             'LAL': 1610612747,'MEM': 1610612763,'MIA': 1610612748,'MIL': 1610612749,'MIN': 1610612750,'NJN': 1610612751,'NOH': 1610612740,
                             'NOK': 1610612740,'NOP': 1610612740,'NYK': 1610612752,'OKC': 1610612760,'ORL': 1610612753,'PHI': 1610612755,'PHX': 1610612756,
                             'POR': 1610612757,'SAC': 1610612758,'SAS': 1610612759,'SEA': 1610612760,'TOR': 1610612761,'UTA': 1610612762,'VAN': 1610612763,'WAS': 1610612764}
        
    # retries to be robust against nba_api errors and rate limiting
    def _with_retry(self, fn, desc: str, max_attempts: int = 6, base_sleep: float = 0.5, max_sleep: float = 60.0):
        delay = base_sleep
        for call_attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except Exception as e:
                self.logger.error(f"Problem with NBA API fetching {desc} Attempt {call_attempt} out of {max_attempts}: {e}")
                if call_attempt == max_attempts:
                    raise
                jitter = random.uniform(0, 0.5 * delay)
                sleep(delay + jitter)
                delay = min(delay * 2, max_sleep)

    def insert_game(self, cur, game: pd.Series, season_type: str):
        # TEAM AGNOSTIC GAME INFO
        primary_team_abrev = game['TEAM_ABBREVIATION']
        secondary_team_abrev = game['MATCHUP'][-3:]
        primary_team_id = self.abrev_id_map[primary_team_abrev]
        secondary_team_id = self.abrev_id_map[secondary_team_abrev]
        game_id = game['GAME_ID']
        game_season_id = game['SEASON_ID']
        home_team_id = -1
        away_team_id = -1
        if game['MATCHUP'][4] == '@':
            away_team_id = game['TEAM_ID']
            home_team_id = self.abrev_id_map[secondary_team_abrev]
        else:
            home_team_id = game['TEAM_ID']
            away_team_id = self.abrev_id_map[secondary_team_abrev]
        game_date = datetime.strptime(game['GAME_DATE'], "%Y-%m-%d").date()
        game_winner_id = primary_team_id if game['WL'] == 'W' else secondary_team_id
        home_team_abrev = primary_team_abrev if home_team_id == primary_team_id else secondary_team_abrev
        away_team_abrev = primary_team_abrev if away_team_id == primary_team_id else secondary_team_abrev

        try:
            cur.execute("INSERT INTO game (id, season_id, home_team_id, home_team_abrev, away_team_id, away_team_abrev, date, season_type, winner_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;",
                            (game_id, game_season_id, home_team_id, home_team_abrev, away_team_id, away_team_abrev, game_date, season_type, game_winner_id))
        except psycopg.Error as e:
            self.logger.error(f"ERROR INSERTING GAME WITH ID {game_id}, ERROR: {e} ABORTING ...")
            raise
        
        # TEAM PERFORMANCE
        mins = game['MIN']
        pts = game['PTS']
        overtime = mins > 250 # this is a bit of an assumption will confirm using play by play data
        field_goals_made = game['FGM']
        field_goals_attempted = game['FGA']
        field_goal_percentage = game['FG_PCT']
        three_pointers_made = game['FG3M']
        three_pointers_attempted = game['FG3A']
        three_pointer_percentage = game['FG3_PCT']
        free_throws_made = game['FTM']
        free_throws_attempted = game['FTA']
        free_throw_percentage = game['FT_PCT']
        offensive_rebounds = game['OREB']
        defensive_rebounds = game['DREB']
        total_rebounds = game['REB']
        assists = game['AST']
        steals = game['STL']
        blocks = game['BLK']
        turnovers = game['TOV']
        personal_fouls = game['PF']
        plus_minus = int(game['PLUS_MINUS']) if pd.notna(game['PLUS_MINUS']) else None
        try: 
            cur.execute("INSERT INTO game_team_performance (game_id, team_id, team_abrev, mins, pts, overtime, field_goals_made, field_goals_attempted, field_goal_percentage, " \
            "three_pointers_made, three_pointers_attempted, three_pointer_percentage, free_throws_made, free_throws_attempted, free_throw_percentage, offensive_rebounds, " \
            "defensive_rebounds, total_rebounds, assists, steals, blocks, turnovers, personal_fouls, plus_minus) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
            "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", (game_id, primary_team_id, primary_team_abrev, mins, pts, overtime, field_goals_made, field_goals_attempted, field_goal_percentage,
                                                                three_pointers_made, three_pointers_attempted, three_pointer_percentage, free_throws_made, free_throws_attempted, free_throw_percentage, 
                                                                offensive_rebounds, defensive_rebounds, total_rebounds, assists, steals, blocks, turnovers, personal_fouls, plus_minus))
        except psycopg.Error as e: 
            self.logger.error(f"ERROR INSERTING TEAM SPECIFIC GAME INFO WITH GAME ID: {game_id}, TEAM ID: {primary_team_id} ERROR: {e} ABORTING ...")
            raise
        return True     

    def load_games(self):
        if not self.team_ids:
            raise RuntimeError(f"ABORTING GAME LOADING, TEAM IDS NOT FOUND")
        
        with self.conn.cursor() as cur:
            for id in self.team_ids:
                self.logger.info(f'LOADING {"CURRENT SEASON" if self.update else "ALL"} GAMES FOR TEAM {id}')
                if self.update or self.whole_current_season:
                    if self.whole_current_season:
                        date_from_nullable = None
                    else:
                        date_from_nullable = (date.today() - timedelta(days=3))

                    gamefinder_regular = self._with_retry(
                        lambda: leaguegamefinder.LeagueGameFinder(team_id_nullable=id, season_type_nullable="Regular Season", season_nullable='2025-26', date_from_nullable=date_from_nullable),
                        desc=f"Regular season games for 2025/26 season for team {id}"
                    )
                    gamefinder_playoff = self._with_retry(
                        lambda: leaguegamefinder.LeagueGameFinder(team_id_nullable=id, season_type_nullable="Playoffs", season_nullable='2025-26', date_from_nullable=date_from_nullable),
                        desc=f"Playoff games for 2025/26 season for team {id}"
                    )

                else:
                    gamefinder_regular = self._with_retry(
                        lambda: leaguegamefinder.LeagueGameFinder(team_id_nullable=id, season_type_nullable="Regular Season", date_from_nullable='11-01-1996'), # pbp era
                        desc=f"Regular Season games for entire pbp era for team: {id}"
                    )
                    gamefinder_playoff = self._with_retry(
                        lambda: leaguegamefinder.LeagueGameFinder(team_id_nullable=id, season_type_nullable="Playoffs", date_from_nullable='11-01-1996'),
                        desc=f"Playoff games for entire pbp era for team: {id}"
                    )

                # ITERATE THROUGH REGULAR SEASON GAMES FOR TEAM
                games = gamefinder_regular.get_data_frames()[0]
                for _, game in games.iterrows():
                    self.insert_game(cur, game, "regular")

                # ITERATE THROUGH PLAYOFF GAMES FOR TEAM
                games = gamefinder_playoff.get_data_frames()[0]
                for _, game in games.iterrows():
                    self.insert_game(cur, game, "playoff")
