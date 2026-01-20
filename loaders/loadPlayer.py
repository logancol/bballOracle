import psycopg
import logging
import sys
from nba_api.stats.static import players
from app.core.config import settings

# -- simple, but giving same object structure in case I want to use it to pull player stats later
class PlayerLoader:
    def __init__(self, db_conn: psycopg.connection):
        self.conn = db_conn
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            stream_handler = logging.StreamHandler(sys.stdout)
            log_formatter = logging.Formatter("%(asctime)s [%(processName)s: %(process)d] [%(threadName)s: %(thread)d] [%(levelname)s] %(name)s: %(message)s")
            stream_handler.setFormatter(log_formatter)
            self.logger.addHandler(stream_handler)
    
    # dont need retry for static library data
    def load_player_index(self, cur: psycopg.cursor):
        self.logger.info(f"LOADING PLAYER INDEX FROM NBA_API STATIC DATA")
        all_players = players.get_players()
        for player in all_players:
            player_id = player['id']
            full_name = player['full_name']
            first_name = player['first_name']
            last_name = player['last_name']
            is_active = player['is_active']
            try:
                cur.execute("INSERT INTO player (id, full_name, first_name, last_name, is_active)" \
                " VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING;", (player_id, full_name, first_name, last_name, is_active))
            except psycopg.Error as e:
                self.logger.error(f"PROBLEM LOADING PLAYER WITH ID {player_id}: {e}")
                raise RuntimeError(f"Failed loading player {player_id}") from e
