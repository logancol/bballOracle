# nightly updates (game, pbp, new players)
from loaders.loadPlayer import PlayerLoader
from loaders.loadPBP import PBPDataLoader
import psycopg
from app.core.config import settings
from loaders.loadGame import GameLoader
from loaders.loadTeam import TeamLoader

# -> update player index -> update game data -> update play by play data
def main():
    DB_URL = settings.DATABASE_URL_RW
    with psycopg.connect(DB_URL) as conn: # with pattern for context management
        with conn.transaction():
            loader = TeamLoader(conn)
            with conn.cursor() as cur:
                loader.load_historical_teams(cur)
                loader.load_modern_teams(cur)

    with psycopg.connect(DB_URL) as conn:
        with conn.transaction():
            loader = PlayerLoader(conn)
            with conn.cursor() as cur:
                loader.load_player_index(cur)
                
    with psycopg.connect(DB_URL) as conn:
        with conn.transaction():
            game_loader = GameLoader(conn, update=True)
            game_loader.load_games()
            
    with psycopg.connect(DB_URL) as conn:
        data_loader = PBPDataLoader(conn, update=True)
        data_loader.load_pbp_data()

if __name__ == "__main__":
    main()