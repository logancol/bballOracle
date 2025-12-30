CREATE TABLE Player
(
    player_id INT PRIMARY KEY,
    player_name VARCHAR(256)
);

CREATE TABLE Games
(
    game_id INT PRIMARY KEY,
    season INT
);

pbp_raw_events (
  -- Identity
  game_id            BIGINT NOT NULL,
  event_num          INTEGER NOT NULL,        -- unique within game
  event_type         TEXT NOT NULL,            -- SHOT, REBOUND, FOUL, TURNOVER, SUB, etc
  event_subtype      TEXT,                     -- JUMPER, LAYUP, STEAL, OFF_FOUL, etc

  -- Game context
  season             INTEGER NOT NULL,
  season_type        TEXT NOT NULL,            -- REGULAR, PLAYOFFS
  period             INTEGER NOT NULL,
  clock              INTERVAL NOT NULL,        -- time remaining in period
  home_team_id       INTEGER NOT NULL,
  away_team_id       INTEGER NOT NULL,
  possession_team_id INTEGER,

  -- Primary actors (nullable by event_type)
  primary_player_id  INTEGER,                  -- shooter, fouler, turnover committer
  secondary_player_id INTEGER,                 -- assister, blocker, stealer
  tertiary_player_id INTEGER,                  -- sometimes used (e.g. fouled player)

  -- Explicit role columns (redundant but useful)
  passer_id          INTEGER,
  shooter_id         INTEGER,
  scorer_id          INTEGER,
  rebounder_id       INTEGER,
  blocker_id         INTEGER,
  fouler_id          INTEGER,
  fouled_id          INTEGER,
  turnover_player_id INTEGER,
  steal_player_id    INTEGER,
  assister_id        INTEGER,

  -- Shot context
  shot_type          TEXT,                     -- JUMPER, LAYUP, DUNK, FT
  shot_distance      INTEGER,                  -- feet
  shot_zone          TEXT,
  is_three           BOOLEAN,
  is_assisted        BOOLEAN,
  shot_made          BOOLEAN,
  points             INTEGER,

  -- Rebound context
  rebound_type       TEXT,                     -- OFF, DEF, DEADBALL

  -- Foul context
  foul_type          TEXT,                     -- SHOOTING, OFFENSIVE, TECH
  free_throws_awarded INTEGER,

  -- Turnover context
  turnover_type      TEXT,                     -- BAD_PASS, TRAVEL, OUT_OF_BOUNDS

  -- Substitution context
  player_in_id       INTEGER,
  player_out_id      INTEGER,

  -- Score context
  home_score         INTEGER,
  away_score         INTEGER,
  score_margin       INTEGER,

  -- Metadata
  team_id            INTEGER
  description        TEXT,
  source_event_id    TEXT,
  created_at         TIMESTAMP DEFAULT now(),

  PRIMARY KEY (game_id, event_num)
);

