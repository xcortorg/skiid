CREATE TABLE IF NOT EXISTS prefix (
  guild_id BIGINT NOT NULL,
  prefix TEXT NOT NULL,
  PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS selfprefix (
  user_id BIGINT NOT NULL,
  prefix TEXT NOT NULL,
  PRIMARY KEY(user_id)
);

CREATE TABLE IF NOT EXISTS fakeperms (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    permissions TEXT[] NOT NULL,
    PRIMARY KEY(guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS blacklist (
  id BIGINT NOT NULL,
  type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS autorole (
  guild_id BIGINT NOT NULL,
  role_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS pingonjoin (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS autoresponder (
  guild_id BIGINT NOT NULL,
  trigger TEXT NOT NULL,
  response TEXT NOT NULL,
  PRIMARY KEY(guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS warns (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  time TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS donor (
  user_id BIGINT NOT NULL,
  time INTEGER NOT NULL,
  reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS welcome (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message TEXT NOT NULL,
  PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS leave (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message TEXT NOT NULL,
  PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS starboard (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT,
  count INTEGER,
  emoji TEXT,
  PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS starboard_message (
  guild_id BIGINT NOT NULL,
  channel_id BIGINT NOT NULL,
  message_id BIGINT NOT NULL,
  panel_message_id BIGINT NOT NULL,
  PRIMARY KEY(guild_id, channel_id, message_id)
);

CREATE TABLE IF NOT EXISTS disablecmd (
  guild_id BIGINT NOT NULL,
  command TEXT
);

CREATE TABLE IF NOT EXISTS forcenick (
  guild_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  nickname TEXT,
  PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS filter (
  guild_id BIGINT NOT NULL,
  module TEXT NOT NULL,
  rule_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS reskin (
  user_id BIGINT NOT NULL,
  username TEXT,
  avatar_url TEXT,
  PRIMARY KEY(user_id)
);

CREATE TABLE IF NOT EXISTS antinuke (
  guild_id BIGINT NOT NULL,
  modules TEXT DEFAULT '{}',
  admins BIGINT[] DEFAULT '{}',
  whitelisted BIGINT[] DEFAULT '{}',
  logs BIGINT,
  PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS aliases (
  guild_id BIGINT NOT NULL,
  alias TEXT NOT NULL,
  command TEXT NOT NULL,
  PRIMARY KEY(guild_id, alias)
);