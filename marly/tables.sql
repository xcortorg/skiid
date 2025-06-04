CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;


CREATE TABLE IF NOT EXISTS api_keys (
    user_id bigint,
    key text
);

CREATE TABLE IF NOT EXISTS settings (
    guild_id BIGINT NOT NULL,
    prefix TEXT NOT NULL DEFAULT ',',
    mod_log BIGINT DEFAULT NULL,
    booster_role_base_id BIGINT,
    booster_role_include_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    jail_channel BIGINT DEFAULT NULL,
    jail_role BIGINT DEFAULT NULL,
    mute_role BIGINT DEFAULT NULL,
    reaction_mute_role BIGINT DEFAULT NULL,
    ban_delete_days INTEGER DEFAULT 0,
    lock_role_id BIGINT,
    lock_ignore_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    log_ignore_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    image_mute_role_id BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    welcome_removal BOOLEAN NOT NULL DEFAULT FALSE,

    -- Channel invoke messages
    invoke_kick_message TEXT,
    invoke_ban_message TEXT,
    invoke_unban_message TEXT,
    invoke_timeout_message TEXT,
    invoke_untimeout_message TEXT,
    invoke_mute_message TEXT,
    invoke_unmute_message TEXT,
    invoke_softban_message TEXT,
    invoke_warn_message TEXT,
    invoke_tempban_message TEXT,
    invoke_hardban_message TEXT,
    invoke_jail_message TEXT,
    invoke_unjail_message TEXT,
    invoke_imute_message TEXT,
    invoke_iunmute_message TEXT,
    invoke_rmute_message TEXT,
    invoke_runmute_message TEXT,


    -- DM invoke messages
    invoke_kick_dm TEXT,
    invoke_ban_dm TEXT,
    invoke_unban_dm TEXT,
    invoke_timeout_dm TEXT,
    invoke_untimeout_dm TEXT,
    invoke_mute_dm TEXT,
    invoke_unmute_dm TEXT,
    invoke_softban_dm TEXT,
    invoke_warn_dm TEXT,
    invoke_tempban_dm TEXT,
    invoke_hardban_dm TEXT,
    invoke_jail_dm TEXT,
    invoke_unjail_dm TEXT,
    invoke_imute_dm TEXT,
    invoke_iunmute_dm TEXT,
    invoke_rmute_dm TEXT,
    invoke_runmute_dm TEXT,
    nuke_view TEXT DEFAULT NULL,
    invoke JSONB DEFAULT '{}'::JSONB,
    invoke_silent_mode BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS logging (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  events INTEGER NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

-- Server Settings


CREATE TABLE IF NOT EXISTS jailed (
    guild_id BIGINT,
    user_id BIGINT,
    jailed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS welcome_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  delete_after INTEGER,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS goodbye_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  delete_after INTEGER,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS boost_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  delete_after INTEGER,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS sticky_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS selfprefix (
    user_id BIGINT PRIMARY KEY,
    prefix TEXT
);

CREATE TABLE IF NOT EXISTS thread (
  guild_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, thread_id)
);

CREATE TABLE IF NOT EXISTS aliases (
    guild_id BIGINT,
    alias TEXT,
    command TEXT,
    invoke TEXT,
    PRIMARY KEY (guild_id, alias)
);


CREATE TABLE IF NOT EXISTS afk (
  user_id BIGINT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'AFK',
  left_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);


CREATE TABLE IF NOT EXISTS fake_permissions (
    guild_id BIGINT,
    role_id BIGINT,
    permission TEXT,
    PRIMARY KEY (guild_id, role_id, permission)
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

CREATE TABLE IF NOT EXISTS scheduled_nukes (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    interval TEXT NOT NULL,
    message TEXT,
    archive_pins BOOLEAN DEFAULT FALSE,
    next_nuke TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

--- Games and Etc

CREATE TABLE IF NOT EXISTS tictactoe_stats (
    user_id BIGINT PRIMARY KEY,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    games_played INTEGER DEFAULT 0
);


CREATE TABLE IF NOT EXISTS juul (
    guild_id BIGINT NOT NULL,
    user_id BIGINT,  -- Current holder of the juul
    puff_count INTEGER DEFAULT 0,
    flavor TEXT DEFAULT 'Cool Mint',
    is_enabled BOOLEAN DEFAULT TRUE,
    last_hit_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    stolen_count INTEGER DEFAULT 0,
    passed_count INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS juul_stats (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    total_hits INTEGER DEFAULT 0,
    times_stolen INTEGER DEFAULT 0,
    times_received INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);


CREATE TABLE IF NOT EXISTS blunts (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    puff_count INTEGER DEFAULT 0,
    strain TEXT DEFAULT 'OG Kush',
    last_hit_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS blunt_stats (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    total_hits INTEGER DEFAULT 0,
    blunts_shared INTEGER DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);


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

CREATE TABLE IF NOT EXISTS emoji_stats (
    guild_id BIGINT,
    emoji_id TEXT,
    uses BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, emoji_id)
);

CREATE TABLE IF NOT EXISTS command_usage (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    command_name TEXT NOT NULL,
    command_type TEXT NOT NULL,
    uses BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, command_name, command_type)
);

--- Commands-Specific
CREATE SCHEMA IF NOT EXISTS commands;

CREATE TABLE IF NOT EXISTS commands.ignored (
    guild_id BIGINT,
    target_id BIGINT,
    PRIMARY KEY (guild_id, target_id)
);

CREATE TABLE IF NOT EXISTS commands.disabled (
    guild_id BIGINT,
    channel_id BIGINT,
    command TEXT,
    PRIMARY KEY (guild_id, channel_id, command)
);

CREATE TABLE IF NOT EXISTS commands.restricted (
    guild_id BIGINT,
    role_id BIGINT,
    command TEXT,
    PRIMARY KEY (guild_id, role_id, command)
);



CREATE TABLE IF NOT EXISTS blacklist (
    user_id BIGINT,
    reason TEXT,
    PRIMARY KEY (user_id)   
);

CREATE TABLE IF NOT EXISTS auto_roles (
    guild_id BIGINT,
    role_id BIGINT,
    humans BOOLEAN DEFAULT FALSE,
    bots BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS auto_responses (
    guild_id BIGINT,
    trigger TEXT,
    response TEXT,
    self_destruct BIGINT,
    not_strict BOOLEAN DEFAULT FALSE,
    ignore_command_check BOOLEAN DEFAULT FALSE,
    reply BOOLEAN DEFAULT FALSE,
    delete BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (guild_id, trigger)
);


CREATE TABLE IF NOT EXISTS boost_messages (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    self_destruct INTEGER,
    PRIMARY KEY (guild_id, channel_id)
);



CREATE SCHEMA IF NOT EXISTS timer;

CREATE TABLE IF NOT EXISTS timer.nuke (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    interval INTERVAL NOT NULL,
    next_trigger TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS timer.task (
    id SERIAL PRIMARY KEY,
    event TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL DEFAULT '{}'::JSONB
);