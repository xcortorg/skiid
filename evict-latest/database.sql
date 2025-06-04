--
-- PostgreSQL database dump
--

-- Dumped from database version 14.17 (Ubuntu 14.17-1.pgdg22.04+1)
-- Dumped by pg_dump version 14.17 (Ubuntu 14.17-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'SQL_ASCII';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: alerts; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA alerts;


ALTER SCHEMA alerts OWNER TO root;

--
-- Name: audio; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA audio;


ALTER SCHEMA audio OWNER TO root;

--
-- Name: auto; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA auto;


ALTER SCHEMA auto OWNER TO root;

--
-- Name: commands; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA commands;


ALTER SCHEMA commands OWNER TO root;

--
-- Name: counting; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA counting;


ALTER SCHEMA counting OWNER TO postgres;

--
-- Name: disboard; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA disboard;


ALTER SCHEMA disboard OWNER TO root;

--
-- Name: family; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA family;


ALTER SCHEMA family OWNER TO postgres;

--
-- Name: feeds; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA feeds;


ALTER SCHEMA feeds OWNER TO root;

--
-- Name: fortnite; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA fortnite;


ALTER SCHEMA fortnite OWNER TO root;

--
-- Name: fun; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA fun;


ALTER SCHEMA fun OWNER TO postgres;

--
-- Name: history; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA history;


ALTER SCHEMA history OWNER TO root;

--
-- Name: invoke_history; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA invoke_history;


ALTER SCHEMA invoke_history OWNER TO root;

--
-- Name: joindm; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA joindm;


ALTER SCHEMA joindm OWNER TO postgres;

--
-- Name: lastfm; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA lastfm;


ALTER SCHEMA lastfm OWNER TO root;

--
-- Name: level; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA level;


ALTER SCHEMA level OWNER TO root;

--
-- Name: music; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA music;


ALTER SCHEMA music OWNER TO root;

--
-- Name: porn; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA porn;


ALTER SCHEMA porn OWNER TO postgres;

--
-- Name: reposters; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA reposters;


ALTER SCHEMA reposters OWNER TO root;

--
-- Name: reskin; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA reskin;


ALTER SCHEMA reskin OWNER TO root;

--
-- Name: snipe; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA snipe;


ALTER SCHEMA snipe OWNER TO root;

--
-- Name: spam; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA spam;


ALTER SCHEMA spam OWNER TO postgres;

--
-- Name: statistics; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA statistics;


ALTER SCHEMA statistics OWNER TO root;

--
-- Name: stats; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA stats;


ALTER SCHEMA stats OWNER TO postgres;

--
-- Name: streaks; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA streaks;


ALTER SCHEMA streaks OWNER TO postgres;

--
-- Name: ticket; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA ticket;


ALTER SCHEMA ticket OWNER TO root;

--
-- Name: timer; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA timer;


ALTER SCHEMA timer OWNER TO root;

--
-- Name: track; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA track;


ALTER SCHEMA track OWNER TO root;

--
-- Name: transcribe; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA transcribe;


ALTER SCHEMA transcribe OWNER TO root;

--
-- Name: verification; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA verification;


ALTER SCHEMA verification OWNER TO root;

--
-- Name: voice; Type: SCHEMA; Schema: -; Owner: root
--

CREATE SCHEMA voice;


ALTER SCHEMA voice OWNER TO root;

--
-- Name: voicemaster; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA voicemaster;


ALTER SCHEMA voicemaster OWNER TO postgres;

--
-- Name: citext; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS citext WITH SCHEMA public;


--
-- Name: EXTENSION citext; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION citext IS 'data type for case-insensitive character strings';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: twitch; Type: TABLE; Schema: alerts; Owner: root
--

CREATE TABLE alerts.twitch (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    twitch_id bigint NOT NULL,
    twitch_login text NOT NULL,
    last_stream_id bigint,
    role_id bigint,
    template text
);


ALTER TABLE alerts.twitch OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: audio; Owner: root
--

CREATE TABLE audio.config (
    guild_id bigint NOT NULL,
    volume integer NOT NULL
);


ALTER TABLE audio.config OWNER TO root;

--
-- Name: playlist_tracks; Type: TABLE; Schema: audio; Owner: postgres
--

CREATE TABLE audio.playlist_tracks (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    playlist_url text NOT NULL,
    track_title text NOT NULL,
    track_uri text NOT NULL,
    track_author text NOT NULL,
    album_name text,
    artwork_url text,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE audio.playlist_tracks OWNER TO postgres;

--
-- Name: playlists; Type: TABLE; Schema: audio; Owner: postgres
--

CREATE TABLE audio.playlists (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    playlist_name text NOT NULL,
    playlist_url text NOT NULL,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    track_count integer NOT NULL
);


ALTER TABLE audio.playlists OWNER TO postgres;

--
-- Name: recently_played; Type: TABLE; Schema: audio; Owner: postgres
--

CREATE TABLE audio.recently_played (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    track_title text NOT NULL,
    track_uri text NOT NULL,
    track_author text NOT NULL,
    artwork_url text,
    played_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    playlist_name text,
    playlist_url text
);


ALTER TABLE audio.recently_played OWNER TO postgres;

--
-- Name: settings; Type: TABLE; Schema: audio; Owner: postgres
--

CREATE TABLE audio.settings (
    guild_id bigint NOT NULL,
    dj_role_id bigint,
    panel_channel_id bigint
);


ALTER TABLE audio.settings OWNER TO postgres;

--
-- Name: statistics; Type: TABLE; Schema: audio; Owner: root
--

CREATE TABLE audio.statistics (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    tracks_played integer DEFAULT 0 NOT NULL
);


ALTER TABLE audio.statistics OWNER TO root;

--
-- Name: media; Type: TABLE; Schema: auto; Owner: root
--

CREATE TABLE auto.media (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    type text NOT NULL,
    category text NOT NULL,
    CONSTRAINT media_type_check CHECK ((type = ANY (ARRAY['banner'::text, 'pfp'::text])))
);


ALTER TABLE auto.media OWNER TO root;

--
-- Name: media_id_seq; Type: SEQUENCE; Schema: auto; Owner: root
--

CREATE SEQUENCE auto.media_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE auto.media_id_seq OWNER TO root;

--
-- Name: media_id_seq; Type: SEQUENCE OWNED BY; Schema: auto; Owner: root
--

ALTER SEQUENCE auto.media_id_seq OWNED BY auto.media.id;


--
-- Name: disabled; Type: TABLE; Schema: commands; Owner: root
--

CREATE TABLE commands.disabled (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    command text NOT NULL
);


ALTER TABLE commands.disabled OWNER TO root;

--
-- Name: ignore; Type: TABLE; Schema: commands; Owner: root
--

CREATE TABLE commands.ignore (
    guild_id bigint NOT NULL,
    target_id bigint NOT NULL
);


ALTER TABLE commands.ignore OWNER TO root;

--
-- Name: restricted; Type: TABLE; Schema: commands; Owner: root
--

CREATE TABLE commands.restricted (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    command text NOT NULL
);


ALTER TABLE commands.restricted OWNER TO root;

--
-- Name: usage; Type: TABLE; Schema: commands; Owner: root
--

CREATE TABLE commands.usage (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    user_id bigint NOT NULL,
    command text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE commands.usage OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: counting; Owner: postgres
--

CREATE TABLE counting.config (
    guild_id bigint NOT NULL,
    channel_id bigint,
    current_count integer DEFAULT 0,
    high_score integer DEFAULT 0,
    safe_mode boolean DEFAULT false,
    allow_fails boolean DEFAULT false,
    last_user_id bigint,
    success_emoji text DEFAULT '✅'::text,
    fail_emoji text DEFAULT '❌'::text
);


ALTER TABLE counting.config OWNER TO postgres;

--
-- Name: bump; Type: TABLE; Schema: disboard; Owner: root
--

CREATE TABLE disboard.bump (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    bumped_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE disboard.bump OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: disboard; Owner: root
--

CREATE TABLE disboard.config (
    guild_id bigint NOT NULL,
    status boolean DEFAULT true NOT NULL,
    channel_id bigint,
    last_channel_id bigint,
    last_user_id bigint,
    message text,
    thank_message text,
    next_bump timestamp with time zone
);


ALTER TABLE disboard.config OWNER TO root;

--
-- Name: marriages; Type: TABLE; Schema: family; Owner: postgres
--

CREATE TABLE family.marriages (
    user_id bigint NOT NULL,
    partner_id bigint NOT NULL,
    marriage_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    active boolean DEFAULT true
);


ALTER TABLE family.marriages OWNER TO postgres;

--
-- Name: members; Type: TABLE; Schema: family; Owner: postgres
--

CREATE TABLE family.members (
    user_id bigint NOT NULL,
    related_id bigint NOT NULL,
    relationship text
);


ALTER TABLE family.members OWNER TO postgres;

--
-- Name: profiles; Type: TABLE; Schema: family; Owner: postgres
--

CREATE TABLE family.profiles (
    user_id bigint NOT NULL,
    bio text
);


ALTER TABLE family.profiles OWNER TO postgres;

--
-- Name: instagram; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.instagram (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    instagram_id bigint NOT NULL,
    instagram_name text NOT NULL,
    template text
);


ALTER TABLE feeds.instagram OWNER TO root;

--
-- Name: pinterest; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.pinterest (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    pinterest_id text NOT NULL,
    pinterest_name text NOT NULL,
    board text,
    board_id text,
    embeds boolean DEFAULT true NOT NULL,
    only_new boolean DEFAULT false NOT NULL
);


ALTER TABLE feeds.pinterest OWNER TO root;

--
-- Name: reddit; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.reddit (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    subreddit_name text NOT NULL
);


ALTER TABLE feeds.reddit OWNER TO root;

--
-- Name: soundcloud; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.soundcloud (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    soundcloud_id bigint NOT NULL,
    soundcloud_name text NOT NULL,
    template text
);


ALTER TABLE feeds.soundcloud OWNER TO root;

--
-- Name: tiktok; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.tiktok (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    tiktok_id bigint NOT NULL,
    tiktok_name text NOT NULL,
    template text
);


ALTER TABLE feeds.tiktok OWNER TO root;

--
-- Name: twitter; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.twitter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    twitter_id bigint NOT NULL,
    twitter_name text NOT NULL,
    template text,
    color text
);


ALTER TABLE feeds.twitter OWNER TO root;

--
-- Name: youtube; Type: TABLE; Schema: feeds; Owner: root
--

CREATE TABLE feeds.youtube (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    youtube_id text NOT NULL,
    youtube_name text NOT NULL,
    template text,
    shorts boolean DEFAULT false NOT NULL
);


ALTER TABLE feeds.youtube OWNER TO root;

--
-- Name: authorization; Type: TABLE; Schema: fortnite; Owner: root
--

CREATE TABLE fortnite."authorization" (
    user_id bigint NOT NULL,
    display_name text NOT NULL,
    account_id text NOT NULL,
    access_token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    refresh_token text NOT NULL
);


ALTER TABLE fortnite."authorization" OWNER TO root;

--
-- Name: reminder; Type: TABLE; Schema: fortnite; Owner: root
--

CREATE TABLE fortnite.reminder (
    user_id bigint NOT NULL,
    item_id text NOT NULL,
    item_name text NOT NULL,
    item_type text NOT NULL
);


ALTER TABLE fortnite.reminder OWNER TO root;

--
-- Name: rotation; Type: TABLE; Schema: fortnite; Owner: root
--

CREATE TABLE fortnite.rotation (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text
);


ALTER TABLE fortnite.rotation OWNER TO root;

--
-- Name: wyr_channels; Type: TABLE; Schema: fun; Owner: postgres
--

CREATE TABLE fun.wyr_channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    rating character varying(4) DEFAULT 'pg13'::character varying NOT NULL
);


ALTER TABLE fun.wyr_channels OWNER TO postgres;

--
-- Name: moderation; Type: TABLE; Schema: history; Owner: root
--

CREATE TABLE history.moderation (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    reason text NOT NULL,
    action text DEFAULT 'Unknown'::text NOT NULL,
    duration interval,
    guild_id bigint DEFAULT 0 NOT NULL,
    case_id integer DEFAULT 0 NOT NULL,
    role_id bigint
);


ALTER TABLE history.moderation OWNER TO root;

--
-- Name: moderation_id_seq; Type: SEQUENCE; Schema: history; Owner: root
--

CREATE SEQUENCE history.moderation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE history.moderation_id_seq OWNER TO root;

--
-- Name: moderation_id_seq; Type: SEQUENCE OWNED BY; Schema: history; Owner: root
--

ALTER SEQUENCE history.moderation_id_seq OWNED BY history.moderation.id;


--
-- Name: commands; Type: TABLE; Schema: invoke_history; Owner: root
--

CREATE TABLE invoke_history.commands (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    command_name text NOT NULL,
    category text NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    guild_id bigint NOT NULL
);


ALTER TABLE invoke_history.commands OWNER TO root;

--
-- Name: commands_id_seq; Type: SEQUENCE; Schema: invoke_history; Owner: root
--

CREATE SEQUENCE invoke_history.commands_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE invoke_history.commands_id_seq OWNER TO root;

--
-- Name: commands_id_seq; Type: SEQUENCE OWNED BY; Schema: invoke_history; Owner: root
--

ALTER SEQUENCE invoke_history.commands_id_seq OWNED BY invoke_history.commands.id;


--
-- Name: config; Type: TABLE; Schema: joindm; Owner: postgres
--

CREATE TABLE joindm.config (
    guild_id bigint NOT NULL,
    message text,
    enabled boolean DEFAULT false
);


ALTER TABLE joindm.config OWNER TO postgres;

--
-- Name: albums; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.albums (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    album public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.albums OWNER TO root;

--
-- Name: artists; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.artists (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.artists OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.config (
    user_id bigint NOT NULL,
    username public.citext NOT NULL,
    color bigint,
    command text,
    reactions text[] DEFAULT '{}'::text[] NOT NULL,
    embed_mode text DEFAULT 'default'::text NOT NULL,
    last_indexed timestamp with time zone DEFAULT now() NOT NULL,
    access_token text,
    web_authentication boolean DEFAULT false
);


ALTER TABLE lastfm.config OWNER TO root;

--
-- Name: crown_updates; Type: TABLE; Schema: lastfm; Owner: postgres
--

CREATE TABLE lastfm.crown_updates (
    guild_id bigint NOT NULL,
    last_update timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE lastfm.crown_updates OWNER TO postgres;

--
-- Name: crowns; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.crowns (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    artist public.citext NOT NULL,
    claimed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE lastfm.crowns OWNER TO root;

--
-- Name: hidden; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.hidden (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE lastfm.hidden OWNER TO root;

--
-- Name: tracks; Type: TABLE; Schema: lastfm; Owner: root
--

CREATE TABLE lastfm.tracks (
    user_id bigint NOT NULL,
    username text NOT NULL,
    artist public.citext NOT NULL,
    track public.citext NOT NULL,
    plays bigint NOT NULL
);


ALTER TABLE lastfm.tracks OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: level; Owner: root
--

CREATE TABLE level.config (
    guild_id bigint NOT NULL,
    status boolean DEFAULT true NOT NULL,
    cooldown integer DEFAULT 60 NOT NULL,
    max_level integer DEFAULT 0 NOT NULL,
    stack_roles boolean DEFAULT true NOT NULL,
    formula_multiplier double precision DEFAULT 1 NOT NULL,
    xp_multiplier double precision DEFAULT 1 NOT NULL,
    xp_min integer DEFAULT 15 NOT NULL,
    xp_max integer DEFAULT 40 NOT NULL,
    effort_status boolean DEFAULT false NOT NULL,
    effort_text bigint DEFAULT 25 NOT NULL,
    effort_image bigint DEFAULT 3 NOT NULL,
    effort_booster bigint DEFAULT 10 NOT NULL
);


ALTER TABLE level.config OWNER TO root;

--
-- Name: member; Type: TABLE; Schema: level; Owner: root
--

CREATE TABLE level.member (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    xp integer DEFAULT 0 NOT NULL,
    level integer DEFAULT 0 NOT NULL,
    total_xp integer DEFAULT 0 NOT NULL,
    last_message timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE level.member OWNER TO root;

--
-- Name: notification; Type: TABLE; Schema: level; Owner: root
--

CREATE TABLE level.notification (
    guild_id bigint NOT NULL,
    channel_id bigint,
    dm boolean DEFAULT false NOT NULL,
    template text
);


ALTER TABLE level.notification OWNER TO root;

--
-- Name: role; Type: TABLE; Schema: level; Owner: root
--

CREATE TABLE level.role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    level integer NOT NULL
);


ALTER TABLE level.role OWNER TO root;

--
-- Name: history; Type: TABLE; Schema: music; Owner: postgres
--

CREATE TABLE music.history (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    title text NOT NULL,
    artist text NOT NULL,
    duration integer NOT NULL,
    thumbnail text NOT NULL,
    uri text NOT NULL,
    played_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE music.history OWNER TO postgres;

--
-- Name: history_id_seq; Type: SEQUENCE; Schema: music; Owner: postgres
--

CREATE SEQUENCE music.history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE music.history_id_seq OWNER TO postgres;

--
-- Name: history_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: postgres
--

ALTER SEQUENCE music.history_id_seq OWNED BY music.history.id;


--
-- Name: playlist_tracks; Type: TABLE; Schema: music; Owner: postgres
--

CREATE TABLE music.playlist_tracks (
    id integer NOT NULL,
    playlist_id integer,
    title text NOT NULL,
    artist text NOT NULL,
    duration integer NOT NULL,
    thumbnail text NOT NULL,
    uri text NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    added_by bigint NOT NULL
);


ALTER TABLE music.playlist_tracks OWNER TO postgres;

--
-- Name: playlist_tracks_id_seq; Type: SEQUENCE; Schema: music; Owner: postgres
--

CREATE SEQUENCE music.playlist_tracks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE music.playlist_tracks_id_seq OWNER TO postgres;

--
-- Name: playlist_tracks_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: postgres
--

ALTER SEQUENCE music.playlist_tracks_id_seq OWNED BY music.playlist_tracks.id;


--
-- Name: playlists; Type: TABLE; Schema: music; Owner: postgres
--

CREATE TABLE music.playlists (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    name text NOT NULL,
    thumbnail text DEFAULT 'https://img.freepik.com/premium-photo/treble-clef-circle-musical-notes-black-background-design-3d-illustration_116124-10456.jpg?semt=ais'::text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE music.playlists OWNER TO postgres;

--
-- Name: playlists_id_seq; Type: SEQUENCE; Schema: music; Owner: postgres
--

CREATE SEQUENCE music.playlists_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE music.playlists_id_seq OWNER TO postgres;

--
-- Name: playlists_id_seq; Type: SEQUENCE OWNED BY; Schema: music; Owner: postgres
--

ALTER SEQUENCE music.playlists_id_seq OWNED BY music.playlists.id;


--
-- Name: config; Type: TABLE; Schema: porn; Owner: postgres
--

CREATE TABLE porn.config (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    webhook_id bigint NOT NULL,
    webhook_token text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    spoiler boolean DEFAULT false NOT NULL
);


ALTER TABLE porn.config OWNER TO postgres;

--
-- Name: access_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.access_tokens (
    user_id bigint NOT NULL,
    token text NOT NULL,
    created_at timestamp with time zone NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    discord_token text
);


ALTER TABLE public.access_tokens OWNER TO postgres;

--
-- Name: afk; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.afk (
    user_id bigint NOT NULL,
    status text DEFAULT 'AFK'::text NOT NULL,
    left_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.afk OWNER TO root;

--
-- Name: aliases; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.aliases (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    invoke text NOT NULL,
    command text NOT NULL
);


ALTER TABLE public.aliases OWNER TO root;

--
-- Name: antinuke; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.antinuke (
    guild_id bigint NOT NULL,
    whitelist bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    trusted_admins bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    bot boolean DEFAULT false NOT NULL,
    ban jsonb,
    kick jsonb,
    role jsonb,
    channel jsonb,
    webhook jsonb,
    emoji jsonb
);


ALTER TABLE public.antinuke OWNER TO root;

--
-- Name: antiraid; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.antiraid (
    guild_id bigint NOT NULL,
    locked boolean DEFAULT false NOT NULL,
    joins jsonb,
    mentions jsonb,
    avatar jsonb,
    browser jsonb
);


ALTER TABLE public.antiraid OWNER TO root;

--
-- Name: appeal_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appeal_config (
    guild_id bigint NOT NULL,
    appeal_server_id bigint,
    appeal_channel_id bigint,
    logs_channel_id bigint,
    questions jsonb DEFAULT '[{"long": false, "question": "Why were you punished?", "required": true}, {"long": true, "question": "Why should we accept your appeal?", "required": true}, {"long": true, "question": "What will you do differently?", "required": true}]'::jsonb,
    direct_appeal boolean DEFAULT false,
    bypass_roles bigint[] DEFAULT ARRAY[]::bigint[]
);


ALTER TABLE public.appeal_config OWNER TO postgres;

--
-- Name: appeal_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appeal_templates (
    guild_id bigint NOT NULL,
    name character varying(100) NOT NULL,
    response text
);


ALTER TABLE public.appeal_templates OWNER TO postgres;

--
-- Name: appeals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appeals (
    id bigint NOT NULL,
    guild_id bigint,
    user_id bigint,
    moderator_id bigint,
    action_type character varying(32),
    reason text,
    status character varying(16) DEFAULT 'pending'::character varying,
    flags text[],
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.appeals OWNER TO postgres;

--
-- Name: appeals_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.appeals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.appeals_id_seq OWNER TO postgres;

--
-- Name: appeals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.appeals_id_seq OWNED BY public.appeals.id;


--
-- Name: auto_role; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.auto_role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    action text NOT NULL,
    delay integer
);


ALTER TABLE public.auto_role OWNER TO root;

--
-- Name: autokick; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autokick (
    user_id bigint,
    guild_id bigint,
    reason text,
    author_id bigint
);


ALTER TABLE public.autokick OWNER TO postgres;

--
-- Name: avatar_current; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_current (
    user_id bigint NOT NULL,
    avatar_hash text NOT NULL,
    avatar_url text NOT NULL,
    last_updated timestamp without time zone DEFAULT now()
);


ALTER TABLE public.avatar_current OWNER TO postgres;

--
-- Name: avatar_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_history (
    user_id bigint NOT NULL,
    avatar_url text NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now(),
    deleted_at timestamp without time zone
);


ALTER TABLE public.avatar_history OWNER TO postgres;

--
-- Name: avatar_history_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_history_settings (
    user_id bigint NOT NULL,
    enabled boolean DEFAULT false
);


ALTER TABLE public.avatar_history_settings OWNER TO postgres;

--
-- Name: backup; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.backup (
    key text NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    data text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.backup OWNER TO root;

--
-- Name: beta_dashboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.beta_dashboard (
    user_id bigint NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    added_by bigint,
    notes text
);


ALTER TABLE public.beta_dashboard OWNER TO postgres;

--
-- Name: birthdays; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.birthdays (
    user_id bigint NOT NULL,
    birthday timestamp without time zone NOT NULL
);


ALTER TABLE public.birthdays OWNER TO root;

--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.blacklist (
    user_id bigint NOT NULL,
    information text
);


ALTER TABLE public.blacklist OWNER TO root;

--
-- Name: blunt; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blunt (
    guild_id bigint NOT NULL,
    user_id bigint,
    hits bigint DEFAULT 0,
    passes bigint DEFAULT 0,
    members jsonb[] DEFAULT '{}'::jsonb[]
);


ALTER TABLE public.blunt OWNER TO postgres;

--
-- Name: boost_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.boost_history (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    boost_count integer DEFAULT 0,
    first_boost_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_boost_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.boost_history OWNER TO postgres;

--
-- Name: boost_message; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.boost_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.boost_message OWNER TO root;

--
-- Name: booster_role; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.booster_role (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    role_id bigint NOT NULL,
    shared boolean,
    multi_boost_enabled boolean DEFAULT false
);


ALTER TABLE public.booster_role OWNER TO root;

--
-- Name: boosters_lost; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.boosters_lost (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    lasted_for interval NOT NULL,
    ended_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.boosters_lost OWNER TO root;

--
-- Name: business_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business_jobs (
    job_id integer NOT NULL,
    business_id bigint,
    "position" text,
    salary integer,
    slots integer DEFAULT 1,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description text
);


ALTER TABLE public.business_jobs OWNER TO postgres;

--
-- Name: business_jobs_job_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.business_jobs_job_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.business_jobs_job_id_seq OWNER TO postgres;

--
-- Name: business_jobs_job_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.business_jobs_job_id_seq OWNED BY public.business_jobs.job_id;


--
-- Name: business_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business_stats (
    business_id bigint NOT NULL,
    total_revenue bigint DEFAULT 0,
    total_expenses bigint DEFAULT 0
);


ALTER TABLE public.business_stats OWNER TO postgres;

--
-- Name: businesses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.businesses (
    business_id integer NOT NULL,
    owner_id bigint,
    name text,
    balance bigint DEFAULT 0,
    employee_limit integer DEFAULT 5,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    description text
);


ALTER TABLE public.businesses OWNER TO postgres;

--
-- Name: businesses_business_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.businesses_business_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.businesses_business_id_seq OWNER TO postgres;

--
-- Name: businesses_business_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.businesses_business_id_seq OWNED BY public.businesses.business_id;


--
-- Name: card_daily; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_daily (
    user_id bigint NOT NULL,
    last_claim timestamp without time zone
);


ALTER TABLE public.card_daily OWNER TO postgres;

--
-- Name: card_drop_channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_drop_channels (
    channel_id bigint NOT NULL,
    guild_id bigint,
    added_by bigint,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.card_drop_channels OWNER TO postgres;

--
-- Name: card_duels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_duels (
    duel_id integer NOT NULL,
    player1_id bigint,
    player2_id bigint,
    winner_id bigint,
    reward integer,
    played_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.card_duels OWNER TO postgres;

--
-- Name: card_duels_duel_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.card_duels_duel_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.card_duels_duel_id_seq OWNER TO postgres;

--
-- Name: card_duels_duel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.card_duels_duel_id_seq OWNED BY public.card_duels.duel_id;


--
-- Name: card_market; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_market (
    listing_id integer NOT NULL,
    seller_id bigint,
    card_id text,
    price integer,
    listed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.card_market OWNER TO postgres;

--
-- Name: card_market_listing_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.card_market_listing_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.card_market_listing_id_seq OWNER TO postgres;

--
-- Name: card_market_listing_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.card_market_listing_id_seq OWNED BY public.card_market.listing_id;


--
-- Name: card_packs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_packs (
    pack_id integer NOT NULL,
    name text NOT NULL,
    price integer NOT NULL,
    description text,
    rarity_weights jsonb
);


ALTER TABLE public.card_packs OWNER TO postgres;

--
-- Name: card_packs_pack_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.card_packs_pack_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.card_packs_pack_id_seq OWNER TO postgres;

--
-- Name: card_packs_pack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.card_packs_pack_id_seq OWNED BY public.card_packs.pack_id;


--
-- Name: card_recipes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_recipes (
    result_card_id integer,
    required_cards jsonb,
    cost integer
);


ALTER TABLE public.card_recipes OWNER TO postgres;

--
-- Name: card_sets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.card_sets (
    set_id integer NOT NULL,
    name text NOT NULL,
    price integer NOT NULL,
    description text,
    rarity_weights jsonb
);


ALTER TABLE public.card_sets OWNER TO postgres;

--
-- Name: card_sets_set_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.card_sets_set_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.card_sets_set_id_seq OWNER TO postgres;

--
-- Name: card_sets_set_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.card_sets_set_id_seq OWNED BY public.card_sets.set_id;


--
-- Name: cases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.cases (
    guild_id bigint,
    count integer
);


ALTER TABLE public.cases OWNER TO postgres;

--
-- Name: clownboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clownboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    self_clown boolean DEFAULT true NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '🤡'::text NOT NULL
);


ALTER TABLE public.clownboard OWNER TO postgres;

--
-- Name: clownboard_entry; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clownboard_entry (
    guild_id bigint NOT NULL,
    clown_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.clownboard_entry OWNER TO postgres;

--
-- Name: confess; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess (
    guild_id bigint,
    channel_id bigint,
    confession integer,
    upvote text DEFAULT '👍'::text,
    downvote text DEFAULT '👎'::text
);


ALTER TABLE public.confess OWNER TO postgres;

--
-- Name: confess_blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_blacklist (
    guild_id bigint NOT NULL,
    word text NOT NULL
);


ALTER TABLE public.confess_blacklist OWNER TO postgres;

--
-- Name: confess_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_members (
    guild_id bigint,
    user_id bigint,
    confession integer
);


ALTER TABLE public.confess_members OWNER TO postgres;

--
-- Name: confess_mute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_mute (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.confess_mute OWNER TO postgres;

--
-- Name: confess_replies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_replies (
    message_id bigint NOT NULL,
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL
);


ALTER TABLE public.confess_replies OWNER TO postgres;

--
-- Name: config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.config (
    guild_id bigint NOT NULL,
    prefix text DEFAULT ','::text,
    baserole bigint,
    voicemaster jsonb DEFAULT '{}'::jsonb,
    mod_log bigint,
    invoke jsonb DEFAULT '{}'::jsonb,
    lock_ignore jsonb[] DEFAULT '{}'::jsonb[],
    reskin jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.config OWNER TO postgres;

--
-- Name: contracts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.contracts (
    business_id bigint NOT NULL,
    employee_id bigint NOT NULL,
    salary integer,
    "position" text,
    can_hire boolean DEFAULT false,
    hired_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.contracts OWNER TO postgres;

--
-- Name: counter; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.counter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    option text NOT NULL,
    last_update timestamp with time zone DEFAULT now() NOT NULL,
    rate_limited_until timestamp with time zone
);


ALTER TABLE public.counter OWNER TO root;

--
-- Name: crypto; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.crypto (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    transaction_id text NOT NULL,
    transaction_type text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.crypto OWNER TO root;

--
-- Name: dalle_credits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.dalle_credits (
    user_id bigint NOT NULL,
    credits numeric(10,2) NOT NULL,
    last_reset timestamp without time zone NOT NULL
);


ALTER TABLE public.dalle_credits OWNER TO postgres;

--
-- Name: deck_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.deck_cards (
    deck_id integer NOT NULL,
    card_id text NOT NULL,
    quantity integer DEFAULT 1
);


ALTER TABLE public.deck_cards OWNER TO postgres;

--
-- Name: donators; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donators (
    user_id bigint
);


ALTER TABLE public.donators OWNER TO postgres;

--
-- Name: earnings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.earnings (
    user_id bigint NOT NULL,
    h0 double precision DEFAULT 0,
    h1 double precision DEFAULT 0,
    h2 double precision DEFAULT 0,
    h3 double precision DEFAULT 0,
    h4 double precision DEFAULT 0,
    h5 double precision DEFAULT 0,
    h6 double precision DEFAULT 0,
    h7 double precision DEFAULT 0,
    h8 double precision DEFAULT 0,
    h9 double precision DEFAULT 0,
    h10 double precision DEFAULT 0,
    h11 double precision DEFAULT 0,
    h12 double precision DEFAULT 0,
    h13 double precision DEFAULT 0,
    h14 double precision DEFAULT 0,
    h15 double precision DEFAULT 0,
    h16 double precision DEFAULT 0,
    h17 double precision DEFAULT 0,
    h18 double precision DEFAULT 0,
    h19 double precision DEFAULT 0,
    h20 double precision DEFAULT 0,
    h21 double precision DEFAULT 0,
    h22 double precision DEFAULT 0,
    h23 double precision DEFAULT 0
);


ALTER TABLE public.earnings OWNER TO postgres;

--
-- Name: economy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy (
    user_id bigint NOT NULL,
    wallet bigint DEFAULT 0,
    bank bigint DEFAULT 0,
    bank_capacity bigint DEFAULT 10000,
    gems integer DEFAULT 0,
    last_daily timestamp without time zone,
    daily_streak integer DEFAULT 0,
    last_interest timestamp without time zone
);


ALTER TABLE public.economy OWNER TO postgres;

--
-- Name: economy_roleshop; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_roleshop (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    price bigint,
    description text
);


ALTER TABLE public.economy_roleshop OWNER TO postgres;

--
-- Name: employee_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employee_stats (
    business_id bigint NOT NULL,
    employee_id bigint NOT NULL,
    work_count integer DEFAULT 0,
    total_earned bigint DEFAULT 0
);


ALTER TABLE public.employee_stats OWNER TO postgres;

--
-- Name: fake_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fake_permissions (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    permission text NOT NULL
);


ALTER TABLE public.fake_permissions OWNER TO postgres;

--
-- Name: forcenick; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.forcenick (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    nickname character varying(32)
);


ALTER TABLE public.forcenick OWNER TO postgres;

--
-- Name: gallery; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.gallery (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.gallery OWNER TO root;

--
-- Name: gambling_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gambling_history (
    game_id integer NOT NULL,
    user_id bigint,
    game_type text,
    bet_amount bigint,
    outcome text,
    profit_loss bigint,
    played_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.gambling_history OWNER TO postgres;

--
-- Name: gambling_history_game_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gambling_history_game_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gambling_history_game_id_seq OWNER TO postgres;

--
-- Name: gambling_history_game_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gambling_history_game_id_seq OWNED BY public.gambling_history.game_id;


--
-- Name: gift_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gift_logs (
    gift_id integer NOT NULL,
    sender_id bigint,
    receiver_id bigint,
    amount bigint,
    message text,
    sent_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.gift_logs OWNER TO postgres;

--
-- Name: gift_logs_gift_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.gift_logs_gift_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.gift_logs_gift_id_seq OWNER TO postgres;

--
-- Name: gift_logs_gift_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.gift_logs_gift_id_seq OWNED BY public.gift_logs.gift_id;


--
-- Name: giveaway; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.giveaway (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    prize text NOT NULL,
    emoji text NOT NULL,
    winners integer NOT NULL,
    ended boolean DEFAULT false NOT NULL,
    ends_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    required_roles bigint[] DEFAULT '{}'::bigint[],
    bonus_roles jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE public.giveaway OWNER TO root;

--
-- Name: giveaway_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.giveaway_settings (
    guild_id bigint NOT NULL,
    bonus_roles jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.giveaway_settings OWNER TO postgres;

--
-- Name: gnames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gnames (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    changed_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.gnames OWNER TO postgres;

--
-- Name: goodbye_message; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.goodbye_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.goodbye_message OWNER TO root;

--
-- Name: guild_verification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild_verification (
    guild_id bigint NOT NULL,
    level integer DEFAULT 1,
    kick_after integer,
    ratelimit integer,
    antialt boolean DEFAULT false,
    bypass_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    verified_role_id bigint,
    manual_verification boolean DEFAULT false,
    log_channel_id bigint,
    platform character varying(10) DEFAULT 'web'::character varying,
    verification_settings jsonb DEFAULT '{}'::jsonb,
    verification_channel_id bigint,
    prevent_vpn boolean DEFAULT false
);


ALTER TABLE public.guild_verification OWNER TO postgres;

--
-- Name: guildblacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guildblacklist (
    guild_id bigint NOT NULL,
    information text
);


ALTER TABLE public.guildblacklist OWNER TO postgres;

--
-- Name: hardban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hardban (
    user_id bigint,
    guild_id bigint
);


ALTER TABLE public.hardban OWNER TO postgres;

--
-- Name: highlights; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.highlights (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    word text NOT NULL
);


ALTER TABLE public.highlights OWNER TO root;

--
-- Name: immune; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.immune (
    guild_id bigint NOT NULL,
    entity_id bigint NOT NULL,
    role_id bigint,
    type character varying(10) NOT NULL
);


ALTER TABLE public.immune OWNER TO postgres;

--
-- Name: instances; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.instances (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    payment_id character varying(100) NOT NULL,
    amount numeric(10,2) NOT NULL,
    purchased_at timestamp without time zone NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    email character varying(255),
    CONSTRAINT check_status CHECK (((status)::text = ANY (ARRAY[('pending'::character varying)::text, ('active'::character varying)::text, ('deployed'::character varying)::text, ('suspended'::character varying)::text])))
);


ALTER TABLE public.instances OWNER TO postgres;

--
-- Name: instances_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.instances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.instances_id_seq OWNER TO postgres;

--
-- Name: instances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.instances_id_seq OWNED BY public.instances.id;


--
-- Name: invite_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invite_config (
    guild_id bigint NOT NULL,
    is_enabled boolean DEFAULT false,
    log_channel_id bigint,
    fake_join_threshold numeric(10,2) DEFAULT 7,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    account_age_requirement integer,
    server_age_requirement integer
);


ALTER TABLE public.invite_config OWNER TO postgres;

--
-- Name: invite_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invite_rewards (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    required_invites integer NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.invite_rewards OWNER TO postgres;

--
-- Name: invite_tracking; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invite_tracking (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    inviter_id bigint,
    invite_code text,
    uses integer DEFAULT 0,
    bonus_uses integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    left_at timestamp without time zone
);


ALTER TABLE public.invite_tracking OWNER TO postgres;

--
-- Name: jail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jail (
    guild_id bigint,
    user_id bigint,
    roles text
);


ALTER TABLE public.jail OWNER TO postgres;

--
-- Name: jaill; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jaill (
    guild_id bigint,
    channel_id bigint,
    jail_id bigint,
    role text,
    log_id bigint
);


ALTER TABLE public.jaill OWNER TO postgres;

--
-- Name: job_applications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.job_applications (
    application_id integer NOT NULL,
    job_id integer,
    applicant_id bigint,
    status text DEFAULT 'pending'::text,
    reviewed_by bigint,
    reviewed_at timestamp without time zone,
    applied_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.job_applications OWNER TO postgres;

--
-- Name: job_applications_application_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.job_applications_application_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.job_applications_application_id_seq OWNER TO postgres;

--
-- Name: job_applications_application_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.job_applications_application_id_seq OWNED BY public.job_applications.application_id;


--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    user_id bigint NOT NULL,
    current_job text,
    job_level integer DEFAULT 1,
    job_experience integer DEFAULT 0,
    last_work timestamp without time zone,
    employer_id bigint
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: logging; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.logging (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    events integer NOT NULL
);


ALTER TABLE public.logging OWNER TO root;

--
-- Name: logging_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logging_history (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint,
    event_type character varying(50) NOT NULL,
    content jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.logging_history OWNER TO postgres;

--
-- Name: logging_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.logging_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.logging_history_id_seq OWNER TO postgres;

--
-- Name: logging_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.logging_history_id_seq OWNED BY public.logging_history.id;


--
-- Name: lottery_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lottery_history (
    id integer NOT NULL,
    user_id bigint,
    pot_amount bigint,
    total_tickets bigint,
    winner_tickets bigint,
    won_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.lottery_history OWNER TO postgres;

--
-- Name: lottery_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.lottery_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.lottery_history_id_seq OWNER TO postgres;

--
-- Name: lottery_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.lottery_history_id_seq OWNED BY public.lottery_history.id;


--
-- Name: lovense_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lovense_config (
    guild_id bigint NOT NULL,
    is_enabled boolean DEFAULT false,
    log_channel_id bigint
);


ALTER TABLE public.lovense_config OWNER TO postgres;

--
-- Name: lovense_connections; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lovense_connections (
    token text NOT NULL,
    guild_id bigint,
    user_id bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.lovense_connections OWNER TO postgres;

--
-- Name: lovense_consent; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lovense_consent (
    user_id bigint NOT NULL,
    agreed boolean DEFAULT false,
    locked boolean DEFAULT false
);


ALTER TABLE public.lovense_consent OWNER TO postgres;

--
-- Name: lovense_devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lovense_devices (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    device_id text,
    device_type text,
    last_active timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.lovense_devices OWNER TO postgres;

--
-- Name: lovense_shares; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lovense_shares (
    guild_id bigint NOT NULL,
    owner_id bigint NOT NULL,
    target_id bigint NOT NULL,
    device_id text NOT NULL
);


ALTER TABLE public.lovense_shares OWNER TO postgres;

--
-- Name: mod; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mod (
    guild_id bigint NOT NULL,
    channel_id bigint,
    jail_id bigint,
    role_id bigint,
    dm_enabled boolean DEFAULT true,
    dm_ban boolean DEFAULT false,
    dm_kick boolean DEFAULT false,
    dm_mute boolean DEFAULT false,
    dm_unban boolean DEFAULT false,
    dm_jail boolean DEFAULT false,
    dm_unjail boolean DEFAULT false,
    dm_unmute boolean DEFAULT false,
    dm_warn boolean DEFAULT false,
    dm_timeout boolean DEFAULT false,
    dm_untimeout boolean DEFAULT false,
    roles text,
    user_id bigint,
    dm_antinuke_ban boolean,
    dm_antinuke_kick boolean,
    dm_antinuke_strip boolean,
    dm_antiraid_ban boolean,
    dm_antiraid_kick boolean,
    dm_antiraid_timeout boolean,
    dm_antiraid_strip boolean,
    dm_role_add boolean,
    dm_role_remove boolean
);


ALTER TABLE public.mod OWNER TO postgres;

--
-- Name: name_history; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.name_history (
    user_id bigint NOT NULL,
    username text NOT NULL,
    is_nickname boolean DEFAULT false NOT NULL,
    is_hidden boolean DEFAULT false NOT NULL,
    changed_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.name_history OWNER TO root;

--
-- Name: pet_adventures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pet_adventures (
    adventure_id integer NOT NULL,
    pet_id integer,
    start_time timestamp without time zone NOT NULL,
    end_time timestamp without time zone NOT NULL,
    adventure_type character varying(32) NOT NULL,
    completed boolean DEFAULT false
);


ALTER TABLE public.pet_adventures OWNER TO postgres;

--
-- Name: pet_adventures_adventure_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pet_adventures_adventure_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pet_adventures_adventure_id_seq OWNER TO postgres;

--
-- Name: pet_adventures_adventure_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pet_adventures_adventure_id_seq OWNED BY public.pet_adventures.adventure_id;


--
-- Name: pet_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pet_items (
    item_id integer NOT NULL,
    owner_id bigint NOT NULL,
    item_name character varying(64) NOT NULL,
    amount integer DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pet_items OWNER TO postgres;

--
-- Name: pet_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pet_items_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pet_items_item_id_seq OWNER TO postgres;

--
-- Name: pet_items_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pet_items_item_id_seq OWNED BY public.pet_items.item_id;


--
-- Name: pet_trades; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pet_trades (
    trade_id integer NOT NULL,
    pet1_id integer,
    pet2_id integer,
    user1_id bigint NOT NULL,
    user2_id bigint NOT NULL,
    trade_fee integer NOT NULL,
    trade_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pet_trades OWNER TO postgres;

--
-- Name: pet_trades_trade_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pet_trades_trade_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pet_trades_trade_id_seq OWNER TO postgres;

--
-- Name: pet_trades_trade_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pet_trades_trade_id_seq OWNED BY public.pet_trades.trade_id;


--
-- Name: pets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pets (
    pet_id integer NOT NULL,
    owner_id bigint NOT NULL,
    name character varying(32) NOT NULL,
    type character varying(32) NOT NULL,
    rarity character varying(16) NOT NULL,
    level integer DEFAULT 1,
    xp integer DEFAULT 0,
    health integer DEFAULT 100,
    happiness integer DEFAULT 100,
    hunger integer DEFAULT 100,
    active boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.pets OWNER TO postgres;

--
-- Name: pets_pet_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.pets_pet_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.pets_pet_id_seq OWNER TO postgres;

--
-- Name: pets_pet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.pets_pet_id_seq OWNED BY public.pets.pet_id;


--
-- Name: pingonjoin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pingonjoin (
    channel_id bigint,
    guild_id bigint
);


ALTER TABLE public.pingonjoin OWNER TO postgres;

--
-- Name: poll_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.poll_votes (
    vote_id uuid DEFAULT gen_random_uuid() NOT NULL,
    poll_id uuid,
    user_id bigint NOT NULL,
    choice_ids integer[] NOT NULL,
    voted_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.poll_votes OWNER TO postgres;

--
-- Name: polls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.polls (
    poll_id uuid DEFAULT gen_random_uuid() NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    creator_id bigint NOT NULL,
    title text NOT NULL,
    description text,
    choices jsonb NOT NULL,
    settings jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ends_at timestamp with time zone,
    is_active boolean DEFAULT true
);


ALTER TABLE public.polls OWNER TO postgres;

--
-- Name: prefix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prefix (
    guild_id bigint,
    prefix text
);


ALTER TABLE public.prefix OWNER TO postgres;

--
-- Name: publisher; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.publisher (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.publisher OWNER TO root;

--
-- Name: quoter; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.quoter (
    guild_id bigint NOT NULL,
    channel_id bigint,
    emoji text,
    embeds boolean DEFAULT true NOT NULL
);


ALTER TABLE public.quoter OWNER TO root;

--
-- Name: reaction_role; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.reaction_role (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    role_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.reaction_role OWNER TO root;

--
-- Name: reaction_trigger; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.reaction_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.reaction_trigger OWNER TO root;

--
-- Name: recordings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.recordings (
    id uuid NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    initiator_id bigint NOT NULL,
    started_at timestamp with time zone NOT NULL,
    ended_at timestamp with time zone,
    status text NOT NULL,
    file_path text
);


ALTER TABLE public.recordings OWNER TO postgres;

--
-- Name: reminders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reminders (
    user_id bigint NOT NULL,
    reminder text NOT NULL,
    remind_at timestamp with time zone NOT NULL,
    invoked_at timestamp with time zone NOT NULL,
    message_url text
);


ALTER TABLE public.reminders OWNER TO postgres;

--
-- Name: reskin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reskin (
    user_id bigint,
    toggled boolean,
    username text,
    avatar text
);


ALTER TABLE public.reskin OWNER TO postgres;

--
-- Name: response_trigger; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.response_trigger (
    guild_id bigint NOT NULL,
    trigger public.citext NOT NULL,
    template text NOT NULL,
    strict boolean DEFAULT false NOT NULL,
    reply boolean DEFAULT false NOT NULL,
    delete boolean DEFAULT false NOT NULL,
    delete_after integer DEFAULT 0 NOT NULL,
    role_id bigint,
    sticker_id bigint
);


ALTER TABLE public.response_trigger OWNER TO root;

--
-- Name: role_applications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role_applications (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    role_id text NOT NULL,
    status text DEFAULT 'pending'::text NOT NULL,
    display_name text NOT NULL,
    description text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    email text
);


ALTER TABLE public.role_applications OWNER TO postgres;

--
-- Name: role_applications_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.role_applications_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.role_applications_id_seq OWNER TO postgres;

--
-- Name: role_applications_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.role_applications_id_seq OWNED BY public.role_applications.id;


--
-- Name: role_shops; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.role_shops (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    price integer,
    description text,
    active boolean DEFAULT true
);


ALTER TABLE public.role_shops OWNER TO postgres;

--
-- Name: roleplay; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.roleplay (
    user_id bigint NOT NULL,
    target_id bigint NOT NULL,
    category text NOT NULL,
    amount integer DEFAULT 1 NOT NULL
);


ALTER TABLE public.roleplay OWNER TO root;

--
-- Name: roleplay_enabled; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roleplay_enabled (
    enabled boolean,
    guild_id bigint
);


ALTER TABLE public.roleplay_enabled OWNER TO postgres;

--
-- Name: selfprefix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.selfprefix (
    user_id bigint,
    prefix text
);


ALTER TABLE public.selfprefix OWNER TO postgres;

--
-- Name: settings; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.settings (
    guild_id bigint NOT NULL,
    prefixes text[] DEFAULT '{}'::text[] NOT NULL,
    reskin boolean DEFAULT false NOT NULL,
    reposter_prefix boolean DEFAULT true NOT NULL,
    reposter_delete boolean DEFAULT false NOT NULL,
    reposter_embed boolean DEFAULT true NOT NULL,
    transcription boolean DEFAULT false NOT NULL,
    welcome_removal boolean DEFAULT false NOT NULL,
    booster_role_base_id bigint,
    booster_role_include_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    lock_role_id bigint,
    lock_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    log_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    reassign_ignore_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    reassign_roles boolean DEFAULT false NOT NULL,
    invoke_kick text,
    invoke_ban text,
    invoke_unban text,
    invoke_timeout text,
    invoke_untimeout text,
    invoke_play text,
    play_panel boolean DEFAULT true NOT NULL,
    play_deletion boolean DEFAULT false NOT NULL,
    safesearch_level text DEFAULT 'strict'::text NOT NULL,
    author text
);


ALTER TABLE public.settings OWNER TO root;

--
-- Name: shop_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shop_items (
    item_id integer NOT NULL,
    name text,
    price integer,
    description text,
    effect_type text,
    effect_value double precision,
    duration integer,
    effect_description text,
    effect_example jsonb,
    stock integer DEFAULT '-1'::integer,
    max_quantity integer DEFAULT '-1'::integer,
    tradeable boolean DEFAULT true
);


ALTER TABLE public.shop_items OWNER TO postgres;

--
-- Name: shop_items_item_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.shop_items_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.shop_items_item_id_seq OWNER TO postgres;

--
-- Name: shop_items_item_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.shop_items_item_id_seq OWNED BY public.shop_items.item_id;


--
-- Name: shutup; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shutup (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.shutup OWNER TO postgres;

--
-- Name: social_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.social_links (
    user_id bigint NOT NULL,
    type character varying(32) NOT NULL,
    url text NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.social_links OWNER TO postgres;

--
-- Name: socials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socials (
    user_id bigint NOT NULL,
    bio text,
    background_url text,
    show_friends boolean DEFAULT true,
    show_activity boolean DEFAULT true,
    profile_color text DEFAULT 'linear'::text,
    glass_effect boolean DEFAULT false,
    discord_guild text,
    profile_image text,
    last_avatar text,
    last_background text,
    badges text[],
    audio_url text,
    audio_title text,
    click_text text DEFAULT 'Click to enter...'::text,
    click_enabled boolean DEFAULT false,
    linear_color text DEFAULT '#ffffff'::text,
    text_underline_color_type text DEFAULT 'linear'::text,
    text_underline_linear_color text,
    text_underline_gradient_name text,
    bold_text_color_type text DEFAULT 'linear'::text,
    bold_text_linear_color text,
    bold_text_gradient_name text,
    status_color_type text DEFAULT 'linear'::text,
    status_linear_color text,
    status_gradient_name text,
    bio_color_type text DEFAULT 'linear'::text,
    bio_linear_color text,
    bio_gradient_name text,
    social_icons_color_type text DEFAULT 'linear'::text,
    social_icons_linear_color text,
    social_icons_gradient_name text,
    domains jsonb DEFAULT '[]'::jsonb,
    verified_domains jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.socials OWNER TO postgres;

--
-- Name: socials_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socials_details (
    detail_id integer NOT NULL,
    user_id bigint NOT NULL,
    friends bigint NOT NULL,
    url text
);


ALTER TABLE public.socials_details OWNER TO postgres;

--
-- Name: socials_details_detail_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.socials_details_detail_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.socials_details_detail_id_seq OWNER TO postgres;

--
-- Name: socials_details_detail_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.socials_details_detail_id_seq OWNED BY public.socials_details.detail_id;


--
-- Name: socials_gradients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socials_gradients (
    user_id bigint NOT NULL,
    color text,
    "position" integer NOT NULL
);


ALTER TABLE public.socials_gradients OWNER TO postgres;

--
-- Name: socials_saved_colors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socials_saved_colors (
    user_id bigint NOT NULL,
    name text NOT NULL,
    color text,
    type text
);


ALTER TABLE public.socials_saved_colors OWNER TO postgres;

--
-- Name: socials_saved_gradients; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.socials_saved_gradients (
    user_id bigint NOT NULL,
    name text NOT NULL,
    color text,
    "position" integer NOT NULL
);


ALTER TABLE public.socials_saved_gradients OWNER TO postgres;

--
-- Name: starboard; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.starboard (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    self_star boolean DEFAULT true NOT NULL,
    threshold integer DEFAULT 3 NOT NULL,
    emoji text DEFAULT '⭐'::text NOT NULL,
    color integer
);


ALTER TABLE public.starboard OWNER TO root;

--
-- Name: starboard_entry; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.starboard_entry (
    guild_id bigint NOT NULL,
    star_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    emoji text NOT NULL
);


ALTER TABLE public.starboard_entry OWNER TO root;

--
-- Name: steal_disabled; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.steal_disabled (
    guild_id bigint NOT NULL
);


ALTER TABLE public.steal_disabled OWNER TO postgres;

--
-- Name: sticky_message; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.sticky_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    template text NOT NULL
);


ALTER TABLE public.sticky_message OWNER TO root;

--
-- Name: suggestion; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestion (
    channel_id bigint,
    guild_id bigint,
    author_id bigint,
    blacklisted_id bigint,
    suggestion_id integer,
    thread_enabled boolean DEFAULT false,
    anonymous_allowed boolean DEFAULT true,
    required_role_id bigint
);


ALTER TABLE public.suggestion OWNER TO postgres;

--
-- Name: suggestion_entries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestion_entries (
    guild_id bigint NOT NULL,
    message_id bigint NOT NULL,
    author_id bigint,
    suggestion_id integer,
    is_anonymous boolean DEFAULT false
);


ALTER TABLE public.suggestion_entries OWNER TO postgres;

--
-- Name: suggestion_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestion_votes (
    guild_id bigint,
    message_id bigint NOT NULL,
    user_id bigint NOT NULL,
    vote_type integer
);


ALTER TABLE public.suggestion_votes OWNER TO postgres;

--
-- Name: tag_aliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tag_aliases (
    guild_id bigint NOT NULL,
    alias text NOT NULL,
    original text
);


ALTER TABLE public.tag_aliases OWNER TO postgres;

--
-- Name: tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tags (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    owner_id bigint,
    template text,
    uses bigint DEFAULT 0,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    restricted_user bigint,
    restricted_role bigint
);


ALTER TABLE public.tags OWNER TO postgres;

--
-- Name: thread; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.thread (
    guild_id bigint NOT NULL,
    thread_id bigint NOT NULL
);


ALTER TABLE public.thread OWNER TO root;

--
-- Name: timezones; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.timezones (
    user_id bigint NOT NULL,
    timezone text NOT NULL
);


ALTER TABLE public.timezones OWNER TO root;

--
-- Name: tracker; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tracker (
    guild_id bigint NOT NULL,
    vanity_channel_id bigint,
    username_channel_id bigint
);


ALTER TABLE public.tracker OWNER TO postgres;

--
-- Name: transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.transactions (
    id integer NOT NULL,
    user_id bigint,
    amount bigint,
    action character varying(4),
    "timestamp" timestamp without time zone DEFAULT now()
);


ALTER TABLE public.transactions OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transactions_id_seq OWNER TO postgres;

--
-- Name: transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.transactions_id_seq OWNED BY public.transactions.id;


--
-- Name: translation_contributors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.translation_contributors (
    user_id bigint NOT NULL,
    language_code character varying(10) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.translation_contributors OWNER TO postgres;

--
-- Name: used_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.used_items (
    user_id bigint NOT NULL,
    item text NOT NULL,
    ts timestamp without time zone NOT NULL,
    expiration timestamp without time zone NOT NULL
);


ALTER TABLE public.used_items OWNER TO postgres;

--
-- Name: user_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_cards (
    user_id bigint NOT NULL,
    card_id text NOT NULL,
    quantity integer DEFAULT 1,
    obtained_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_cards OWNER TO postgres;

--
-- Name: user_decks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_decks (
    deck_id integer NOT NULL,
    user_id bigint,
    name text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_decks OWNER TO postgres;

--
-- Name: user_decks_deck_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_decks_deck_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_decks_deck_id_seq OWNER TO postgres;

--
-- Name: user_decks_deck_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_decks_deck_id_seq OWNED BY public.user_decks.deck_id;


--
-- Name: user_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_items (
    user_id bigint NOT NULL,
    item_id integer NOT NULL,
    quantity integer DEFAULT 0,
    expires_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_items OWNER TO postgres;

--
-- Name: user_links; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_links (
    user_id bigint NOT NULL,
    type character varying(32) NOT NULL,
    url text NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_links OWNER TO postgres;

--
-- Name: user_spotify; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_spotify (
    user_id bigint NOT NULL,
    access_token text,
    refresh_token text,
    token_expires_at timestamp without time zone,
    spotify_id text
);


ALTER TABLE public.user_spotify OWNER TO postgres;

--
-- Name: user_transactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_transactions (
    transaction_id integer NOT NULL,
    user_id bigint,
    type text,
    amount bigint,
    details jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_transactions OWNER TO postgres;

--
-- Name: user_transactions_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_transactions_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_transactions_transaction_id_seq OWNER TO postgres;

--
-- Name: user_transactions_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_transactions_transaction_id_seq OWNED BY public.user_transactions.transaction_id;


--
-- Name: user_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_votes (
    user_id bigint NOT NULL,
    last_vote_time timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.user_votes OWNER TO postgres;

--
-- Name: uwulock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.uwulock (
    guild_id bigint,
    user_id bigint
);


ALTER TABLE public.uwulock OWNER TO postgres;

--
-- Name: vanity; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.vanity (
    guild_id bigint NOT NULL,
    channel_id bigint,
    role_id bigint,
    template text
);


ALTER TABLE public.vanity OWNER TO root;

--
-- Name: vape; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vape (
    user_id bigint NOT NULL,
    flavor text,
    hits bigint DEFAULT 0 NOT NULL
);


ALTER TABLE public.vape OWNER TO postgres;

--
-- Name: verification_question_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.verification_question_sessions (
    session_token text NOT NULL,
    question_ids integer[] NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    requires_review boolean DEFAULT false
);


ALTER TABLE public.verification_question_sessions OWNER TO postgres;

--
-- Name: warn_actions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warn_actions (
    guild_id bigint NOT NULL,
    threshold integer NOT NULL,
    action text NOT NULL,
    duration integer
);


ALTER TABLE public.warn_actions OWNER TO postgres;

--
-- Name: webhook; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.webhook (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    webhook_id bigint NOT NULL
);


ALTER TABLE public.webhook OWNER TO root;

--
-- Name: welcome_message; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.welcome_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    delete_after integer
);


ALTER TABLE public.welcome_message OWNER TO root;

--
-- Name: whitelist; Type: TABLE; Schema: public; Owner: root
--

CREATE TABLE public.whitelist (
    guild_id bigint NOT NULL,
    status boolean DEFAULT false NOT NULL,
    action text DEFAULT 'kick'::text NOT NULL
);


ALTER TABLE public.whitelist OWNER TO root;

--
-- Name: disabled; Type: TABLE; Schema: reposters; Owner: root
--

CREATE TABLE reposters.disabled (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    reposter text NOT NULL
);


ALTER TABLE reposters.disabled OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: reskin; Owner: root
--

CREATE TABLE reskin.config (
    user_id bigint NOT NULL,
    username text,
    avatar_url text
);


ALTER TABLE reskin.config OWNER TO root;

--
-- Name: webhook; Type: TABLE; Schema: reskin; Owner: root
--

CREATE TABLE reskin.webhook (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    webhook_id bigint NOT NULL
);


ALTER TABLE reskin.webhook OWNER TO root;

--
-- Name: filter; Type: TABLE; Schema: snipe; Owner: root
--

CREATE TABLE snipe.filter (
    guild_id bigint NOT NULL,
    invites boolean DEFAULT false NOT NULL,
    links boolean DEFAULT false NOT NULL,
    words text[] DEFAULT '{}'::text[] NOT NULL
);


ALTER TABLE snipe.filter OWNER TO root;

--
-- Name: ignore; Type: TABLE; Schema: snipe; Owner: root
--

CREATE TABLE snipe.ignore (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE snipe.ignore OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: spam; Owner: postgres
--

CREATE TABLE spam.config (
    guild_id bigint NOT NULL,
    enabled boolean DEFAULT false,
    threshold integer DEFAULT 3,
    timeout_duration integer DEFAULT 300
);


ALTER TABLE spam.config OWNER TO postgres;

--
-- Name: exempt; Type: TABLE; Schema: spam; Owner: postgres
--

CREATE TABLE spam.exempt (
    guild_id bigint NOT NULL,
    entity_id bigint NOT NULL,
    type text
);


ALTER TABLE spam.exempt OWNER TO postgres;

--
-- Name: messages; Type: TABLE; Schema: spam; Owner: postgres
--

CREATE TABLE spam.messages (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    message_hash text NOT NULL,
    count integer DEFAULT 1
);


ALTER TABLE spam.messages OWNER TO postgres;

--
-- Name: daily; Type: TABLE; Schema: statistics; Owner: postgres
--

CREATE TABLE statistics.daily (
    guild_id bigint NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    member_id bigint NOT NULL,
    messages_sent integer DEFAULT 0,
    voice_minutes integer DEFAULT 0
);


ALTER TABLE statistics.daily OWNER TO postgres;

--
-- Name: daily_channels; Type: TABLE; Schema: statistics; Owner: postgres
--

CREATE TABLE statistics.daily_channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    date date DEFAULT CURRENT_DATE NOT NULL,
    messages_sent integer DEFAULT 0
);


ALTER TABLE statistics.daily_channels OWNER TO postgres;

--
-- Name: config; Type: TABLE; Schema: stats; Owner: postgres
--

CREATE TABLE stats.config (
    guild_id bigint NOT NULL,
    min_word_length integer DEFAULT 3,
    count_bots boolean DEFAULT false,
    channel_whitelist bigint[],
    channel_blacklist bigint[]
);


ALTER TABLE stats.config OWNER TO postgres;

--
-- Name: custom_commands; Type: TABLE; Schema: stats; Owner: postgres
--

CREATE TABLE stats.custom_commands (
    guild_id bigint NOT NULL,
    command text NOT NULL,
    word text,
    created_by bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE stats.custom_commands OWNER TO postgres;

--
-- Name: ignored_words; Type: TABLE; Schema: stats; Owner: postgres
--

CREATE TABLE stats.ignored_words (
    guild_id bigint NOT NULL,
    word text NOT NULL,
    added_by bigint NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE stats.ignored_words OWNER TO postgres;

--
-- Name: word_usage; Type: TABLE; Schema: stats; Owner: postgres
--

CREATE TABLE stats.word_usage (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    word text NOT NULL,
    count integer DEFAULT 1,
    last_used timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE stats.word_usage OWNER TO postgres;

--
-- Name: config; Type: TABLE; Schema: streaks; Owner: postgres
--

CREATE TABLE streaks.config (
    guild_id bigint NOT NULL,
    channel_id bigint,
    notification_channel_id bigint,
    streak_emoji text DEFAULT '🔥'::text,
    image_only boolean DEFAULT false
);


ALTER TABLE streaks.config OWNER TO postgres;

--
-- Name: restore_log; Type: TABLE; Schema: streaks; Owner: postgres
--

CREATE TABLE streaks.restore_log (
    id integer NOT NULL,
    guild_id bigint,
    user_id bigint,
    restored_by text,
    restored_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    previous_streak integer
);


ALTER TABLE streaks.restore_log OWNER TO postgres;

--
-- Name: restore_log_id_seq; Type: SEQUENCE; Schema: streaks; Owner: postgres
--

CREATE SEQUENCE streaks.restore_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE streaks.restore_log_id_seq OWNER TO postgres;

--
-- Name: restore_log_id_seq; Type: SEQUENCE OWNED BY; Schema: streaks; Owner: postgres
--

ALTER SEQUENCE streaks.restore_log_id_seq OWNED BY streaks.restore_log.id;


--
-- Name: users; Type: TABLE; Schema: streaks; Owner: postgres
--

CREATE TABLE streaks.users (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    current_streak integer DEFAULT 0,
    highest_streak integer DEFAULT 0,
    last_streak_time timestamp with time zone,
    restores_available integer DEFAULT 0,
    total_images_sent integer DEFAULT 0
);


ALTER TABLE streaks.users OWNER TO postgres;

--
-- Name: button; Type: TABLE; Schema: ticket; Owner: root
--

CREATE TABLE ticket.button (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    template text,
    category_id bigint,
    topic text
);


ALTER TABLE ticket.button OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: ticket; Owner: root
--

CREATE TABLE ticket.config (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    staff_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    blacklisted_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    channel_name text,
    logging_channel bigint DEFAULT 0
);


ALTER TABLE ticket.config OWNER TO root;

--
-- Name: logs; Type: TABLE; Schema: ticket; Owner: postgres
--

CREATE TABLE ticket.logs (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE ticket.logs OWNER TO postgres;

--
-- Name: open; Type: TABLE; Schema: ticket; Owner: root
--

CREATE TABLE ticket.open (
    identifier text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE ticket.open OWNER TO root;

--
-- Name: message; Type: TABLE; Schema: timer; Owner: root
--

CREATE TABLE timer.message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    template text NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL
);


ALTER TABLE timer.message OWNER TO root;

--
-- Name: purge; Type: TABLE; Schema: timer; Owner: root
--

CREATE TABLE timer.purge (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    "interval" integer NOT NULL,
    next_trigger timestamp with time zone NOT NULL,
    method text DEFAULT 'bulk'::text NOT NULL
);


ALTER TABLE timer.purge OWNER TO root;

--
-- Name: username; Type: TABLE; Schema: track; Owner: root
--

CREATE TABLE track.username (
    username text NOT NULL,
    user_ids bigint[]
);


ALTER TABLE track.username OWNER TO root;

--
-- Name: vanity; Type: TABLE; Schema: track; Owner: root
--

CREATE TABLE track.vanity (
    vanity text NOT NULL,
    user_ids bigint[]
);


ALTER TABLE track.vanity OWNER TO root;

--
-- Name: channels; Type: TABLE; Schema: transcribe; Owner: postgres
--

CREATE TABLE transcribe.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    added_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE transcribe.channels OWNER TO postgres;

--
-- Name: rate_limit; Type: TABLE; Schema: transcribe; Owner: postgres
--

CREATE TABLE transcribe.rate_limit (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    last_used timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    uses integer DEFAULT 1
);


ALTER TABLE transcribe.rate_limit OWNER TO postgres;

--
-- Name: logs; Type: TABLE; Schema: verification; Owner: postgres
--

CREATE TABLE verification.logs (
    id integer NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    session_id text NOT NULL,
    event_type text NOT NULL,
    details jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE verification.logs OWNER TO postgres;

--
-- Name: logs_id_seq; Type: SEQUENCE; Schema: verification; Owner: postgres
--

CREATE SEQUENCE verification.logs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE verification.logs_id_seq OWNER TO postgres;

--
-- Name: logs_id_seq; Type: SEQUENCE OWNED BY; Schema: verification; Owner: postgres
--

ALTER SEQUENCE verification.logs_id_seq OWNED BY verification.logs.id;


--
-- Name: sessions; Type: TABLE; Schema: verification; Owner: postgres
--

CREATE TABLE verification.sessions (
    session_id text NOT NULL,
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    completed boolean DEFAULT false,
    failed_attempts integer DEFAULT 0
);


ALTER TABLE verification.sessions OWNER TO postgres;

--
-- Name: settings; Type: TABLE; Schema: verification; Owner: postgres
--

CREATE TABLE verification.settings (
    guild_id bigint NOT NULL,
    enabled boolean DEFAULT false,
    level text DEFAULT 'base'::text,
    methods text[] DEFAULT '{}'::text[],
    timeout integer DEFAULT 1800,
    ip_limit boolean DEFAULT false,
    vpn_check boolean DEFAULT false,
    private_tab_check boolean DEFAULT false,
    log_channel_id bigint,
    verify_channel_id bigint,
    verify_role_id bigint,
    CONSTRAINT settings_level_check CHECK ((level = ANY (ARRAY['base'::text, 'medium'::text])))
);


ALTER TABLE verification.settings OWNER TO postgres;

--
-- Name: channels; Type: TABLE; Schema: voice; Owner: root
--

CREATE TABLE voice.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    owner_id bigint NOT NULL
);


ALTER TABLE voice.channels OWNER TO root;

--
-- Name: config; Type: TABLE; Schema: voice; Owner: root
--

CREATE TABLE voice.config (
    guild_id bigint NOT NULL,
    category_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    bitrate integer,
    name text,
    status text
);


ALTER TABLE voice.config OWNER TO root;

--
-- Name: recordings; Type: TABLE; Schema: voice; Owner: postgres
--

CREATE TABLE voice.recordings (
    id uuid NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    initiator_id bigint NOT NULL,
    started_at timestamp without time zone NOT NULL,
    ended_at timestamp without time zone,
    status text NOT NULL,
    file_path text
);


ALTER TABLE voice.recordings OWNER TO postgres;

--
-- Name: channels; Type: TABLE; Schema: voicemaster; Owner: postgres
--

CREATE TABLE voicemaster.channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    owner_id bigint
);


ALTER TABLE voicemaster.channels OWNER TO postgres;

--
-- Name: configuration; Type: TABLE; Schema: voicemaster; Owner: postgres
--

CREATE TABLE voicemaster.configuration (
    guild_id bigint NOT NULL,
    category_id bigint,
    interface_id bigint,
    channel_id bigint,
    role_id bigint,
    region text,
    bitrate bigint,
    interface_emojis jsonb,
    interface_layout character varying(10) DEFAULT 'default'::character varying,
    interface_embed text
);


ALTER TABLE voicemaster.configuration OWNER TO postgres;

--
-- Name: media id; Type: DEFAULT; Schema: auto; Owner: root
--

ALTER TABLE ONLY auto.media ALTER COLUMN id SET DEFAULT nextval('auto.media_id_seq'::regclass);


--
-- Name: moderation id; Type: DEFAULT; Schema: history; Owner: root
--

ALTER TABLE ONLY history.moderation ALTER COLUMN id SET DEFAULT nextval('history.moderation_id_seq'::regclass);


--
-- Name: commands id; Type: DEFAULT; Schema: invoke_history; Owner: root
--

ALTER TABLE ONLY invoke_history.commands ALTER COLUMN id SET DEFAULT nextval('invoke_history.commands_id_seq'::regclass);


--
-- Name: history id; Type: DEFAULT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.history ALTER COLUMN id SET DEFAULT nextval('music.history_id_seq'::regclass);


--
-- Name: playlist_tracks id; Type: DEFAULT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.playlist_tracks ALTER COLUMN id SET DEFAULT nextval('music.playlist_tracks_id_seq'::regclass);


--
-- Name: playlists id; Type: DEFAULT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.playlists ALTER COLUMN id SET DEFAULT nextval('music.playlists_id_seq'::regclass);


--
-- Name: appeals id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appeals ALTER COLUMN id SET DEFAULT nextval('public.appeals_id_seq'::regclass);


--
-- Name: business_jobs job_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_jobs ALTER COLUMN job_id SET DEFAULT nextval('public.business_jobs_job_id_seq'::regclass);


--
-- Name: businesses business_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.businesses ALTER COLUMN business_id SET DEFAULT nextval('public.businesses_business_id_seq'::regclass);


--
-- Name: card_duels duel_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_duels ALTER COLUMN duel_id SET DEFAULT nextval('public.card_duels_duel_id_seq'::regclass);


--
-- Name: card_market listing_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_market ALTER COLUMN listing_id SET DEFAULT nextval('public.card_market_listing_id_seq'::regclass);


--
-- Name: card_packs pack_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_packs ALTER COLUMN pack_id SET DEFAULT nextval('public.card_packs_pack_id_seq'::regclass);


--
-- Name: card_sets set_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_sets ALTER COLUMN set_id SET DEFAULT nextval('public.card_sets_set_id_seq'::regclass);


--
-- Name: gambling_history game_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gambling_history ALTER COLUMN game_id SET DEFAULT nextval('public.gambling_history_game_id_seq'::regclass);


--
-- Name: gift_logs gift_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gift_logs ALTER COLUMN gift_id SET DEFAULT nextval('public.gift_logs_gift_id_seq'::regclass);


--
-- Name: instances id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instances ALTER COLUMN id SET DEFAULT nextval('public.instances_id_seq'::regclass);


--
-- Name: job_applications application_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_applications ALTER COLUMN application_id SET DEFAULT nextval('public.job_applications_application_id_seq'::regclass);


--
-- Name: logging_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logging_history ALTER COLUMN id SET DEFAULT nextval('public.logging_history_id_seq'::regclass);


--
-- Name: lottery_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lottery_history ALTER COLUMN id SET DEFAULT nextval('public.lottery_history_id_seq'::regclass);


--
-- Name: pet_adventures adventure_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_adventures ALTER COLUMN adventure_id SET DEFAULT nextval('public.pet_adventures_adventure_id_seq'::regclass);


--
-- Name: pet_items item_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_items ALTER COLUMN item_id SET DEFAULT nextval('public.pet_items_item_id_seq'::regclass);


--
-- Name: pet_trades trade_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_trades ALTER COLUMN trade_id SET DEFAULT nextval('public.pet_trades_trade_id_seq'::regclass);


--
-- Name: pets pet_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pets ALTER COLUMN pet_id SET DEFAULT nextval('public.pets_pet_id_seq'::regclass);


--
-- Name: role_applications id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_applications ALTER COLUMN id SET DEFAULT nextval('public.role_applications_id_seq'::regclass);


--
-- Name: shop_items item_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shop_items ALTER COLUMN item_id SET DEFAULT nextval('public.shop_items_item_id_seq'::regclass);


--
-- Name: socials_details detail_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_details ALTER COLUMN detail_id SET DEFAULT nextval('public.socials_details_detail_id_seq'::regclass);


--
-- Name: transactions id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions ALTER COLUMN id SET DEFAULT nextval('public.transactions_id_seq'::regclass);


--
-- Name: user_decks deck_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_decks ALTER COLUMN deck_id SET DEFAULT nextval('public.user_decks_deck_id_seq'::regclass);


--
-- Name: user_transactions transaction_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_transactions ALTER COLUMN transaction_id SET DEFAULT nextval('public.user_transactions_transaction_id_seq'::regclass);


--
-- Name: restore_log id; Type: DEFAULT; Schema: streaks; Owner: postgres
--

ALTER TABLE ONLY streaks.restore_log ALTER COLUMN id SET DEFAULT nextval('streaks.restore_log_id_seq'::regclass);


--
-- Name: logs id; Type: DEFAULT; Schema: verification; Owner: postgres
--

ALTER TABLE ONLY verification.logs ALTER COLUMN id SET DEFAULT nextval('verification.logs_id_seq'::regclass);


--
-- Name: twitch twitch_pkey; Type: CONSTRAINT; Schema: alerts; Owner: root
--

ALTER TABLE ONLY alerts.twitch
    ADD CONSTRAINT twitch_pkey PRIMARY KEY (guild_id, twitch_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: audio; Owner: root
--

ALTER TABLE ONLY audio.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: playlist_tracks playlist_tracks_pkey; Type: CONSTRAINT; Schema: audio; Owner: postgres
--

ALTER TABLE ONLY audio.playlist_tracks
    ADD CONSTRAINT playlist_tracks_pkey PRIMARY KEY (guild_id, user_id, playlist_url, track_uri);


--
-- Name: playlists playlists_pkey; Type: CONSTRAINT; Schema: audio; Owner: postgres
--

ALTER TABLE ONLY audio.playlists
    ADD CONSTRAINT playlists_pkey PRIMARY KEY (guild_id, user_id, playlist_url);


--
-- Name: recently_played recently_played_pkey; Type: CONSTRAINT; Schema: audio; Owner: postgres
--

ALTER TABLE ONLY audio.recently_played
    ADD CONSTRAINT recently_played_pkey PRIMARY KEY (guild_id, user_id, played_at);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: audio; Owner: postgres
--

ALTER TABLE ONLY audio.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (guild_id);


--
-- Name: statistics statistics_pkey; Type: CONSTRAINT; Schema: audio; Owner: root
--

ALTER TABLE ONLY audio.statistics
    ADD CONSTRAINT statistics_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: media media_pkey; Type: CONSTRAINT; Schema: auto; Owner: root
--

ALTER TABLE ONLY auto.media
    ADD CONSTRAINT media_pkey PRIMARY KEY (id);


--
-- Name: media unique_media_config; Type: CONSTRAINT; Schema: auto; Owner: root
--

ALTER TABLE ONLY auto.media
    ADD CONSTRAINT unique_media_config UNIQUE (guild_id, channel_id, type);


--
-- Name: disabled disabled_pkey; Type: CONSTRAINT; Schema: commands; Owner: root
--

ALTER TABLE ONLY commands.disabled
    ADD CONSTRAINT disabled_pkey PRIMARY KEY (guild_id, channel_id, command);


--
-- Name: ignore ignore_pkey; Type: CONSTRAINT; Schema: commands; Owner: root
--

ALTER TABLE ONLY commands.ignore
    ADD CONSTRAINT ignore_pkey PRIMARY KEY (guild_id, target_id);


--
-- Name: restricted restricted_pkey; Type: CONSTRAINT; Schema: commands; Owner: root
--

ALTER TABLE ONLY commands.restricted
    ADD CONSTRAINT restricted_pkey PRIMARY KEY (guild_id, role_id, command);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: counting; Owner: postgres
--

ALTER TABLE ONLY counting.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: disboard; Owner: root
--

ALTER TABLE ONLY disboard.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: marriages marriages_pkey; Type: CONSTRAINT; Schema: family; Owner: postgres
--

ALTER TABLE ONLY family.marriages
    ADD CONSTRAINT marriages_pkey PRIMARY KEY (user_id, partner_id);


--
-- Name: members members_pkey; Type: CONSTRAINT; Schema: family; Owner: postgres
--

ALTER TABLE ONLY family.members
    ADD CONSTRAINT members_pkey PRIMARY KEY (user_id, related_id);


--
-- Name: profiles profiles_pkey; Type: CONSTRAINT; Schema: family; Owner: postgres
--

ALTER TABLE ONLY family.profiles
    ADD CONSTRAINT profiles_pkey PRIMARY KEY (user_id);


--
-- Name: instagram instagram_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.instagram
    ADD CONSTRAINT instagram_pkey PRIMARY KEY (guild_id, instagram_id);


--
-- Name: pinterest pinterest_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.pinterest
    ADD CONSTRAINT pinterest_pkey PRIMARY KEY (guild_id, pinterest_id);


--
-- Name: reddit reddit_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.reddit
    ADD CONSTRAINT reddit_pkey PRIMARY KEY (guild_id, subreddit_name);


--
-- Name: soundcloud soundcloud_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.soundcloud
    ADD CONSTRAINT soundcloud_pkey PRIMARY KEY (guild_id, soundcloud_id);


--
-- Name: tiktok tiktok_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.tiktok
    ADD CONSTRAINT tiktok_pkey PRIMARY KEY (guild_id, tiktok_id);


--
-- Name: twitter twitter_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.twitter
    ADD CONSTRAINT twitter_pkey PRIMARY KEY (guild_id, twitter_id);


--
-- Name: youtube youtube_pkey; Type: CONSTRAINT; Schema: feeds; Owner: root
--

ALTER TABLE ONLY feeds.youtube
    ADD CONSTRAINT youtube_pkey PRIMARY KEY (guild_id, youtube_id);


--
-- Name: authorization authorization_user_id_key; Type: CONSTRAINT; Schema: fortnite; Owner: root
--

ALTER TABLE ONLY fortnite."authorization"
    ADD CONSTRAINT authorization_user_id_key UNIQUE (user_id);


--
-- Name: reminder reminder_pkey; Type: CONSTRAINT; Schema: fortnite; Owner: root
--

ALTER TABLE ONLY fortnite.reminder
    ADD CONSTRAINT reminder_pkey PRIMARY KEY (user_id, item_id);


--
-- Name: rotation rotation_guild_id_key; Type: CONSTRAINT; Schema: fortnite; Owner: root
--

ALTER TABLE ONLY fortnite.rotation
    ADD CONSTRAINT rotation_guild_id_key UNIQUE (guild_id);


--
-- Name: wyr_channels wyr_channels_pkey; Type: CONSTRAINT; Schema: fun; Owner: postgres
--

ALTER TABLE ONLY fun.wyr_channels
    ADD CONSTRAINT wyr_channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: moderation moderation_pkey; Type: CONSTRAINT; Schema: history; Owner: root
--

ALTER TABLE ONLY history.moderation
    ADD CONSTRAINT moderation_pkey PRIMARY KEY (id);


--
-- Name: commands commands_pkey; Type: CONSTRAINT; Schema: invoke_history; Owner: root
--

ALTER TABLE ONLY invoke_history.commands
    ADD CONSTRAINT commands_pkey PRIMARY KEY (id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: joindm; Owner: postgres
--

ALTER TABLE ONLY joindm.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: albums albums_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.albums
    ADD CONSTRAINT albums_pkey PRIMARY KEY (user_id, artist, album);


--
-- Name: artists artists_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.artists
    ADD CONSTRAINT artists_pkey PRIMARY KEY (user_id, artist);


--
-- Name: config config_user_id_key; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.config
    ADD CONSTRAINT config_user_id_key UNIQUE (user_id);


--
-- Name: crown_updates crown_updates_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: postgres
--

ALTER TABLE ONLY lastfm.crown_updates
    ADD CONSTRAINT crown_updates_pkey PRIMARY KEY (guild_id);


--
-- Name: crowns crowns_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.crowns
    ADD CONSTRAINT crowns_pkey PRIMARY KEY (guild_id, artist);


--
-- Name: hidden hidden_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.hidden
    ADD CONSTRAINT hidden_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: tracks tracks_pkey; Type: CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.tracks
    ADD CONSTRAINT tracks_pkey PRIMARY KEY (user_id, artist, track);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: member member_pkey; Type: CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.member
    ADD CONSTRAINT member_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (guild_id);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (guild_id, level);


--
-- Name: role role_role_id_key; Type: CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_role_id_key UNIQUE (role_id);


--
-- Name: history history_pkey; Type: CONSTRAINT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.history
    ADD CONSTRAINT history_pkey PRIMARY KEY (id);


--
-- Name: playlist_tracks playlist_tracks_pkey; Type: CONSTRAINT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.playlist_tracks
    ADD CONSTRAINT playlist_tracks_pkey PRIMARY KEY (id);


--
-- Name: playlists playlists_pkey; Type: CONSTRAINT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.playlists
    ADD CONSTRAINT playlists_pkey PRIMARY KEY (id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: porn; Owner: postgres
--

ALTER TABLE ONLY porn.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: access_tokens access_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.access_tokens
    ADD CONSTRAINT access_tokens_pkey PRIMARY KEY (user_id);


--
-- Name: afk afk_user_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.afk
    ADD CONSTRAINT afk_user_id_key UNIQUE (user_id);


--
-- Name: aliases aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.aliases
    ADD CONSTRAINT aliases_pkey PRIMARY KEY (guild_id, name);


--
-- Name: antinuke antinuke_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.antinuke
    ADD CONSTRAINT antinuke_guild_id_key UNIQUE (guild_id);


--
-- Name: antiraid antiraid_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.antiraid
    ADD CONSTRAINT antiraid_pkey PRIMARY KEY (guild_id);


--
-- Name: appeal_config appeal_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appeal_config
    ADD CONSTRAINT appeal_config_pkey PRIMARY KEY (guild_id);


--
-- Name: appeal_templates appeal_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appeal_templates
    ADD CONSTRAINT appeal_templates_pkey PRIMARY KEY (guild_id, name);


--
-- Name: appeals appeals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.appeals
    ADD CONSTRAINT appeals_pkey PRIMARY KEY (id);


--
-- Name: auto_role auto_role_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.auto_role
    ADD CONSTRAINT auto_role_pkey PRIMARY KEY (guild_id, role_id, action);


--
-- Name: avatar_current avatar_current_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_current
    ADD CONSTRAINT avatar_current_pkey PRIMARY KEY (user_id);


--
-- Name: avatar_history avatar_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_history
    ADD CONSTRAINT avatar_history_pkey PRIMARY KEY (user_id, avatar_url);


--
-- Name: avatar_history_settings avatar_history_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_history_settings
    ADD CONSTRAINT avatar_history_settings_pkey PRIMARY KEY (user_id);


--
-- Name: backup backup_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.backup
    ADD CONSTRAINT backup_pkey PRIMARY KEY (key, guild_id);


--
-- Name: beta_dashboard beta_dashboard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.beta_dashboard
    ADD CONSTRAINT beta_dashboard_pkey PRIMARY KEY (user_id);


--
-- Name: birthdays birthdays_user_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.birthdays
    ADD CONSTRAINT birthdays_user_id_key UNIQUE (user_id);


--
-- Name: blacklist blacklist_user_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.blacklist
    ADD CONSTRAINT blacklist_user_id_key UNIQUE (user_id);


--
-- Name: blunt blunt_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blunt
    ADD CONSTRAINT blunt_pkey PRIMARY KEY (guild_id);


--
-- Name: boost_history boost_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.boost_history
    ADD CONSTRAINT boost_history_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: boost_message boost_message_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.boost_message
    ADD CONSTRAINT boost_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: booster_role booster_role_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.booster_role
    ADD CONSTRAINT booster_role_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: boosters_lost boosters_lost_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.boosters_lost
    ADD CONSTRAINT boosters_lost_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: business_jobs business_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_jobs
    ADD CONSTRAINT business_jobs_pkey PRIMARY KEY (job_id);


--
-- Name: business_stats business_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_stats
    ADD CONSTRAINT business_stats_pkey PRIMARY KEY (business_id);


--
-- Name: businesses businesses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.businesses
    ADD CONSTRAINT businesses_pkey PRIMARY KEY (business_id);


--
-- Name: card_daily card_daily_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_daily
    ADD CONSTRAINT card_daily_pkey PRIMARY KEY (user_id);


--
-- Name: card_drop_channels card_drop_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_drop_channels
    ADD CONSTRAINT card_drop_channels_pkey PRIMARY KEY (channel_id);


--
-- Name: card_duels card_duels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_duels
    ADD CONSTRAINT card_duels_pkey PRIMARY KEY (duel_id);


--
-- Name: card_market card_market_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_market
    ADD CONSTRAINT card_market_pkey PRIMARY KEY (listing_id);


--
-- Name: card_packs card_packs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_packs
    ADD CONSTRAINT card_packs_pkey PRIMARY KEY (pack_id);


--
-- Name: card_sets card_sets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.card_sets
    ADD CONSTRAINT card_sets_pkey PRIMARY KEY (set_id);


--
-- Name: clownboard_entry clownboard_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clownboard_entry
    ADD CONSTRAINT clownboard_entry_pkey PRIMARY KEY (guild_id, channel_id, message_id, emoji);


--
-- Name: clownboard clownboard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clownboard
    ADD CONSTRAINT clownboard_pkey PRIMARY KEY (guild_id, emoji);


--
-- Name: confess_blacklist confess_blacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.confess_blacklist
    ADD CONSTRAINT confess_blacklist_pkey PRIMARY KEY (guild_id, word);


--
-- Name: confess_replies confess_replies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.confess_replies
    ADD CONSTRAINT confess_replies_pkey PRIMARY KEY (message_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: contracts contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.contracts
    ADD CONSTRAINT contracts_pkey PRIMARY KEY (business_id, employee_id);


--
-- Name: counter counter_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.counter
    ADD CONSTRAINT counter_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: crypto crypto_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.crypto
    ADD CONSTRAINT crypto_pkey PRIMARY KEY (user_id, transaction_id);


--
-- Name: dalle_credits dalle_credits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.dalle_credits
    ADD CONSTRAINT dalle_credits_pkey PRIMARY KEY (user_id);


--
-- Name: deck_cards deck_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deck_cards
    ADD CONSTRAINT deck_cards_pkey PRIMARY KEY (deck_id, card_id);


--
-- Name: earnings earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.earnings
    ADD CONSTRAINT earnings_pkey PRIMARY KEY (user_id);


--
-- Name: economy economy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy
    ADD CONSTRAINT economy_pkey PRIMARY KEY (user_id);


--
-- Name: economy_roleshop economy_roleshop_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_roleshop
    ADD CONSTRAINT economy_roleshop_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: employee_stats employee_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_stats
    ADD CONSTRAINT employee_stats_pkey PRIMARY KEY (business_id, employee_id);


--
-- Name: fake_permissions fake_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.fake_permissions
    ADD CONSTRAINT fake_permissions_pkey PRIMARY KEY (guild_id, role_id, permission);


--
-- Name: forcenick forcenick_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.forcenick
    ADD CONSTRAINT forcenick_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: gallery gallery_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.gallery
    ADD CONSTRAINT gallery_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: gambling_history gambling_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gambling_history
    ADD CONSTRAINT gambling_history_pkey PRIMARY KEY (game_id);


--
-- Name: gift_logs gift_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gift_logs
    ADD CONSTRAINT gift_logs_pkey PRIMARY KEY (gift_id);


--
-- Name: giveaway_settings giveaway_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.giveaway_settings
    ADD CONSTRAINT giveaway_settings_pkey PRIMARY KEY (guild_id);


--
-- Name: gnames gnames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gnames
    ADD CONSTRAINT gnames_pkey PRIMARY KEY (guild_id, name, changed_at);


--
-- Name: goodbye_message goodbye_message_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.goodbye_message
    ADD CONSTRAINT goodbye_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: guild_verification guild_verification_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guild_verification
    ADD CONSTRAINT guild_verification_pkey PRIMARY KEY (guild_id);


--
-- Name: guildblacklist guildblacklist_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guildblacklist
    ADD CONSTRAINT guildblacklist_guild_id_key UNIQUE (guild_id);


--
-- Name: highlights highlights_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.highlights
    ADD CONSTRAINT highlights_pkey PRIMARY KEY (guild_id, user_id, word);


--
-- Name: immune immune_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.immune
    ADD CONSTRAINT immune_pkey PRIMARY KEY (guild_id, entity_id, type);


--
-- Name: instances instances_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.instances
    ADD CONSTRAINT instances_pkey PRIMARY KEY (id);


--
-- Name: invite_config invite_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invite_config
    ADD CONSTRAINT invite_config_pkey PRIMARY KEY (guild_id);


--
-- Name: invite_rewards invite_rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invite_rewards
    ADD CONSTRAINT invite_rewards_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: invite_tracking invite_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invite_tracking
    ADD CONSTRAINT invite_tracking_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: job_applications job_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.job_applications
    ADD CONSTRAINT job_applications_pkey PRIMARY KEY (application_id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (user_id);


--
-- Name: logging_history logging_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logging_history
    ADD CONSTRAINT logging_history_pkey PRIMARY KEY (id);


--
-- Name: logging logging_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.logging
    ADD CONSTRAINT logging_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: lottery_history lottery_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lottery_history
    ADD CONSTRAINT lottery_history_pkey PRIMARY KEY (id);


--
-- Name: lovense_config lovense_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lovense_config
    ADD CONSTRAINT lovense_config_pkey PRIMARY KEY (guild_id);


--
-- Name: lovense_connections lovense_connections_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lovense_connections
    ADD CONSTRAINT lovense_connections_pkey PRIMARY KEY (token);


--
-- Name: lovense_consent lovense_consent_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lovense_consent
    ADD CONSTRAINT lovense_consent_pkey PRIMARY KEY (user_id);


--
-- Name: lovense_devices lovense_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lovense_devices
    ADD CONSTRAINT lovense_devices_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: lovense_shares lovense_shares_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lovense_shares
    ADD CONSTRAINT lovense_shares_pkey PRIMARY KEY (guild_id, owner_id, target_id, device_id);


--
-- Name: pet_adventures pet_adventures_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_adventures
    ADD CONSTRAINT pet_adventures_pkey PRIMARY KEY (adventure_id);


--
-- Name: pet_items pet_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_items
    ADD CONSTRAINT pet_items_pkey PRIMARY KEY (item_id);


--
-- Name: pet_trades pet_trades_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_trades
    ADD CONSTRAINT pet_trades_pkey PRIMARY KEY (trade_id);


--
-- Name: pets pets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pets
    ADD CONSTRAINT pets_pkey PRIMARY KEY (pet_id);


--
-- Name: poll_votes poll_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_pkey PRIMARY KEY (vote_id);


--
-- Name: poll_votes poll_votes_poll_id_user_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_poll_id_user_id_key UNIQUE (poll_id, user_id);


--
-- Name: polls polls_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.polls
    ADD CONSTRAINT polls_pkey PRIMARY KEY (poll_id);


--
-- Name: publisher publisher_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.publisher
    ADD CONSTRAINT publisher_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: quoter quoter_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.quoter
    ADD CONSTRAINT quoter_guild_id_key UNIQUE (guild_id);


--
-- Name: reaction_role reaction_role_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.reaction_role
    ADD CONSTRAINT reaction_role_pkey PRIMARY KEY (guild_id, message_id, emoji);


--
-- Name: reaction_trigger reaction_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.reaction_trigger
    ADD CONSTRAINT reaction_trigger_pkey PRIMARY KEY (guild_id, trigger, emoji);


--
-- Name: recordings recordings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.recordings
    ADD CONSTRAINT recordings_pkey PRIMARY KEY (id);


--
-- Name: response_trigger response_trigger_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.response_trigger
    ADD CONSTRAINT response_trigger_pkey PRIMARY KEY (guild_id, trigger);


--
-- Name: role_applications role_applications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_applications
    ADD CONSTRAINT role_applications_pkey PRIMARY KEY (id);


--
-- Name: role_applications role_applications_user_id_role_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_applications
    ADD CONSTRAINT role_applications_user_id_role_id_key UNIQUE (user_id, role_id);


--
-- Name: role_shops role_shops_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.role_shops
    ADD CONSTRAINT role_shops_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: roleplay roleplay_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.roleplay
    ADD CONSTRAINT roleplay_pkey PRIMARY KEY (user_id, target_id, category);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (guild_id);


--
-- Name: shop_items shop_items_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shop_items
    ADD CONSTRAINT shop_items_name_key UNIQUE (name);


--
-- Name: shop_items shop_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shop_items
    ADD CONSTRAINT shop_items_pkey PRIMARY KEY (item_id);


--
-- Name: social_links social_links_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.social_links
    ADD CONSTRAINT social_links_unique UNIQUE (user_id, type);


--
-- Name: socials_details socials_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_details
    ADD CONSTRAINT socials_details_pkey PRIMARY KEY (detail_id);


--
-- Name: socials_details socials_details_user_id_friends_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_details
    ADD CONSTRAINT socials_details_user_id_friends_key UNIQUE (user_id, friends);


--
-- Name: socials_gradients socials_gradients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_gradients
    ADD CONSTRAINT socials_gradients_pkey PRIMARY KEY (user_id, "position");


--
-- Name: socials socials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials
    ADD CONSTRAINT socials_pkey PRIMARY KEY (user_id);


--
-- Name: socials_saved_colors socials_saved_colors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_saved_colors
    ADD CONSTRAINT socials_saved_colors_pkey PRIMARY KEY (user_id, name);


--
-- Name: socials_saved_gradients socials_saved_gradients_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_saved_gradients
    ADD CONSTRAINT socials_saved_gradients_pkey PRIMARY KEY (user_id, name, "position");


--
-- Name: starboard_entry starboard_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.starboard_entry
    ADD CONSTRAINT starboard_entry_pkey PRIMARY KEY (guild_id, channel_id, message_id, emoji);


--
-- Name: starboard starboard_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.starboard
    ADD CONSTRAINT starboard_pkey PRIMARY KEY (guild_id, emoji);


--
-- Name: steal_disabled steal_disabled_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.steal_disabled
    ADD CONSTRAINT steal_disabled_pkey PRIMARY KEY (guild_id);


--
-- Name: sticky_message sticky_message_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.sticky_message
    ADD CONSTRAINT sticky_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: suggestion_entries suggestion_entries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suggestion_entries
    ADD CONSTRAINT suggestion_entries_pkey PRIMARY KEY (guild_id, message_id);


--
-- Name: suggestion_votes suggestion_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suggestion_votes
    ADD CONSTRAINT suggestion_votes_pkey PRIMARY KEY (message_id, user_id);


--
-- Name: tag_aliases tag_aliases_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tag_aliases
    ADD CONSTRAINT tag_aliases_pkey PRIMARY KEY (guild_id, alias);


--
-- Name: tags tags_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tags
    ADD CONSTRAINT tags_pkey PRIMARY KEY (guild_id, name);


--
-- Name: thread thread_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.thread
    ADD CONSTRAINT thread_pkey PRIMARY KEY (guild_id, thread_id);


--
-- Name: timezones timezones_user_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.timezones
    ADD CONSTRAINT timezones_user_id_key UNIQUE (user_id);


--
-- Name: tracker tracker_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tracker
    ADD CONSTRAINT tracker_pkey PRIMARY KEY (guild_id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: translation_contributors translation_contributors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.translation_contributors
    ADD CONSTRAINT translation_contributors_pkey PRIMARY KEY (user_id);


--
-- Name: roleplay_enabled unique_guild_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roleplay_enabled
    ADD CONSTRAINT unique_guild_id UNIQUE (guild_id);


--
-- Name: mod unique_guild_user; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mod
    ADD CONSTRAINT unique_guild_user UNIQUE (guild_id, user_id);


--
-- Name: used_items used_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.used_items
    ADD CONSTRAINT used_items_pkey PRIMARY KEY (user_id, item);


--
-- Name: user_cards user_cards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_cards
    ADD CONSTRAINT user_cards_pkey PRIMARY KEY (user_id, card_id);


--
-- Name: user_decks user_decks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_decks
    ADD CONSTRAINT user_decks_pkey PRIMARY KEY (deck_id);


--
-- Name: user_items user_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_items
    ADD CONSTRAINT user_items_pkey PRIMARY KEY (user_id, item_id);


--
-- Name: user_links user_links_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_links
    ADD CONSTRAINT user_links_pkey PRIMARY KEY (user_id, type);


--
-- Name: user_spotify user_spotify_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_spotify
    ADD CONSTRAINT user_spotify_pkey PRIMARY KEY (user_id);


--
-- Name: user_transactions user_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_transactions
    ADD CONSTRAINT user_transactions_pkey PRIMARY KEY (transaction_id);


--
-- Name: user_votes user_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_votes
    ADD CONSTRAINT user_votes_pkey PRIMARY KEY (user_id);


--
-- Name: vanity vanity_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.vanity
    ADD CONSTRAINT vanity_guild_id_key UNIQUE (guild_id);


--
-- Name: vape vape_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vape
    ADD CONSTRAINT vape_pkey PRIMARY KEY (user_id);


--
-- Name: verification_question_sessions verification_question_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verification_question_sessions
    ADD CONSTRAINT verification_question_sessions_pkey PRIMARY KEY (session_token);


--
-- Name: warn_actions warn_actions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.warn_actions
    ADD CONSTRAINT warn_actions_pkey PRIMARY KEY (guild_id, threshold);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (channel_id, webhook_id);


--
-- Name: welcome_message welcome_message_pkey; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.welcome_message
    ADD CONSTRAINT welcome_message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: whitelist whitelist_guild_id_key; Type: CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.whitelist
    ADD CONSTRAINT whitelist_guild_id_key UNIQUE (guild_id);


--
-- Name: disabled disabled_pkey; Type: CONSTRAINT; Schema: reposters; Owner: root
--

ALTER TABLE ONLY reposters.disabled
    ADD CONSTRAINT disabled_pkey PRIMARY KEY (guild_id, channel_id, reposter);


--
-- Name: config config_user_id_key; Type: CONSTRAINT; Schema: reskin; Owner: root
--

ALTER TABLE ONLY reskin.config
    ADD CONSTRAINT config_user_id_key UNIQUE (user_id);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: reskin; Owner: root
--

ALTER TABLE ONLY reskin.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: filter filter_guild_id_key; Type: CONSTRAINT; Schema: snipe; Owner: root
--

ALTER TABLE ONLY snipe.filter
    ADD CONSTRAINT filter_guild_id_key UNIQUE (guild_id);


--
-- Name: ignore ignore_pkey; Type: CONSTRAINT; Schema: snipe; Owner: root
--

ALTER TABLE ONLY snipe.ignore
    ADD CONSTRAINT ignore_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: spam; Owner: postgres
--

ALTER TABLE ONLY spam.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: exempt exempt_pkey; Type: CONSTRAINT; Schema: spam; Owner: postgres
--

ALTER TABLE ONLY spam.exempt
    ADD CONSTRAINT exempt_pkey PRIMARY KEY (guild_id, entity_id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: spam; Owner: postgres
--

ALTER TABLE ONLY spam.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (guild_id, user_id, message_hash);


--
-- Name: daily_channels daily_channels_pkey; Type: CONSTRAINT; Schema: statistics; Owner: postgres
--

ALTER TABLE ONLY statistics.daily_channels
    ADD CONSTRAINT daily_channels_pkey PRIMARY KEY (guild_id, channel_id, date);


--
-- Name: daily daily_pkey; Type: CONSTRAINT; Schema: statistics; Owner: postgres
--

ALTER TABLE ONLY statistics.daily
    ADD CONSTRAINT daily_pkey PRIMARY KEY (guild_id, date, member_id);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: stats; Owner: postgres
--

ALTER TABLE ONLY stats.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: custom_commands custom_commands_pkey; Type: CONSTRAINT; Schema: stats; Owner: postgres
--

ALTER TABLE ONLY stats.custom_commands
    ADD CONSTRAINT custom_commands_pkey PRIMARY KEY (guild_id, command);


--
-- Name: ignored_words ignored_words_pkey; Type: CONSTRAINT; Schema: stats; Owner: postgres
--

ALTER TABLE ONLY stats.ignored_words
    ADD CONSTRAINT ignored_words_pkey PRIMARY KEY (guild_id, word);


--
-- Name: word_usage word_usage_pkey; Type: CONSTRAINT; Schema: stats; Owner: postgres
--

ALTER TABLE ONLY stats.word_usage
    ADD CONSTRAINT word_usage_pkey PRIMARY KEY (guild_id, user_id, word);


--
-- Name: config config_pkey; Type: CONSTRAINT; Schema: streaks; Owner: postgres
--

ALTER TABLE ONLY streaks.config
    ADD CONSTRAINT config_pkey PRIMARY KEY (guild_id);


--
-- Name: restore_log restore_log_pkey; Type: CONSTRAINT; Schema: streaks; Owner: postgres
--

ALTER TABLE ONLY streaks.restore_log
    ADD CONSTRAINT restore_log_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: streaks; Owner: postgres
--

ALTER TABLE ONLY streaks.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: button button_pkey; Type: CONSTRAINT; Schema: ticket; Owner: root
--

ALTER TABLE ONLY ticket.button
    ADD CONSTRAINT button_pkey PRIMARY KEY (identifier, guild_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: ticket; Owner: root
--

ALTER TABLE ONLY ticket.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: open open_pkey; Type: CONSTRAINT; Schema: ticket; Owner: root
--

ALTER TABLE ONLY ticket.open
    ADD CONSTRAINT open_pkey PRIMARY KEY (identifier, guild_id, user_id);


--
-- Name: logs unique_guild_id; Type: CONSTRAINT; Schema: ticket; Owner: postgres
--

ALTER TABLE ONLY ticket.logs
    ADD CONSTRAINT unique_guild_id UNIQUE (guild_id);


--
-- Name: message message_pkey; Type: CONSTRAINT; Schema: timer; Owner: root
--

ALTER TABLE ONLY timer.message
    ADD CONSTRAINT message_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: purge purge_pkey; Type: CONSTRAINT; Schema: timer; Owner: root
--

ALTER TABLE ONLY timer.purge
    ADD CONSTRAINT purge_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: username username_pkey; Type: CONSTRAINT; Schema: track; Owner: root
--

ALTER TABLE ONLY track.username
    ADD CONSTRAINT username_pkey PRIMARY KEY (username);


--
-- Name: vanity vanity_pkey; Type: CONSTRAINT; Schema: track; Owner: root
--

ALTER TABLE ONLY track.vanity
    ADD CONSTRAINT vanity_pkey PRIMARY KEY (vanity);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: transcribe; Owner: postgres
--

ALTER TABLE ONLY transcribe.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: rate_limit rate_limit_pkey; Type: CONSTRAINT; Schema: transcribe; Owner: postgres
--

ALTER TABLE ONLY transcribe.rate_limit
    ADD CONSTRAINT rate_limit_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: verification; Owner: postgres
--

ALTER TABLE ONLY verification.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: verification; Owner: postgres
--

ALTER TABLE ONLY verification.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: verification; Owner: postgres
--

ALTER TABLE ONLY verification.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (guild_id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: voice; Owner: root
--

ALTER TABLE ONLY voice.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: config config_guild_id_key; Type: CONSTRAINT; Schema: voice; Owner: root
--

ALTER TABLE ONLY voice.config
    ADD CONSTRAINT config_guild_id_key UNIQUE (guild_id);


--
-- Name: recordings recordings_pkey; Type: CONSTRAINT; Schema: voice; Owner: postgres
--

ALTER TABLE ONLY voice.recordings
    ADD CONSTRAINT recordings_pkey PRIMARY KEY (id);


--
-- Name: channels channels_pkey; Type: CONSTRAINT; Schema: voicemaster; Owner: postgres
--

ALTER TABLE ONLY voicemaster.channels
    ADD CONSTRAINT channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: configuration configuration_pkey; Type: CONSTRAINT; Schema: voicemaster; Owner: postgres
--

ALTER TABLE ONLY voicemaster.configuration
    ADD CONSTRAINT configuration_pkey PRIMARY KEY (guild_id);


--
-- Name: idx_invite_tracking_joined_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_invite_tracking_joined_at ON public.invite_tracking USING btree (guild_id, joined_at);


--
-- Name: mod_pkey; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX mod_pkey ON public.mod USING btree (guild_id, user_id);


--
-- Name: user_votes_time_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX user_votes_time_idx ON public.user_votes USING btree (last_vote_time);


--
-- Name: custom_commands_lookup_idx; Type: INDEX; Schema: stats; Owner: postgres
--

CREATE INDEX custom_commands_lookup_idx ON stats.custom_commands USING btree (guild_id, command);


--
-- Name: playlist_tracks playlist_tracks_guild_id_user_id_playlist_url_fkey; Type: FK CONSTRAINT; Schema: audio; Owner: postgres
--

ALTER TABLE ONLY audio.playlist_tracks
    ADD CONSTRAINT playlist_tracks_guild_id_user_id_playlist_url_fkey FOREIGN KEY (guild_id, user_id, playlist_url) REFERENCES audio.playlists(guild_id, user_id, playlist_url) ON DELETE CASCADE;


--
-- Name: albums albums_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.albums
    ADD CONSTRAINT albums_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: artists artists_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.artists
    ADD CONSTRAINT artists_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: crowns crowns_user_id_artist_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.crowns
    ADD CONSTRAINT crowns_user_id_artist_fkey FOREIGN KEY (user_id, artist) REFERENCES lastfm.artists(user_id, artist) ON DELETE CASCADE;


--
-- Name: tracks tracks_user_id_fkey; Type: FK CONSTRAINT; Schema: lastfm; Owner: root
--

ALTER TABLE ONLY lastfm.tracks
    ADD CONSTRAINT tracks_user_id_fkey FOREIGN KEY (user_id) REFERENCES lastfm.config(user_id) ON DELETE CASCADE;


--
-- Name: config config_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.config
    ADD CONSTRAINT config_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES public.settings(guild_id) ON DELETE CASCADE;


--
-- Name: member member_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.member
    ADD CONSTRAINT member_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: notification notification_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.notification
    ADD CONSTRAINT notification_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: role role_guild_id_fkey; Type: FK CONSTRAINT; Schema: level; Owner: root
--

ALTER TABLE ONLY level.role
    ADD CONSTRAINT role_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES level.config(guild_id) ON DELETE CASCADE;


--
-- Name: playlist_tracks playlist_tracks_playlist_id_fkey; Type: FK CONSTRAINT; Schema: music; Owner: postgres
--

ALTER TABLE ONLY music.playlist_tracks
    ADD CONSTRAINT playlist_tracks_playlist_id_fkey FOREIGN KEY (playlist_id) REFERENCES music.playlists(id) ON DELETE CASCADE;


--
-- Name: business_stats business_stats_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business_stats
    ADD CONSTRAINT business_stats_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(business_id);


--
-- Name: clownboard_entry clownboard_entry_guild_id_emoji_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clownboard_entry
    ADD CONSTRAINT clownboard_entry_guild_id_emoji_fkey FOREIGN KEY (guild_id, emoji) REFERENCES public.clownboard(guild_id, emoji) ON DELETE CASCADE;


--
-- Name: deck_cards deck_cards_deck_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.deck_cards
    ADD CONSTRAINT deck_cards_deck_id_fkey FOREIGN KEY (deck_id) REFERENCES public.user_decks(deck_id);


--
-- Name: employee_stats employee_stats_business_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employee_stats
    ADD CONSTRAINT employee_stats_business_id_fkey FOREIGN KEY (business_id) REFERENCES public.businesses(business_id);


--
-- Name: pet_adventures pet_adventures_pet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_adventures
    ADD CONSTRAINT pet_adventures_pet_id_fkey FOREIGN KEY (pet_id) REFERENCES public.pets(pet_id);


--
-- Name: pet_trades pet_trades_pet1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_trades
    ADD CONSTRAINT pet_trades_pet1_id_fkey FOREIGN KEY (pet1_id) REFERENCES public.pets(pet_id);


--
-- Name: pet_trades pet_trades_pet2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pet_trades
    ADD CONSTRAINT pet_trades_pet2_id_fkey FOREIGN KEY (pet2_id) REFERENCES public.pets(pet_id);


--
-- Name: poll_votes poll_votes_poll_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.poll_votes
    ADD CONSTRAINT poll_votes_poll_id_fkey FOREIGN KEY (poll_id) REFERENCES public.polls(poll_id) ON DELETE CASCADE;


--
-- Name: socials_details socials_details_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.socials_details
    ADD CONSTRAINT socials_details_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.socials(user_id) ON DELETE CASCADE;


--
-- Name: starboard_entry starboard_entry_guild_id_emoji_fkey; Type: FK CONSTRAINT; Schema: public; Owner: root
--

ALTER TABLE ONLY public.starboard_entry
    ADD CONSTRAINT starboard_entry_guild_id_emoji_fkey FOREIGN KEY (guild_id, emoji) REFERENCES public.starboard(guild_id, emoji) ON DELETE CASCADE;


--
-- Name: tag_aliases tag_aliases_guild_id_original_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tag_aliases
    ADD CONSTRAINT tag_aliases_guild_id_original_fkey FOREIGN KEY (guild_id, original) REFERENCES public.tags(guild_id, name) ON DELETE CASCADE;


--
-- Name: button button_guild_id_fkey; Type: FK CONSTRAINT; Schema: ticket; Owner: root
--

ALTER TABLE ONLY ticket.button
    ADD CONSTRAINT button_guild_id_fkey FOREIGN KEY (guild_id) REFERENCES ticket.config(guild_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

