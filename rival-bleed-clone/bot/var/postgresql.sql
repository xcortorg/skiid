CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE IF NOT EXISTS starboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '⭐'::text NOT NULL,
    ts boolean DEFAULT NULL,
    lock boolean DEFAULT NULL, 
    jump boolean DEFAULT NULL,
    self_star boolean DEFAULT NULL,
    attachments boolean DEFAULT NULL,
    color text DEFAULT NULL,
    ignore_entries bytea DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS timezones (
    user_id BIGINT NOT NULL UNIQUE,
    timezone TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sticky_roles (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, user_id, role_id)
);

CREATE TABLE IF NOT EXISTS silenced (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS forcenick (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    nickname TEXT NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS button_roles (
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    emoji TEXT,
    label TEXT,
    style TEXT,
    index INT NOT NULL
);

CREATE TABLE IF NOT EXISTS antiraid (
    guild_id BIGINT NOT NULL UNIQUE,
    raid_status BOOLEAN DEFAULT FALSE,
    status BOOLEAN DEFAULT FALSE,
    raid_triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    raid_expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    new_accounts BOOLEAN DEFAULT FALSE,
    new_account_threshold INT DEFAULT 7,
    new_account_punishment INT DEFAULT 1,
    joins BOOLEAN DEFAULT FALSE,
    join_threshold INT DEFAULT NULL,
    join_punishment INT DEFAULT 1,
    no_avatar BOOLEAN DEFAULT FALSE,
    no_avatar_punishment INT DEFAULT 1,
    whitelist BIGINT[] DEFAULT NULL,
    lock_channels BOOLEAN DEFAULT FALSE,
    punish BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS giveaways (
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    winner_count INT DEFAULT 1,
    max_level INT DEFAULT 0,
    min_level INT DEFAULT 0,
    min_stay INT DEFAULT 0,
    prize TEXT,
    rewarded_roles BIGINT[] DEFAULT NULL,
    required_roles BIGINT[] DEFAULT NULL,
    age INT DEFAULT 0,
    hosts BIGINT[] NOT NULL,
    expiration timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    entries BIGINT[],
    win_message_id BIGINT,
    PRIMARY KEY(guild_id, message_id, channel_id)
);

ALTER TABLE giveaways OWNER TO postgres;

CREATE TABLE IF NOT EXISTS instances (
    user_id BIGINT NOT NULL UNIQUE,
    token TEXT NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS bump_reminder (
    guild_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT NOT NULL,
    message TEXT,
    last_bump timestamp with time zone,
    thankyou_message TEXT,
    last_bump_user_id BIGINT,
    last_thankyou_message BIGINT,
    last_reminder BIGINT,
    reminded BOOLEAN DEFAULT FALSE,
    auto_clean BOOLEAN DEFAULT FALSE,
    auto_lock BOOLEAN DEFAULT FALSE
);

ALTER TABLE bump_reminder OWNER TO postgres;

CREATE TABLE IF NOT EXISTS server_embeds (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY(guild_id, name)
);

ALTER TABLE server_embeds OWNER TO postgres;

ALTER TABLE button_roles OWNER TO postgres;

CREATE TABLE IF NOT EXISTS command_usage (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    command_name text NOT NULL,
    command_type text NOT NULL,
    uses bigint DEFAULT 1,
    CONSTRAINT command_usage_command_type_check CHECK ((command_type = ANY (ARRAY['internal'::text, 'custom'::text])))
);

ALTER TABLE command_usage OWNER TO postgres;

CREATE TABLE IF NOT EXISTS fake_permissions (
    guild_id BIGINT NOT NULL,
    object_id BIGINT NOT NULL,
    object_type TEXT NOT NULL,
    permissions TEXT NOT NULL,
    created_by BIGINT NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY(guild_id, object_id)
);

ALTER TABLE fake_permissions OWNER TO postgres;

CREATE TABLE IF NOT EXISTS disabled_commands (
    guild_id bigint NOT NULL,
    command TEXT NOT NULL,
    object_ids bigint[],
    object_types text[],
    PRIMARY KEY(guild_id, command)
);

CREATE TABLE IF NOT EXISTS kick_notifications (
    guild_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    channels BIGINT[],
    message TEXT,
    PRIMARY KEY(guild_id, username)
);

CREATE TABLE IF NOT EXISTS youtube_notifications (
    guild_id BIGINT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    channels BIGINT[],
    message TEXT,
    PRIMARY KEY(guild_id, username)
);

ALTER TABLE kick_notifications OWNER TO postgres;

CREATE TABLE IF NOT EXISTS soundcloud_notifications (
    guild_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    channels BIGINT[],
    message TEXT,
    PRIMARY KEY(guild_id, username)
);

CREATE TABLE IF NOT EXISTS cases (
    guild_id BIGINT NOT NULL,
    case_id BIGINT NOT NULL,
    case_type TEXT NOT NULL,
    message_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    moderator TEXT,
    target TEXT, 
    reason TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (guild_id, case_id)
);

CREATE TABLE IF NOT EXISTS notes (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    note_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    note TEXT,
    PRIMARY KEY(guild_id, user_id, note_id)
);

CREATE TABLE IF NOT EXISTS hardban (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    moderator_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS temproles (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    expiration TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY(guild_id, user_id, role_id)
);

ALTER TABLE cases OWNER TO postgres;

ALTER TABLE soundcloud_notifications OWNER TO postgres;


CREATE TABLE IF NOT EXISTS jailed (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_ids BIGINT[],
    moderator_id BIGINT NOT NULL,
    reason TEXT NOT NULL,
    expiration timestamp with time zone,
    jailed_at timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS tempbans (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    moderator_id BIGINT NOT NULL,
    expiration timestamp with time zone,
    reason TEXT,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS auto_responders (
    guild_id BIGINT NOT NULL,
    trigger TEXT NOT NULL,
    response TEXT NOT NULL,
    strict BOOLEAN DEFAULT FALSE,
    reply BOOLEAN DEFAULT FALSE,
    self_destruct INT DEFAULT NULL,
    ignore_command_checks BOOLEAN DEFAULT FALSE,
    allowed_role_ids BIGINT[] DEFAULT NULL,
    denied_role_ids BIGINT[] DEFAULT NULL,
    allowed_channel_ids BIGINT[] DEFAULT NULL,
    denied_channel_ids BIGINT[] DEFAULT NULL,
    PRIMARY KEY(guild_id, trigger)
);

CREATE TABLE IF NOT EXISTS command_restrictions (
    guild_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, command, role_id)
);

CREATE TABLE IF NOT EXISTS command_allowed (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    PRIMARY KEY(guild_id, user_id, command)
);

CREATE TABLE IF NOT EXISTS auto_reactions (
    guild_id BIGINT NOT NULL,
    trigger TEXT NOT NULL,
    response TEXT[] NOT NULL,
    owner_id BIGINT,
    strict BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(guild_id, trigger, response)
);

ALTER TABLE disabled_commands OWNER TO postgres;

CREATE TABLE IF NOT EXISTS moderation_statistics (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    data text,
    PRIMARY KEY(guild_id, user_id)
);


CREATE TABLE IF NOT EXISTS image_only (
    guild_id BIGINT,
    channel_id BIGINT,
    PRIMARY KEY(guild_id, channel_id)
);

ALTER TABLE image_only OWNER TO postgres;

CREATE TABLE IF NOT EXISTS aliases (
    guild_id BIGINT NOT NULL,
    command_name TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY(guild_id, alias)
);

ALTER TABLE aliases OWNER TO postgres;

CREATE TABLE IF NOT EXISTS sticky_message (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    code TEXT NOT NULL,
    last_message BIGINT,
    PRIMARY KEY(guild_id, channel_id)
);

ALTER TABLE sticky_message OWNER TO postgres;

CREATE TABLE IF NOT EXISTS invocation (
    guild_id BIGINT NOT NULL,
    command TEXT NOT NULL,
    message_code TEXT,
    dm_code TEXT,
    PRIMARY KEY(guild_id, command)
);

ALTER TABLE invocation OWNER TO postgres;

CREATE TABLE IF NOT EXISTS pagination (
    guild_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    creator_id BIGINT NOT NULL,
    pages TEXT[] NOT NULL,
    current_page BIGINT NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id, message_id, channel_id)
);

ALTER TABLE pagination OWNER TO postgres;


CREATE TABLE IF NOT EXISTS disabled_modules (
    guild_id BIGINT NOT NULL,
    module TEXT NOT NULL,
    channel_ids bigint[],
    PRIMARY KEY(guild_id, module)
);

ALTER TABLE disabled_modules OWNER TO postgres;

CREATE TABLE IF NOT EXISTS disabled_events (
    guild_id BIGINT NOT NULL,
    event TEXT NOT NULL,
    channel_ids bigint[],
    PRIMARY KEY(guild_id, event)
);

ALTER TABLE disabled_events OWNER TO postgres;


CREATE TABLE IF NOT EXISTS ignored (
    guild_id BIGINT NOT NULL,
    object_id BIGINT NOT NULL,
    object_type TEXT NOT NULL,
    PRIMARY KEY(guild_id, object_id)
);

ALTER TABLE ignored OWNER TO postgres;

CREATE TABLE IF NOT EXISTS pin_config (
    guild_id BIGINT NOT NULL UNIQUE,
    channel_id BIGINT,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    unpinning BOOLEAN NOT NULL DEFAULT FALSE
);

ALTER TABLE pin_config OWNER TO postgres;

ALTER TABLE ONLY command_usage
    ADD CONSTRAINT command_usage_pkey PRIMARY KEY (guild_id, user_id, command_name, command_type);


ALTER TABLE starboard OWNER TO postgres;

CREATE TABLE IF NOT EXISTS starboard_entries (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL,
    starboard_message_id bigint NOT NULL
);

CREATE TABLE IF NOT EXISTS color_roles (
    guild_id BIGINT NOT NULL UNIQUE,
    roles TEXT[]
);

ALTER TABLE authorizations ALTER COLUMN owner_id DROP NOT NULL;

ALTER TABLE authorizations ALTER COLUMN creator DROP NOT NULL;

CREATE TABLE IF NOT EXISTS authorizations (
    guild_id bigint NOT NULL,
    owner_id bigint,
    creator bigint,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    transfers INT NOT NULL DEFAULT 0,
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS blacklists (
    object_id BIGINT NOT NULL,
    object_type TEXT NOT NULL,
    creator BIGINT NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    reason TEXT,
    PRIMARY KEY(object_id, object_type)
);

CREATE TABLE IF NOT EXISTS donators (
    user_id BIGINT NOT NULL UNIQUE,
    creator BIGINT NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    expiration timestamp with time zone
);

ALTER TABLE starboard_entries OWNER TO postgres;

CREATE TABLE IF NOT EXISTS self_prefix (
    user_id bigint NOT NULL PRIMARY KEY,
    prefix TEXT DEFAULT NULL
);

ALTER TABLE self_prefix OWNER TO postgres;


CREATE TABLE IF NOT EXISTS clownboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '⭐'::text NOT NULL,
    ts boolean DEFAULT NULL,
    lock boolean DEFAULT NULL, 
    jump boolean DEFAULT NULL,
    self_clown boolean DEFAULT NULL,
    attachments boolean DEFAULT NULL,
    color text DEFAULT NULL,
    ignore_entries bytea DEFAULT NULL
);

ALTER TABLE clownboard OWNER TO postgres;

CREATE TABLE IF NOT EXISTS names (
    user_id bigint NOT NULL,
    type text NOT NULL,
    username text NOT NULL,
    ts timestamp without time zone NOT NULL,
    PRIMARY KEY(user_id, type, username, ts)
);

ALTER TABLE names OWNER TO postgres;

CREATE TABLE IF NOT EXISTS guild_names (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    ts timestamp without time zone NOT NULL,
    PRIMARY KEY(guild_id, name, ts)
);

ALTER TABLE guild_names OWNER TO postgres;

CREATE TABLE IF NOT EXISTS reaction_history (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    reaction text NOT NULL,
    user_id bigint NOT NULL,
    ts timestamp with time zone DEFAULT now() NOT NULL,
    PRIMARY KEY(guild_id, channel_id, message_id, reaction, user_id)
);

ALTER TABLE reaction_history OWNER TO postgres;

CREATE TABLE IF NOT EXISTS clownboard_entries (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL,
    clownboard_message_id bigint NOT NULL
);


ALTER TABLE clownboard_entries OWNER TO postgres;

CREATE TABLE IF NOT EXISTS timer (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    interval text NOT NULL,
    msg TEXT NOT NULL,
    PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS counters (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    counter_type TEXT NOT NULL,
    format TEXT DEFAULT NULL,
    PRIMARY KEY(guild_id, counter_type)
);

CREATE TABLE IF NOT EXISTS traceback (
    command text NOT NULL,
    error_code text NOT NULL,
    error_message text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    user_id bigint NOT NULL,
    content text NOT NULL,
    date timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE traceback OWNER TO postgres;


CREATE TABLE IF NOT EXISTS text_level_settings (
    guild_id bigint NOT NULL,
    roles bytea DEFAULT NULL,
    award_message text DEFAULT NULL,
    award_message_mode text DEFAULT NULL,
    channel_id bigint DEFAULT NULL,
    locked boolean DEFAULT NULL,
    multiplier float DEFAULT NULL,
    roles_stack boolean DEFAULT NULL,
    ignored bytea DEFAULT NULL,
    PRIMARY KEY(guild_id)
);


ALTER TABLE text_level_settings OWNER TO postgres;


CREATE TABLE IF NOT EXISTS text_levels (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    xp bigint NOT NULL,
    msgs bigint DEFAULT 0,
    messages_enabled boolean DEFAULT TRUE,
    last_level_up BIGINT DEFAULT 0,
    PRIMARY KEY(guild_id, user_id)
);


ALTER TABLE text_levels OWNER TO postgres;


CREATE TABLE IF NOT EXISTS logs (
    guild_id bigint NOT NULL UNIQUE,
    events TEXT[] NOT NULL,
    channel_ids BIGINT[] NOT NULL,
    webhooks TEXT[] NOT NULL,
    ignored BIGINT[]
);

CREATE TABLE IF NOT EXISTS config (
    guild_id bigint NOT NULL,
    auto_nick TEXT,
    auto_play BOOLEAN DEFAULT FALSE,
    jail_roles BOOLEAN DEFAULT TRUE,
    join_logs BIGINT,
    mod_logs BIGINT,
    ban_purge INT DEFAULT NULL,
    google_safety BOOLEAN,
    reposting BOOLEAN NOT NULL DEFAULT TRUE,
    staff_roles bigint[] DEFAULT NULL,
    jail_channel BIGINT,
    jail_message TEXT,
    colorme BOOLEAN NOT NULL DEFAULT FALSE,
    colorme_base BIGINT,
    lock_ignore JSONB[] NOT NULL DEFAULT '{}'::JSONB[],
    dj_role BIGINT,
    premium_role BIGINT,
    prefixes TEXT[],
    lastfm_reactions JSONB[] NOT NULL DEFAULT '{}'::JSONB[],
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS logging (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    messages TEXT NOT NULL,
    id TEXT NOT NULL,
    expiration BIGINT,
    PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS webhooks (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    id TEXT NOT NULL UNIQUE,
    name TEXT,
    url TEXT NOT NULL,
    created_by BIGINT NOT NULL
    message_ids BIGINT[],
);

CREATE TABLE IF NOT EXISTS trackers (
    guild_id BIGINT NOT NULL,
    tracker_type TEXT NOT NULL,
    channel_ids BIGINT[] NOT NULL,
    PRIMARY KEY(guild_id, tracker_type)
);


ALTER TABLE config OWNER TO postgres;


CREATE SCHEMA IF NOT EXISTS lastfm;

CREATE TABLE IF NOT EXISTS lastfm.config (
    user_id BIGINT UNIQUE NOT NULL,
    username TEXT NOT NULL,
    score BIGINT default 0,
    nowplaying_uses bigint NOT NULL default 0,
    color BIGINT,
    message TEXT,
    reactions JSONB[] NOT NULL DEFAULT ARRAY[]::JSONB[]
);

CREATE TABLE IF NOT EXISTS lastfm.favorites (
    user_id BIGINT NOT NULL,
    track TEXT NOT NULL,
    artist TEXT NOT NULL,
    album TEXT NOT NULL,
    PRIMARY KEY(user_id, track, artist, album)
);

CREATE TABLE IF NOT EXISTS lastfm.command_blacklist (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS lastfm.commands (
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    public boolean default FALSE,
    command TEXT NOT NULL,
    PRIMARY KEY(user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS lastfm.locations (
    track CITEXT NOT NULL,
    artist CITEXT NOT NULL,
    youtube TEXT,
    spotify TEXT,
    itunes TEXT,
    PRIMARY KEY(track, artist)
);

CREATE TABLE IF NOT EXISTS lastfm.artists (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist)
);

CREATE TABLE IF NOT EXISTS lastfm.albums (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    album CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist, album)
);

CREATE TABLE IF NOT EXISTS lastfm.tracks (
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    track CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (user_id, artist, track)
);

CREATE TABLE IF NOT EXISTS lastfm.crowns (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    artist CITEXT NOT NULL,
    plays BIGINT NOT NULL,
    PRIMARY KEY (guild_id, artist)
);

CREATE TABLE IF NOT EXISTS lastfm.hidden (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);


CREATE TABLE IF NOT EXISTS lastfm_data (
    user_id BIGINT NOT NULL,
    username TEXT,
    key TEXT,
    token TEXT,
    PRIMARY KEY(user_id)
);

CREATE TABLE IF NOT EXISTS lastfm.artist_avatars (
    artist CITEXT NOT NULL,
    image_url TEXT NOT NULL,
    PRIMARY KEY(artist)
);

ALTER TABLE lastfm_data OWNER TO postgres;


CREATE SCHEMA IF NOT EXISTS voicemaster;

CREATE TABLE IF NOT EXISTS voicemaster.configuration (
    guild_id BIGINT UNIQUE NOT NULL,
    category_id BIGINT NOT NULL,
    interface_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    role_id BIGINT,
    region TEXT,
    bitrate BIGINT
);

CREATE TABLE IF NOT EXISTS voicemaster.channels (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_roles (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS booster_roles (
    guild_id BIGINT NOT NULL,
    role_limit BIGINT DEFAULT NULL,
    base_id BIGINT DEFAULT NULL,
    award_id BIGINT DEFAULT NULL,
    PRIMARY KEY (guild_id)
);

ALTER TABLE custom_roles OWNER TO postgres;

ALTER TABLE booster_roles OWNER TO postgres;


CREATE TABLE IF NOT EXISTS join_messages (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS leave_messages (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS boost_messages (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message TEXT NOT NULL,
    self_destruct BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS boosters_lost (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expired_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS antinuke (
    guild_id BIGINT UNIQUE NOT NULL,
    whitelist BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    admins BIGINT[] NOT NULL DEFAULT '{}'::BIGINT[],
    botadd JSONB NOT NULL DEFAULT '{}'::JSONB,
    webhook JSONB NOT NULL DEFAULT '{}'::JSONB,
    emoji JSONB NOT NULL DEFAULT '{}'::JSONB,
    ban JSONB NOT NULL DEFAULT '{}'::JSONB,
    kick JSONB NOT NULL DEFAULT '{}'::JSONB,
    channel JSONB NOT NULL DEFAULT '{}'::JSONB,
    role JSONB NOT NULL DEFAULT '{}'::JSONB,
    permissions JSONB[] NOT NULL DEFAULT '{}'::JSONB[]
);


CREATE TABLE IF NOT EXISTS message_logs (
    id TEXT NOT NULL UNIQUE,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    messages JSONB[] NOT NULL DEFAULT '[]'::JSONB[],
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
);

CREATE TABLE IF NOT EXISTS afk (
    user_id BIGINT UNIQUE NOT NULL,
    status TEXT,
    date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auto_role (
    guild_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, role_id)
);

CREATE TABLE IF NOT EXISTS reaction_role (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    emoji TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, message_id, role_id)
);

CREATE SCHEMA IF NOT EXISTS feeds;

CREATE TABLE IF NOT EXISTS feeds.tiktok (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, username)
);

CREATE TABLE IF NOT EXISTS feeds.twitter (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    user_id BIGINT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, username)
);

CREATE TABLE IF NOT EXISTS feeds.youtube (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    youtube_id TEXT NOT NULL,
    youtube_name TEXT NOT NULL,
    PRIMARY KEY(guild_id, youtube_id)
);


CREATE TABLE IF NOT EXISTS feeds.instagram (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, username)
);

CREATE TABLE IF NOT EXISTS feeds.twitch (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, username)
);


CREATE TABLE IF NOT EXISTS feeds.kick (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    username TEXT NOT NULL,
    PRIMARY KEY(guild_id, channel_id, username)
);

CREATE SCHEMA IF NOT EXISTS moderation;

CREATE TABLE IF NOT EXISTS moderation.caps (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    threshold INT DEFAULT 100,
    exempt_roles BIGINT[],
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.links (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    exempt_roles BIGINT[],
    whitelist TEXT[] DEFAULT NULL,
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.emoji (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    threshold INT DEFAULT 10,
    exempt_roles BIGINT[],
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.spoilers (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    threshold INT DEFAULT 5,
    exempt_roles BIGINT[],
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.invites (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    exempt_roles BIGINT[],
    whitelist TEXT[] DEFAULT NULL,
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.mention (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    threshold INT DEFAULT 10,
    exempt_roles BIGINT[],
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.music (
    guild_id BIGINT NOT NULL,
    channel_ids BIGINT[],
    exempt_roles BIGINT[],
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id)
);

CREATE TABLE IF NOT EXISTS moderation.regex (
    guild_id BIGINT NOT NULL,
    regex TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'delete',
    PRIMARY KEY(guild_id, regex)
);

CREATE TABLE IF NOT EXISTS moderation.regex_exempt (
    guild_id BIGINT NOT NULL UNIQUE,
    exempt_roles BIGINT[]
);

CREATE TABLE IF NOT EXISTS tickets (
    guild_id BIGINT NOT NULL UNIQUE,
    open_embed TEXT,
    category_id BIGINT,
    logs BIGINT,
    support_id BIGINT,
    open_emoji TEXT,
    delete_emoji TEXT,
    message_id BIGINT
);

CREATE TABLE IF NOT EXISTS opened_tickets (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_topics (
    guild_id BIGINT,
    name TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS logging (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    messages TEXT NOT NULL,
    id TEXT NOT NULL,
    expiration BIGINT
);

CREATE TABLE IF NOT EXISTS tictactoe (
    user_id BIGINT NOT NULL UNIQUE,
    wins NUMERIC NOT NULL DEFAULT 0,
    losses NUMERIC NOT NULL DEFAULT 0,
    ties NUMERIC NOT NULL DEFAULT 0
);

CREATE SCHEMA IF NOT EXISTS roleplay;

CREATE TABLE IF NOT EXISTS roleplay.status (
    guild_id BIGINT NOT NULL UNIQUE,
    status BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS roleplay.actions (
    action TEXT NOT NULL,
    giver BIGINT NOT NULL,
    receiver BIGINT NOT NULL,
    amount NUMERIC NOT NULL DEFAULT 0,
    PRIMARY KEY(action, giver, receiver)
);

CREATE SCHEMA IF NOT EXISTS statistics;

CREATE TABLE IF NOT EXISTS statistics.guilds (
    guild_id BIGINT NOT NULL UNIQUE,
    total_messages NUMERIC NOT NULL DEFAULT 0,
    total_humans_messages NUMERIC NOT NULL DEFAULT 0,
    total_bots_messages NUMERIC NOT NULL DEFAULT 0,
    total_messages_members JSONB DEFAULT '{}'::jsonb,
    messages JSONB DEFAULT '{}'::jsonb,
    total_voice NUMERIC NOT NULL DEFAULT 0,
    total_humans_voice NUMERIC NOT NULL DEFAULT 0,
    total_bots_voice NUMERIC NOT NULL DEFAULT 0,
    total_voice_members JSONB DEFAULT '{}'::jsonb,
    voice JSONB DEFAULT '{}'::jsonb,
    first_track timestamp with time zone not null default now()
);


CREATE TABLE IF NOT EXISTS statistics.member_count (
    guild_id BIGINT NOT NULL UNIQUE,
    joins INT DEFAULT 0
);

CREATE SCHEMA IF NOT EXISTS roles;

CREATE TABLE IF NOT EXISTS roles.restore (
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    role_ids BIGINT[] NOT NULL,
    PRIMARY KEY(guild_id, user_id)
);

CREATE SCHEMA IF NOT EXISTS pokemon;

CREATE TABLE IF NOT EXISTS pokemon.users (
    user_id BIGINT NOT NULL UNIQUE,
    party JSONB,
    pokemon JSONB,
    inventory JSONB
);

CREATE TABLE IF NOT EXISTS pokemon.pokemon (
    name TEXT NOT NULL,
    data JSONB,
    dex_id BIGINT
);

CREATE TABLE IF NOT EXISTS pokemon.catches (
    name TEXT NOT NULL UNIQUE,
    times BIGINT,
    last_caught TEXT,
    catchers BYTEA
);

CREATE TABLE IF NOT EXISTS pokemon.moves (
    name TEXT NOT NULL,
    moves BYTEA
);

CREATE TABLE IF NOT EXISTS spotify (
    user_id BIGINT NOT NULL UNIQUE,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    expiration TIMESTAMP WITH TIME ZONE NOT NULL,
    default_device_id TEXT
);

CREATE TABLE IF NOT EXISTS marriage (
    first_user_id BIGINT NOT NULL,
    second_user_id BIGINT NOT NULL,
    marriage_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS nuke (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    last_nuke TIMESTAMP WITH TIME ZONE NOT NULL,
    nuke_threshold BIGINT NOT NULL,
    message TEXT,
    PRIMARY KEY(guild_id, channel_id) 
);
CREATE SCHEMA IF NOT EXISTS birthday;

CREATE TABLE IF NOT EXISTS birthday.users (
    user_id BIGINT NOT NULL UNIQUE,
    month INT NOT NULL,
    day INT NOT NULL 
);

CREATE TABLE IF NOT EXISTS birthday.servers (
    guild_id BIGINT NOT NULL UNIQUE,
    role_id BIGINT,
    role_ids BIGINT[],
    channel_id BIGINT
);

CREATE TABLE IF NOT EXISTS autopfp (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    categories TEXT[] NOT NULL,
    PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS autobanner (
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    categories TEXT[] NOT NULL,
    PRIMARY KEY(guild_id, channel_id)
);

CREATE TABLE IF NOT EXISTS pingonjoin (
    guild_id BIGINT NOT NULL UNIQUE.
    channel_ids BIGINT[] NOT NULL
);

CREATE TABLE IF NOT EXISTS subscribe (
    user_id BIGINT NOT NULL,
    txid TEXT NOT NULL,
    PRIMARY KEY(user_id, txid)
);