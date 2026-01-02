CREATE TABLE Player
(
    player_id INT PRIMARY KEY,
    player_full_name VARCHAR(256),
    player_first_name VARCHAR(256),
    player_last_name VARCHAR(256),
    player_is_active BOOLEAN
);

CREATE TABLE Team
(
    team_id INT PRIMARY KEY,
    team_full_name VARCHAR(256),
    team_abbreviation VARCHAR(256),
    team_nickname VARCHAR(256),
    team_city VARCHAR(256)
);

CREATE TABLE Game
(
    game_id INT PRIMARY KEY,
    season_id INT,
    home_team_id INT REFERENCES Team(team_id),
    away_team_id INT REFERENCES Team(team_id),
    game_date DATE,
    season_type TEXT
);

CREATE TABLE pbp_raw_event_shots (
  -- Identity
  game_id            BIGINT NOT NULL REFERENCES Game(game_id),
  event_num          INTEGER NOT NULL,    
  event_type         TEXT NOT NULL,  
  event_subtype      TEXT,     

  -- Game context
  season             INTEGER NOT NULL,
  home_score         INTEGER,
  away_score         INTEGER,
  season_type        TEXT NOT NULL,  
  period             INTEGER NOT NULL,
  clock              INTERVAL NOT NULL, 
  home_team_id       INTEGER REFERENCES Team(team_id),
  away_team_id       INTEGER REFERENCES Team(team_id),
  possession_team_id INTEGER,

  primary_player_id  INTEGER,  

  -- Shot context
  shot_x             INTEGER,                  
  shot_y             INTEGER,
  is_three           BOOLEAN,
  shot_made          BOOLEAN,
  points             INTEGER,

  created_at         TIMESTAMP DEFAULT now(),

  PRIMARY KEY (game_id, event_num)
);

