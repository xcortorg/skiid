CREATE TABLE IF NOT EXISTS donors (
    user_id BIGINT PRIMARY KEY,
    is_donor BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS vape (
    user_id BIGINT PRIMARY KEY,
    flavor TEXT,
    hits INT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS voicemaster (
    guild_id BIGINT PRIMARY KEY,         
    category_id BIGINT,                   
    interface_id BIGINT,                  
    create_channel_id BIGINT                 
);
CREATE TABLE IF NOT EXISTS vc_owners (
    channel_id BIGINT PRIMARY KEY,          
    owner_id BIGINT                         
);
CREATE TABLE IF NOT EXISTS blacklist (
    user_id TEXT PRIMARY KEY,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS user_timezones (
    user_id BIGINT PRIMARY KEY,
    timezone TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sniped_messages (
    message_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    content TEXT NOT NULL,
    deleted_at TIMESTAMP NOT NULL
);
CREATE TABLE IF NOT EXISTS pinterest_feeds (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS economy (
    user_id BIGINT PRIMARY KEY,
    balance BIGINT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cooldowns (
    user_id BIGINT PRIMARY KEY,
    last_command_timestamp BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS name_history (
    user_id BIGINT NOT NULL,
    username TEXT,
    display_name TEXT,
    timestamp TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, timestamp)
);
CREATE TABLE IF NOT EXISTS daily (
    user_id BIGINT PRIMARY KEY,
    last_daily_claim TIMESTAMP
);
CREATE TABLE IF NOT EXISTS prefixes (
    user_id BIGINT PRIMARY KEY,
    prefix TEXT NOT NULL
);
