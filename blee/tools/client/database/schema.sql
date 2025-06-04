--- GLOBAL --- 
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;


CREATE TABLE IF NOT EXISTS donators (
    user_id BIGINT,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS traceback (
    error_id TEXT,
    command TEXT,
    guild_id BIGINT,
    channel_id BIGINT,
    user_id BIGINT,
    traceback TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (error_id)
);


--- Servers

CREATE TABLE IF NOT EXISTS settings (
    guild_id BIGINT UNIQUE,
    prefix TEXT  DEFAULT ',',
    baserole BIGINT DEFAULT NULL,
    voicemaster JSONB  DEFAULT '{}'::JSONB,
    mod_log BIGINT DEFAULT NULL,
    invoke JSONB  DEFAULT '{}'::JSONB,
    lock_ignore JSONB[]  DEFAULT '{}'::JSONB[],
    reskin JSONB  DEFAULT '{}'::JSONB,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS sticky_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message_id BIGINT,
    message TEXT,
    schedule TEXT,
    PRIMARY KEY (guild_id, channel_id, message_id)
);

CREATE TABLE IF NOT EXISTS auto_roles (
    guild_id BIGINT,
    role_id BIGINT,
    humans BOOLEAN DEFAULT FALSE,
    bots BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS join_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS selfprefix (
    user_id BIGINT PRIMARY KEY,
    prefix TEXT
);

CREATE TABLE IF NOT EXISTS afk (
    user_id BIGINT,
    message TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS aliases (
    guild_id BIGINT,
    alias TEXT,
    command TEXT,
    invoke TEXT,
    PRIMARY KEY (guild_id, alias)
);

--- Moderation
CREATE TABLE IF NOT EXISTS cases (
    guild_id BIGINT,
    case_id BIGINT,
    case_type TEXT,
    message_id BIGINT,
    moderator_id BIGINT,
    target_id BIGINT,
    moderator TEXT,
    target TEXT,
    reason TEXT,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (guild_id, case_id)
);


CREATE TABLE IF NOT EXISTS leave_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS boost_messages (
    guild_id BIGINT,
    channel_id BIGINT,
    message TEXT,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id)
);


CREATE TABLE IF NOT EXISTS booster_roles (
    guild_id BIGINT,
    user_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, user_id)
);


--- Snipe

CREATE SCHEMA IF NOT EXISTS snipe;

CREATE TABLE IF NOT EXISTS snipe.filter (
  guild_id BIGINT UNIQUE NOT NULL,
  invites BOOLEAN NOT NULL DEFAULT FALSE,
  links BOOLEAN NOT NULL DEFAULT FALSE,
  words TEXT[] NOT NULL DEFAULT '{}'::TEXT[]
);

CREATE TABLE IF NOT EXISTS snipe.ignore (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, user_id)
);

--- Users

CREATE TABLE IF NOT EXISTS name_history (
  user_id BIGINT NOT NULL,
  username TEXT NOT NULL,
  is_nickname BOOLEAN NOT NULL DEFAULT FALSE,
  is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
  changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tictactoe_stats (
    user_id BIGINT PRIMARY KEY,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fake_permissions (
    guild_id BIGINT,
    role_id BIGINT,
    permission TEXT,
    PRIMARY KEY (guild_id, role_id, permission)
);


CREATE TABLE IF NOT EXISTS emoji_stats (
    guild_id BIGINT,
    emoji_id TEXT,
    uses BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, emoji_id)
);


--- VoiceMaster
CREATE SCHEMA IF NOT EXISTS voicemaster;

CREATE TABLE IF NOT EXISTS voicemaster.configuration (
    guild_id BIGINT UNIQUE,
    category_id BIGINT,
    interface_id BIGINT,
    channel_id BIGINT,
    role_id BIGINT,
    region TEXT,
    bitrate BIGINT,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS voicemaster.channels (
    guild_id BIGINT,
    channel_id BIGINT,
    owner_id BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);