CREATE TABLE IF NOT EXISTS welcome (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS goodbye (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS boost (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT,
    message TEXT
);

CREATE TABLE IF NOT EXISTS autorole (
    guild_id BIGINT PRIMARY KEY,
    role_id BIGINT
);

CREATE TABLE IF NOT EXISTS vanity (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS username (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS skullboard (
    guild_id BIGINT PRIMARY KEY,
    emoji TEXT DEFAULT '💀',
    channel_id BIGINT,
    reaction_count INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pingonjoin (
    guild_id BIGINT,
    channel_id BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS autorespond (
    guild_id BIGINT NOT NULL,
    trigger TEXT NOT NULL,
    response TEXT,
    PRIMARY KEY (guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS autoreact (
    guild_id BIGINT NOT NULL,
    trigger TEXT NOT NULL,
    emoji TEXT,
    PRIMARY KEY (guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS invoke (
    guild_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    message TEXT,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS joindm (
    guild_id BIGINT PRIMARY KEY,
    message TEXT
);

CREATE TABLE IF NOT EXISTS reactionroles (
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji TEXT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, message_id, emoji)
);

CREATE TABLE IF NOT EXISTS prefixes (
    user_id TEXT PRIMARY KEY,
    prefix TEXT
);

CREATE TABLE IF NOT EXISTS blacklist (
    user_id TEXT PRIMARY KEY,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS errors (
    error_id TEXT PRIMARY KEY,
    error_message TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vanityroles (
    guild_id BIGINT PRIMARY KEY,  
    enabled BOOLEAN DEFAULT FALSE, 
    text VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS vanityroles_roles (
    guild_id BIGINT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, role_id),
    FOREIGN KEY (guild_id) REFERENCES vanityroles(guild_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS voicemaster (
    guild_id BIGINT PRIMARY KEY,
    category_id BIGINT,
    interface_id BIGINT,
    create_channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS voicemaster_owners (
    channel_id BIGINT PRIMARY KEY,
    owner_id BIGINT
);

CREATE TABLE IF NOT EXISTS automod (
    guild_id BIGINT NOT NULL,
    word TEXT NOT NULL,
    PRIMARY KEY (guild_id, word)
);

CREATE TABLE IF NOT EXISTS antilink (
    guild_id BIGINT NOT NULL,
    pattern TEXT NOT NULL,
    PRIMARY KEY (guild_id, pattern)
);

CREATE TABLE IF NOT EXISTS uids (
    user_id BIGINT PRIMARY KEY,
    uid SERIAL UNIQUE
);

CREATE TABLE IF NOT EXISTS userinfo (
    user_id BIGINT PRIMARY KEY,
    name TEXT,
    footer TEXT,
    bio TEXT
);

CREATE TABLE IF NOT EXISTS antinuke (
    guild_id BIGINT PRIMARY KEY,
    channeldelete INTEGER,
    channelcreate INTEGER,
    roledelete INTEGER,
    rolecreate INTEGER,
    roleupdate INTEGER,
    webhookcreate INTEGER,
    ban INTEGER,
    kick INTEGER,
    punishment VARCHAR(4),
    log BIGINT
);

CREATE TABLE IF NOT EXISTS antinuke_admins (
    guild_id BIGINT,
    user_id BIGINT,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS antinuke_logs (
    logid SERIAL PRIMARY KEY,
    guild_id BIGINT,
    user_id BIGINT,
    action_type VARCHAR(50), 
    timestamp TIMESTAMP,
    details TEXT
);

CREATE TABLE IF NOT EXISTS lastfm ( 
    user_id BIGINT PRIMARY KEY,
    username TEXT 
);

CREATE TABLE IF NOT EXISTS timezone (
    user_id BIGINT PRIMARY KEY,
    timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vape (
    user_id BIGINT PRIMARY KEY,
    flavor TEXT,
    hits INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS autopfp (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT
);
