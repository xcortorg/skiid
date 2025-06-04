CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS timescaledb;



CREATE TABLE IF NOT EXISTS payment (
  guild_id BIGINT UNIQUE NOT NULL,
  customer_id BIGINT NOT NULL,
  method TEXT NOT NULL,
  amount BIGINT NOT NULL,
  transfers INTEGER NOT NULL DEFAULT 0,
  paid_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS blacklist (
  user_id BIGINT UNIQUE NOT NULL,
  information TEXT,
  reason TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
  user_id BIGINT NOT NULL,
  message TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id)
);

CREATE TABLE IF NOT EXISTS webhook (
  identifier TEXT NOT NULL,
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  author_id BIGINT NOT NULL,
  webhook_id BIGINT NOT NULL,
  PRIMARY KEY (channel_id, webhook_id)
);

CREATE TABLE IF NOT EXISTS name_history (
  user_id BIGINT NOT NULL,
  username TEXT NOT NULL,
  is_nickname BOOLEAN NOT NULL DEFAULT FALSE,
  is_hidden BOOLEAN NOT NULL DEFAULT FALSE,
  changed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS afk (
  user_id BIGINT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'AFK',
  left_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS crypto (
  user_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  transaction_id TEXT NOT NULL,
  transaction_type TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (user_id, transaction_id)
);

CREATE TABLE IF NOT EXISTS highlights (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  word TEXT NOT NULl,
  PRIMARY KEY (guild_id, user_id, word)
);

CREATE SCHEMA IF NOT EXISTS lastfm;

CREATE TABLE IF NOT EXISTS lastfm.config (
    user_id BIGINT UNIQUE NOT NULL,
    username CITEXT NOT NULL,
    color BIGINT,
    command TEXT,
    reactions TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    embed_mode TEXT NOT NULL DEFAULT 'default',
    last_indexed TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lastfm.artists (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist),
    FOREIGN KEY (user_id) REFERENCES lastfm.config (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lastfm.albums (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    album CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist, album),
    FOREIGN KEY (user_id) REFERENCES lastfm.config (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lastfm.tracks (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    track CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist, track),
    FOREIGN KEY (user_id) REFERENCES lastfm.config (user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lastfm.crowns (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    artist CITEXT NOT NULL,
    claimed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, artist),
    FOREIGN KEY (user_id, artist) REFERENCES lastfm.artists (user_id, artist)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lastfm.hidden (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE SCHEMA IF NOT EXISTS reskin;

CREATE TABLE IF NOT EXISTS reskin.webhook (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  webhook_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS reskin.config (
  user_id BIGINT UNIQUE NOT NULL,
  username TEXT,
  avatar_url TEXT
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

CREATE SCHEMA IF NOT EXISTS ticket;

CREATE TABLE IF NOT EXISTS ticket.config (
  guild_id BIGINT UNIQUE NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  staff_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  blacklisted_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  channel_name TEXT
);

CREATE TABLE IF NOT EXISTS ticket.button (
  identifier TEXT NOT NULL,
  guild_id BIGINT NOT NULL,
  template TEXT,
  category_id BIGINT,
  topic TEXT,
  PRIMARY KEY (identifier, guild_id),
  FOREIGN KEY (guild_id) REFERENCES ticket.config (guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ticket.open (
  identifier TEXT NOT NULL,
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  PRIMARY KEY (identifier, guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS settings (
  guild_id BIGINT NOT NULL,
  prefix TEXT,
  reskin BOOLEAN NOT NULL DEFAULT FALSE,
  reposter_prefix BOOLEAN NOT NULL DEFAULT TRUE,
  reposter_delete BOOLEAN NOT NULL DEFAULT FALSE,
  reposter_embed BOOLEAN NOT NULL DEFAULT TRUE,
  transcription BOOLEAN NOT NULL DEFAULT FALSE,
  welcome_removal BOOLEAN NOT NULL DEFAULT FALSE,
  booster_role_base_id BIGINT,
  booster_role_include_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  lock_role_id BIGINT,
  lock_ignore_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  log_ignore_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  mod_log_channel_id BIGINT,
  reassign_ignore_ids BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  reassign_roles BOOLEAN NOT NULL DEFAULT FALSE,
  invoke_kick TEXT,
  invoke_ban TEXT,
  invoke_unban TEXT,
  invoke_timeout TEXT,
  invoke_untimeout TEXT,
  invoke_play TEXT,
  safesearch_level TEXT NOT NULL DEFAULT 'strict',
  play_panel BOOLEAN NOT NULL DEFAULT TRUE,
  play_deletion BOOLEAN NOT NULL DEFAULT FALSE,
  backup_task BOOLEAN NOT NULL DEFAULT FALSE,
  jail_channel_id BIGINT,
  jail_role_id BIGINT,
  PRIMARY KEY (guild_id)
);


CREATE TABLE IF NOT EXISTS member_roles (
    guild_id BIGINT,
    member_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, member_id, role_id)
);


CREATE TABLE IF NOT EXISTS economy (
    user_id BIGINT NOT NULL, 
    credits INTEGER NOT NULL, 
    bank INTEGER NOT NULL,
    daily TIMESTAMPTZ,
    monthly TIMESTAMPTZ,
    PRIMARY KEY (user_id)
);


CREATE TABLE IF NOT EXISTS jail (
  user_id BIGINT NOT NULL,
  guild_id BIGINT NOT NULL,
  moderator_id BIGINT NOT NULL,
  reason TEXT NOT NULL DEFAULT 'No reason provided',
  start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  end_time TIMESTAMP WITH TIME ZONE,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  previous_roles BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS selfprefix (
    user_id BIGINT PRIMARY KEY,
    prefix TEXT
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

CREATE TABLE IF NOT EXISTS donators (
    user_id BIGINT,
    PRIMARY KEY (user_id)
);


CREATE TABLE IF NOT EXISTS reminders (
    user_id BIGINT,
    text CITEXT,
    jump_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE,
    timestamp TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (user_id, timestamp)
);


CREATE TABLE IF NOT EXISTS antinuke (
  guild_id BIGINT UNIQUE NOT NULL,
  whitelist BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  trusted_admins BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
  "bot" BOOLEAN NOT NULL DEFAULT FALSE,
  "ban" JSONB,
  "kick" JSONB,
  "role" JSONB,
  "channel" JSONB,
  "webhook" JSONB,
  "emoji" JSONB
);

CREATE TABLE IF NOT EXISTS backup (
    key TEXT NOT NULL,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    "data" TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (key, guild_id)
);

CREATE TABLE IF NOT EXISTS quoter (
  guild_id BIGINT UNIQUE NOT NULL,
  channel_id BIGINT,
  emoji TEXT,
  embeds BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS whitelist (
  guild_id BIGINT UNIQUE NOT NULL,
  status BOOLEAN NOT NULL DEFAULT FALSE,
  action TEXT NOT NULL DEFAULT 'kick'
);

CREATE TABLE IF NOT EXISTS vanity_sniper (
  guild_id BIGINT UNIQUE NOT NULL,
  status BOOLEAN NOT NULL DEFAULT TRUE,
  channel_id BIGINT,
  vanities TEXT[] NOT NULL DEFAULT '{}'::TEXT[]
);

CREATE TABLE IF NOT EXISTS vanity (
  guild_id BIGINT UNIQUE NOT NULL,
  channel_id BIGINT,
  role_id BIGINT,
  template TEXT
);

CREATE TABLE IF NOT EXISTS antiraid (
  guild_id BIGINT NOT NULL,
  locked BOOLEAN NOT NULL DEFAULT FALSE,
  joins JSONB,
  mentions JSONB,
  avatar JSONB,
  browser JSONB,
  PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS aliases (
  guild_id BIGINT NOT NULL,
  name TEXT NOT NULL,
  invoke TEXT NOT NULL,
  command TEXT NOT NULL,
  PRIMARY KEY (guild_id, name)
);

CREATE TABLE IF NOT EXISTS logging (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  events INTEGER NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS starboard (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  self_star BOOLEAN NOT NULL DEFAULT TRUE,
  threshold INTEGER NOT NULL DEFAULT 3,
  emoji TEXT NOT NULL DEFAULT '⭐',
  PRIMARY KEY (guild_id, emoji)
);

CREATE TABLE IF NOT EXISTS starboard_entry (
  guild_id BIGINT NOT NULL,
  star_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  emoji TEXT NOT NULL,
  PRIMARY KEY (guild_id, channel_id, message_id, emoji),
  FOREIGN KEY (guild_id, emoji) REFERENCES starboard (guild_id, emoji) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS booster_role (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS boosters_lost (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  lasted_for INTERVAL NOT NULL,
  ended_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS counter (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  option TEXT NOT NULL,
  last_update TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  rate_limited_until TIMESTAMP WITH TIME ZONE,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS gallery (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS auto_role (
  guild_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  action TEXT NOT NULL,
  delay INTEGER,
  PRIMARY KEY (guild_id, role_id, action)
);

CREATE TABLE IF NOT EXISTS reaction_role (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  emoji TEXT NOT NULL,
  PRIMARY KEY (guild_id, message_id, emoji)
);

CREATE TABLE IF NOT EXISTS reaction_trigger (
  guild_id BIGINT NOT NULL,
  trigger CITEXT NOT NULL,
  emoji TEXT NOT NULL,
  PRIMARY KEY (guild_id, trigger, emoji)
);

CREATE TABLE IF NOT EXISTS response_trigger (
  guild_id BIGINT NOT NULL,
  trigger CITEXT NOT NULL,
  template TEXT NOT NULL,
  strict BOOLEAN NOT NULL DEFAULT FALSE,
  reply BOOLEAN NOT NULL DEFAULT FALSE,
  delete BOOLEAN NOT NULL DEFAULT FALSE,
  delete_after INTEGER NOT NULL DEFAULT 0,
  role_id BIGINT,
  PRIMARY KEY (guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS thread (
  guild_id BIGINT NOT NULL,
  thread_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, thread_id)
);

CREATE TABLE IF NOT EXISTS publisher (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE SCHEMA IF NOT EXISTS timer;

CREATE TABLE IF NOT EXISTS timer.message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  interval INTEGER NOT NULL,
  next_trigger TIMESTAMP WITH TIME ZONE NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS timer.purge (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  interval INTEGER NOT NULL,
  next_trigger TIMESTAMP WITH TIME ZONE NOT NULL,
  method TEXT NOT NULL DEFAULT 'bulk',
  PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS sticky_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  template TEXT NOT NULL,
  PRIMARY KEY (guild_id, channel_id)
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

CREATE TABLE IF NOT EXISTS giveaway (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  prize TEXT NOT NULL,
  emoji TEXT NOT NULL,
  winners INTEGER NOT NULL,
  ended BOOLEAN NOT NULL DEFAULT FALSE,
  ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS disboard;

CREATE TABLE IF NOT EXISTS disboard.config (
  guild_id BIGINT UNIQUE NOT NULL,
  status BOOLEAN NOT NULL DEFAULT TRUE,
  channel_id BIGINT,
  last_channel_id BIGINT,
  last_user_id BIGINT,
  message TEXT,
  thank_message TEXT,
  next_bump TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS disboard.bump (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  bumped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS level;

CREATE TABLE IF NOT EXISTS level.config (
  guild_id BIGINT UNIQUE NOT NULL,
  status BOOLEAN NOT NULL DEFAULT TRUE,
  cooldown INTEGER NOT NULL DEFAULT 60,
  max_level INTEGER NOT NULL DEFAULT 0,
  stack_roles BOOLEAN NOT NULL DEFAULT TRUE,
  formula_multiplier FLOAT NOT NULL DEFAULT 1,
  xp_multiplier FLOAT NOT NULL DEFAULT 1,
  xp_min INTEGER NOT NULL DEFAULT 15,
  xp_max INTEGER NOT NULL DEFAULT 40,
  effort_status BOOLEAN NOT NULL DEFAULT FALSE,
  effort_text BIGINT NOT NULL DEFAULT 25,
  effort_image BIGINT NOT NULL DEFAULT 3,
  effort_booster BIGINT NOT NULL DEFAULT 10,
  FOREIGN KEY (guild_id) REFERENCES settings (guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS level.role (
  guild_id BIGINT NOT NULL,
  role_id BIGINT  UNIQUE NOT NULL,
  level INTEGER NOT NULL,
  PRIMARY KEY (guild_id, level),
  FOREIGN KEY (guild_id) REFERENCES level.config (guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS level.notification (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT,
  dm BOOLEAN NOT NULL DEFAULT FALSE,
  template TEXT,
  PRIMARY KEY (guild_id),
  FOREIGN KEY (guild_id) REFERENCES level.config (guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS level.member (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  level INTEGER NOT NULL DEFAULT 0,
  total_xp INTEGER NOT NULL DEFAULT 0,
  last_message TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  PRIMARY KEY (guild_id, user_id),
  FOREIGN KEY (guild_id) REFERENCES level.config (guild_id) ON DELETE CASCADE
);

CREATE SCHEMA IF NOT EXISTS reposters;

CREATE TABLE IF NOT EXISTS reposters.disabled (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  reposter TEXT NOT NULL,
  PRIMARY KEY (guild_id, channel_id, reposter)
);

CREATE SCHEMA IF NOT EXISTS commands;

CREATE TABLE IF NOT EXISTS commands.disabled (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  command TEXT NOT NULL,
  PRIMARY KEY (guild_id, channel_id, command)
);

CREATE TABLE IF NOT EXISTS commands.restricted (
  guild_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL,
  command TEXT NOT NULL,
  PRIMARY KEY (guild_id, role_id, command)
);

CREATE TABLE IF NOT EXISTS commands.ignore (
  guild_id BIGINT NOT NULL,
  target_id BIGINT NOT NULL,
  PRIMARY KEY (guild_id, target_id)
);

CREATE TABLE IF NOT EXISTS commands.usage (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  command TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- VoiceMaster
CREATE SCHEMA IF NOT EXISTS voice;

CREATE TABLE IF NOT EXISTS voice.config (
    guild_id BIGINT UNIQUE NOT NULL,
    category_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    bitrate INTEGER,
    name TEXT,
    status TEXT
);

CREATE TABLE IF NOT EXISTS voice.channels (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    PRIMARY KEY (guild_id, channel_id)
);

-- Audio
CREATE SCHEMA IF NOT EXISTS audio;

CREATE TABLE IF NOT EXISTS audio.config (
  guild_id BIGINT UNIQUE NOT NULL,
  volume INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS audio.statistics (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  tracks_played INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS roleplay (
    user_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, target_id, category)
);

CREATE TABLE IF NOT EXISTS birthdays (
    user_id BIGINT UNIQUE NOT NULL,
    birthday TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id)  -- Ensure user_id is the primary key
);

CREATE TABLE IF NOT EXISTS user_settings (
    user_id BIGINT PRIMARY KEY,  -- Discord user ID
    sunsign VARCHAR(50) NOT NULL  -- Zodiac sign
);

CREATE TABLE IF NOT EXISTS timezones (
    user_id BIGINT UNIQUE NOT NULL,
    timezone TEXT NOT NULL
);

CREATE SCHEMA IF NOT EXISTS fortnite;

CREATE TABLE IF NOT EXISTS fortnite.authorization (
    user_id BIGINT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    account_id TEXT NOT NULL,
    access_token TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    refresh_token TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fortnite.reminder (
    user_id BIGINT NOT NULL,
    item_id TEXT NOT NULL,
    item_name TEXT NOT NULL,
    item_type TEXT NOT NULL,
    PRIMARY KEY (user_id, item_id)
);

CREATE TABLE IF NOT EXISTS fortnite.rotation (
    guild_id BIGINT UNIQUE NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT
);

CREATE TABLE IF NOT EXISTS pubsub (
    id TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE SCHEMA IF NOT EXISTS feeds;

CREATE TABLE IF NOT EXISTS feeds.twitter (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    twitter_id BIGINT NOT NULL,
    twitter_name TEXT NOT NULL,
    template TEXT,
    color TEXT,
    PRIMARY KEY (guild_id, twitter_id)
);


CREATE TABLE IF NOT EXISTS feeds.tiktok (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    tiktok_id BIGINT NOT NULL,
    tiktok_name TEXT NOT NULL,
    template TEXT,
    PRIMARY KEY (guild_id, tiktok_id)
);

CREATE TABLE IF NOT EXISTS feeds.instagram (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    instagram_id BIGINT NOT NULL,
    instagram_name TEXT NOT NULL,
    template TEXT,
    PRIMARY KEY (guild_id, instagram_id)
);

CREATE TABLE IF NOT EXISTS feeds.youtube (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    youtube_id TEXT NOT NULL,
    youtube_name TEXT NOT NULL,
    template TEXT,
    shorts BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (guild_id, youtube_id)
);

CREATE TABLE IF NOT EXISTS feeds.reddit (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    subreddit_name TEXT NOT NULL,
    PRIMARY KEY (guild_id, subreddit_name)
);

CREATE TABLE IF NOT EXISTS feeds.pinterest (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    pinterest_id TEXT NOT NULL,
    pinterest_name TEXT NOT NULL,
    board TEXT,
    board_id TEXT,
    embeds BOOLEAN NOT NULL DEFAULT TRUE,
    only_new BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (guild_id, pinterest_id)
);

CREATE TABLE IF NOT EXISTS feeds.soundcloud (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    soundcloud_id BIGINT NOT NULL,
    soundcloud_name TEXT NOT NULL,
    template TEXT,
    PRIMARY KEY (guild_id, soundcloud_id)
);

CREATE SCHEMA IF NOT EXISTS alerts;

CREATE TABLE IF NOT EXISTS alerts.twitch (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    twitch_id BIGINT NOT NULL,
    twitch_login TEXT NOT NULL,
    last_stream_id BIGINT,
    role_id BIGINT,
    template TEXT,
    PRIMARY KEY (guild_id, twitch_id)
);

CREATE TABLE IF NOT EXISTS blunt (
    guild_id BIGINT,
    user_id BIGINT,
    hits BIGINT  DEFAULT 0,
    passes BIGINT  DEFAULT 0,
    members JSONB[]  DEFAULT '{}'::JSONB[],
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS roleplay (
    user_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    category TEXT NOT NULL,
    amount INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, target_id, category)
);

CREATE TABLE IF NOT EXISTS vape (
    user_id BIGINT PRIMARY KEY,
    flavor TEXT,
    hits BIGINT NOT NULL DEFAULT 0
);


CREATE SCHEMA IF NOT EXISTS metrics;

CREATE TABLE IF NOT EXISTS metrics.names (
    user_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    pomelo BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS metrics.avatars (
    user_id BIGINT NOT NULL,
    asset TEXT NOT NULL,
    key TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS cases (
    id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    message_id BIGINT,
    reason TEXT NOT NULL DEFAULT 'No reason provided',
    "action" BIGINT NOT NULL DEFAULT 0,
    action_expiration TIMESTAMP WITH TIME ZONE,
    action_processed BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id, guild_id)
);

CREATE OR REPLACE FUNCTION NEXT_CASE(BIGINT) RETURNS BIGINT
    LANGUAGE plpgsql
    AS $$
DECLARE
    next_id BIGINT;
BEGIN
    SELECT MAX(id) INTO next_id FROM cases WHERE guild_id = $1;
    IF next_id IS NULL THEN RETURN 1; END IF;
    RETURN next_id + 1;
END;
$$;
