--
-- PostgreSQL database dump
--

-- Dumped from database version 16.8 (Ubuntu 16.8-1.pgdg22.04+1)
-- Dumped by pg_dump version 16.8 (Ubuntu 16.8-1.pgdg22.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: activity_ignore; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_ignore (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.activity_ignore OWNER TO postgres;

--
-- Name: activity_joined; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_joined (
    guild_id bigint,
    user_id bigint,
    "timestamp" bigint
);


ALTER TABLE public.activity_joined OWNER TO postgres;

--
-- Name: activity_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_leaderboard (
    guild_id bigint NOT NULL,
    type text NOT NULL,
    range text NOT NULL,
    message_id bigint,
    channel_id bigint
);


ALTER TABLE public.activity_leaderboard OWNER TO postgres;

--
-- Name: activity_left; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_left (
    guild_id bigint,
    user_id bigint,
    "timestamp" bigint
);


ALTER TABLE public.activity_left OWNER TO postgres;

--
-- Name: activity_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_messages (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    server_id bigint NOT NULL,
    message_date date NOT NULL,
    message_count integer NOT NULL
);


ALTER TABLE public.activity_messages OWNER TO postgres;

--
-- Name: activity_timezone; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_timezone (
    guild_id bigint NOT NULL,
    timezone text
);


ALTER TABLE public.activity_timezone OWNER TO postgres;

--
-- Name: activity_voice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.activity_voice (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    server_id bigint NOT NULL,
    voice_date date NOT NULL,
    voice_time integer DEFAULT 0 NOT NULL
);


ALTER TABLE public.activity_voice OWNER TO postgres;

--
-- Name: afk; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.afk (
    user_id bigint,
    reason text,
    "time" timestamp with time zone
);

ALTER TABLE ONLY public.afk REPLICA IDENTITY FULL;


ALTER TABLE public.afk OWNER TO postgres;

--
-- Name: afk_fake; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.afk_fake (
    user_id bigint,
    reason text,
    "time" timestamp with time zone
);


ALTER TABLE public.afk_fake OWNER TO postgres;

--
-- Name: aliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.aliases (
    guild_id bigint NOT NULL,
    command text NOT NULL,
    alias text NOT NULL,
    args text
);

ALTER TABLE ONLY public.aliases REPLICA IDENTITY FULL;


ALTER TABLE public.aliases OWNER TO postgres;

--
-- Name: antinuke; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke (
    guild_id bigint NOT NULL,
    configured text,
    owner_id bigint,
    whitelisted jsonb,
    admins jsonb,
    logs bigint,
    staffs jsonb,
    whitelisted_roles jsonb
);

ALTER TABLE ONLY public.antinuke REPLICA IDENTITY FULL;


ALTER TABLE public.antinuke OWNER TO postgres;

--
-- Name: antinuke_linksedit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke_linksedit (
    guild_id bigint NOT NULL,
    users jsonb DEFAULT '[]'::jsonb,
    roles jsonb DEFAULT '[]'::jsonb,
    channels jsonb DEFAULT '[]'::jsonb,
    status boolean
);


ALTER TABLE public.antinuke_linksedit OWNER TO postgres;

--
-- Name: antinuke_modules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke_modules (
    guild_id bigint,
    module text,
    punishment text,
    threshold integer
);

ALTER TABLE ONLY public.antinuke_modules REPLICA IDENTITY FULL;


ALTER TABLE public.antinuke_modules OWNER TO postgres;

--
-- Name: antinuke_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke_roles (
    guild_id bigint NOT NULL,
    roles jsonb,
    status boolean DEFAULT false
);


ALTER TABLE public.antinuke_roles OWNER TO postgres;

--
-- Name: antiraid; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antiraid (
    guild_id bigint NOT NULL,
    configured text,
    whitelisted jsonb DEFAULT '[]'::jsonb,
    logs bigint
);


ALTER TABLE public.antiraid OWNER TO postgres;

--
-- Name: antiraid_age; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antiraid_age (
    guild_id bigint NOT NULL,
    punishment text,
    threshold bigint
);


ALTER TABLE public.antiraid_age OWNER TO postgres;

--
-- Name: antiraid_avatar; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antiraid_avatar (
    guild_id bigint NOT NULL,
    punishment text
);


ALTER TABLE public.antiraid_avatar OWNER TO postgres;

--
-- Name: antiraid_massjoin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antiraid_massjoin (
    guild_id bigint NOT NULL,
    punishment text,
    threshold bigint
);

ALTER TABLE ONLY public.antiraid_massjoin REPLICA IDENTITY FULL;


ALTER TABLE public.antiraid_massjoin OWNER TO postgres;

--
-- Name: api_key; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_key (
    user_id bigint NOT NULL,
    key text,
    role text
);

ALTER TABLE ONLY public.api_key REPLICA IDENTITY FULL;


ALTER TABLE public.api_key OWNER TO postgres;

--
-- Name: appeals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.appeals (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.appeals OWNER TO postgres;

--
-- Name: application_responses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.application_responses (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    application_name text NOT NULL,
    responses jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    id bigint,
    upvotes integer DEFAULT 0,
    downvotes integer DEFAULT 0
);


ALTER TABLE public.application_responses OWNER TO postgres;

--
-- Name: application_votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.application_votes (
    message_id bigint NOT NULL,
    user_id bigint NOT NULL,
    vote smallint
);


ALTER TABLE public.application_votes OWNER TO postgres;

--
-- Name: applications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.applications (
    guild_id bigint NOT NULL,
    channel_id bigint,
    name text NOT NULL,
    questions text[] DEFAULT ARRAY[]::text[],
    status boolean DEFAULT true,
    roles jsonb DEFAULT '[]'::jsonb,
    level bigint DEFAULT '0'::bigint
);


ALTER TABLE public.applications OWNER TO postgres;

--
-- Name: authorized; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authorized (
    guild_id bigint NOT NULL,
    owner_id bigint,
    "timestamp" bigint
);


ALTER TABLE public.authorized OWNER TO postgres;

--
-- Name: automod_repeat; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.automod_repeat (
    guild_id bigint,
    rate integer,
    timeout bigint,
    users text,
    channels text,
    roles text,
    message boolean DEFAULT true
);


ALTER TABLE public.automod_repeat OWNER TO postgres;

--
-- Name: automod_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.automod_rules (
    guild_id bigint,
    mode text,
    rule_id bigint
);

ALTER TABLE ONLY public.automod_rules REPLICA IDENTITY FULL;


ALTER TABLE public.automod_rules OWNER TO postgres;

--
-- Name: automod_spam; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.automod_spam (
    guild_id bigint,
    rate integer,
    timeout bigint,
    users text,
    channels text,
    roles text,
    message boolean DEFAULT true
);

ALTER TABLE ONLY public.automod_spam REPLICA IDENTITY FULL;


ALTER TABLE public.automod_spam OWNER TO postgres;

--
-- Name: autopost; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost (
    guild_id bigint NOT NULL,
    type text NOT NULL,
    category text NOT NULL,
    channel_id bigint,
    webhook_name text,
    webhook_avatar text
);


ALTER TABLE public.autopost OWNER TO postgres;

--
-- Name: autopost_instagram; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_instagram (
    guild_id bigint NOT NULL,
    channel_id bigint,
    message text,
    username text NOT NULL
);


ALTER TABLE public.autopost_instagram OWNER TO postgres;

--
-- Name: autopost_instagram_announced; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_instagram_announced (
    channel_id bigint NOT NULL,
    post_id text NOT NULL
);


ALTER TABLE public.autopost_instagram_announced OWNER TO postgres;

--
-- Name: autopost_tiktok; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_tiktok (
    guild_id bigint NOT NULL,
    channel_id bigint,
    message text,
    username text NOT NULL
);


ALTER TABLE public.autopost_tiktok OWNER TO postgres;

--
-- Name: autopost_tiktok_announced; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_tiktok_announced (
    channel_id bigint NOT NULL,
    video_id text NOT NULL
);


ALTER TABLE public.autopost_tiktok_announced OWNER TO postgres;

--
-- Name: autopost_twitch; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_twitch (
    guild_id bigint NOT NULL,
    channel_id bigint,
    message text,
    streamer text NOT NULL
);

ALTER TABLE ONLY public.autopost_twitch REPLICA IDENTITY FULL;


ALTER TABLE public.autopost_twitch OWNER TO postgres;

--
-- Name: autopost_twitch_announced; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_twitch_announced (
    channel_id bigint NOT NULL,
    stream_id text NOT NULL
);


ALTER TABLE public.autopost_twitch_announced OWNER TO postgres;

--
-- Name: autopost_twitter; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_twitter (
    guild_id bigint NOT NULL,
    channel_id bigint,
    message text,
    username text NOT NULL
);


ALTER TABLE public.autopost_twitter OWNER TO postgres;

--
-- Name: autopost_twitter_announced; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_twitter_announced (
    channel_id bigint NOT NULL,
    tweet_id text NOT NULL
);


ALTER TABLE public.autopost_twitter_announced OWNER TO postgres;

--
-- Name: autopost_youtube; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_youtube (
    guild_id bigint NOT NULL,
    channel_id bigint,
    message text,
    username text NOT NULL
);


ALTER TABLE public.autopost_youtube OWNER TO postgres;

--
-- Name: autopost_youtube_announced; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopost_youtube_announced (
    channel_id bigint NOT NULL,
    video_id text NOT NULL
);


ALTER TABLE public.autopost_youtube_announced OWNER TO postgres;

--
-- Name: autopublish; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autopublish (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.autopublish OWNER TO postgres;

--
-- Name: autoreact; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoreact (
    guild_id bigint NOT NULL,
    trigger text NOT NULL,
    reactions text NOT NULL
);

ALTER TABLE ONLY public.autoreact REPLICA IDENTITY FULL;


ALTER TABLE public.autoreact OWNER TO postgres;

--
-- Name: autoreact_channel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoreact_channel (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    reactions jsonb NOT NULL
);


ALTER TABLE public.autoreact_channel OWNER TO postgres;

--
-- Name: autoresponder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoresponder (
    guild_id bigint,
    trigger text,
    response text,
    strict boolean DEFAULT true,
    delete boolean DEFAULT false,
    reply boolean DEFAULT false
);

ALTER TABLE ONLY public.autoresponder REPLICA IDENTITY FULL;


ALTER TABLE public.autoresponder OWNER TO postgres;

--
-- Name: autoresponder_permissions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoresponder_permissions (
    guild_id bigint NOT NULL,
    trigger text NOT NULL,
    state text NOT NULL,
    data jsonb NOT NULL
);


ALTER TABLE public.autoresponder_permissions OWNER TO postgres;

--
-- Name: autorole; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autorole (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);

ALTER TABLE ONLY public.autorole REPLICA IDENTITY FULL;


ALTER TABLE public.autorole OWNER TO postgres;

--
-- Name: autorole_bots; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autorole_bots (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.autorole_bots OWNER TO postgres;

--
-- Name: autorole_humans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autorole_humans (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.autorole_humans OWNER TO postgres;

--
-- Name: autothread; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autothread (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.autothread OWNER TO postgres;

--
-- Name: avatar_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_history (
    user_id bigint,
    avatar text NOT NULL,
    "timestamp" bigint
);


ALTER TABLE public.avatar_history OWNER TO postgres;

--
-- Name: avatar_privacy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_privacy (
    user_id bigint NOT NULL,
    status boolean DEFAULT false
);


ALTER TABLE public.avatar_privacy OWNER TO postgres;

--
-- Name: beta_testers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.beta_testers (
    user_id bigint NOT NULL
);


ALTER TABLE public.beta_testers OWNER TO postgres;

--
-- Name: bio; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bio (
    username text NOT NULL,
    displayname text,
    user_id bigint,
    description text,
    avatar_url text,
    background_url text,
    audio_url text,
    border_color text,
    color text,
    text_color text,
    gradient boolean DEFAULT false,
    gradient_1 text,
    gradient_2 text
);


ALTER TABLE public.bio OWNER TO postgres;

--
-- Name: birthday; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.birthday (
    user_id bigint NOT NULL,
    month integer,
    day integer,
    year integer
);

ALTER TABLE ONLY public.birthday REPLICA IDENTITY FULL;


ALTER TABLE public.birthday OWNER TO postgres;

--
-- Name: birthday_reward; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.birthday_reward (
    guild_id bigint NOT NULL,
    role_id bigint
);


ALTER TABLE public.birthday_reward OWNER TO postgres;

--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist (
    id bigint NOT NULL,
    type text NOT NULL,
    reason text,
    "time" bigint,
    "user" bigint
);

ALTER TABLE ONLY public.blacklist REPLICA IDENTITY FULL;


ALTER TABLE public.blacklist OWNER TO postgres;

--
-- Name: blacklist_cog; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_cog (
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    cog text NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_cog OWNER TO postgres;

--
-- Name: blacklist_cog_server; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_cog_server (
    guild_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    cog text NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_cog_server OWNER TO postgres;

--
-- Name: blacklist_command; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_command (
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    command text NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_command OWNER TO postgres;

--
-- Name: blacklist_command_server; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_command_server (
    guild_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    command text NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_command_server OWNER TO postgres;

--
-- Name: blacklist_server; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_server (
    guild_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_server OWNER TO postgres;

--
-- Name: blacklist_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist_user (
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    duration bigint,
    reason text NOT NULL,
    "timestamp" bigint NOT NULL
);


ALTER TABLE public.blacklist_user OWNER TO postgres;

--
-- Name: boost; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.boost (
    guild_id bigint,
    channel_id bigint,
    message text
);

ALTER TABLE ONLY public.boost REPLICA IDENTITY FULL;


ALTER TABLE public.boost OWNER TO postgres;

--
-- Name: booster_allow; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_allow (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.booster_allow OWNER TO postgres;

--
-- Name: booster_award; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_award (
    guild_id bigint,
    role_id bigint
);

ALTER TABLE ONLY public.booster_award REPLICA IDENTITY FULL;


ALTER TABLE public.booster_award OWNER TO postgres;

--
-- Name: booster_blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_blacklist (
    guild_id bigint,
    user_id bigint,
    reason text
);


ALTER TABLE public.booster_blacklist OWNER TO postgres;

--
-- Name: booster_lost; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_lost (
    guild_id bigint,
    user_id bigint,
    "time" bigint
);


ALTER TABLE public.booster_lost OWNER TO postgres;

--
-- Name: booster_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_module (
    guild_id bigint,
    base bigint,
    banned_words text DEFAULT '[]'::text,
    share_enabled boolean DEFAULT false,
    share_limit bigint DEFAULT '1'::bigint,
    "limit" bigint DEFAULT '0'::bigint
);

ALTER TABLE ONLY public.booster_module REPLICA IDENTITY FULL;


ALTER TABLE public.booster_module OWNER TO postgres;

--
-- Name: booster_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_roles (
    guild_id bigint,
    user_id bigint,
    role_id bigint,
    shared_users jsonb DEFAULT '[]'::jsonb
);

ALTER TABLE ONLY public.booster_roles REPLICA IDENTITY FULL;


ALTER TABLE public.booster_roles OWNER TO postgres;

--
-- Name: bugreports; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bugreports (
    "case" text,
    user_id bigint,
    moderator_id bigint,
    reason text,
    "timestamp" bigint
);


ALTER TABLE public.bugreports OWNER TO postgres;

--
-- Name: bumpreminder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bumpreminder (
    guild_id bigint,
    channel_id bigint,
    user_id bigint,
    thankyou text,
    reminder text,
    "time" timestamp with time zone
);

ALTER TABLE ONLY public.bumpreminder REPLICA IDENTITY FULL;


ALTER TABLE public.bumpreminder OWNER TO postgres;

--
-- Name: bumpreminder_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bumpreminder_leaderboard (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    bumps bigint
);


ALTER TABLE public.bumpreminder_leaderboard OWNER TO postgres;

--
-- Name: business; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business (
    id bigint NOT NULL,
    name character varying(255) NOT NULL,
    statevalue double precision NOT NULL,
    owner bigint,
    hourrevenue double precision NOT NULL,
    balance double precision DEFAULT 0 NOT NULL,
    paid bigint DEFAULT '0'::bigint,
    last_collected bigint DEFAULT '0'::bigint,
    reminder boolean DEFAULT true,
    reminded boolean DEFAULT false
);

ALTER TABLE ONLY public.business REPLICA IDENTITY FULL;


ALTER TABLE public.business OWNER TO postgres;

--
-- Name: business_auction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.business_auction (
    id bigint DEFAULT '0'::bigint,
    name text,
    start_bid_amount double precision DEFAULT '0'::double precision,
    active_bid_user bigint DEFAULT '0'::bigint,
    active_bid_amount double precision DEFAULT '0'::double precision,
    ends bigint DEFAULT '0'::bigint
);

ALTER TABLE ONLY public.business_auction REPLICA IDENTITY FULL;


ALTER TABLE public.business_auction OWNER TO postgres;

--
-- Name: button_message; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.button_message (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    button_id text NOT NULL,
    embed text NOT NULL,
    label text,
    emoji text
);


ALTER TABLE public.button_message OWNER TO postgres;

--
-- Name: button_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.button_role (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    button_id text NOT NULL,
    role_id bigint NOT NULL,
    label text,
    emoji text
);

ALTER TABLE ONLY public.button_role REPLICA IDENTITY FULL;


ALTER TABLE public.button_role OWNER TO postgres;

--
-- Name: button_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.button_settings (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    "unique" boolean DEFAULT false
);


ALTER TABLE public.button_settings OWNER TO postgres;

--
-- Name: channel_disabled_commands; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channel_disabled_commands (
    guild_id bigint,
    channel_id bigint,
    cmd text
);

ALTER TABLE ONLY public.channel_disabled_commands REPLICA IDENTITY FULL;


ALTER TABLE public.channel_disabled_commands OWNER TO postgres;

--
-- Name: channel_disabled_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.channel_disabled_module (
    guild_id bigint,
    channel_id bigint,
    module text
);

ALTER TABLE ONLY public.channel_disabled_module REPLICA IDENTITY FULL;


ALTER TABLE public.channel_disabled_module OWNER TO postgres;

--
-- Name: checkout; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.checkout (
    message bigint,
    amount text
);


ALTER TABLE public.checkout OWNER TO postgres;

--
-- Name: company_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_requests (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    company_id integer NOT NULL,
    text text NOT NULL,
    created bigint NOT NULL
);

ALTER TABLE ONLY public.company_requests REPLICA IDENTITY FULL;


ALTER TABLE public.company_requests OWNER TO postgres;

--
-- Name: clan_requests_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.clan_requests_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clan_requests_id_seq OWNER TO postgres;

--
-- Name: clan_requests_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.clan_requests_id_seq OWNED BY public.company_requests.id;


--
-- Name: company; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    ceo bigint NOT NULL,
    members bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    privacy character varying(20) DEFAULT 'public'::character varying NOT NULL,
    roles jsonb DEFAULT '{}'::jsonb NOT NULL,
    level bigint DEFAULT '1'::bigint,
    vault double precision DEFAULT '0'::double precision,
    reputation bigint DEFAULT '0'::bigint,
    votes bigint DEFAULT '0'::bigint,
    tag text,
    created bigint DEFAULT '0'::bigint,
    description text,
    icon text,
    vault_limit double precision DEFAULT '0'::double precision
);

ALTER TABLE ONLY public.company REPLICA IDENTITY FULL;


ALTER TABLE public.company OWNER TO postgres;

--
-- Name: clans_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.clans_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.clans_id_seq OWNER TO postgres;

--
-- Name: clans_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.clans_id_seq OWNED BY public.company.id;


--
-- Name: clashofclans; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clashofclans (
    user_id bigint NOT NULL,
    tag text
);


ALTER TABLE public.clashofclans OWNER TO postgres;

--
-- Name: clownboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clownboard (
    guild_id bigint,
    channel_id bigint,
    emoji text,
    count integer
);


ALTER TABLE public.clownboard OWNER TO postgres;

--
-- Name: clownboard_ignored; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clownboard_ignored (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.clownboard_ignored OWNER TO postgres;

--
-- Name: clownboard_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.clownboard_messages (
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    clownboard_message_id bigint
);


ALTER TABLE public.clownboard_messages OWNER TO postgres;

--
-- Name: color_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.color_module (
    guild_id bigint,
    base bigint
);

ALTER TABLE ONLY public.color_module REPLICA IDENTITY FULL;


ALTER TABLE public.color_module OWNER TO postgres;

--
-- Name: color_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.color_roles (
    guild_id bigint,
    role_id bigint,
    color text
);

ALTER TABLE ONLY public.color_roles REPLICA IDENTITY FULL;


ALTER TABLE public.color_roles OWNER TO postgres;

--
-- Name: command_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.command_history (
    id integer NOT NULL,
    command text,
    arguments text,
    server_id bigint,
    user_id bigint,
    channel_id bigint,
    "timestamp" bigint
);

ALTER TABLE ONLY public.command_history REPLICA IDENTITY FULL;


ALTER TABLE public.command_history OWNER TO postgres;

--
-- Name: command_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.command_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.command_history_id_seq OWNER TO postgres;

--
-- Name: command_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.command_history_id_seq OWNED BY public.command_history.id;


--
-- Name: command_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.command_stats (
    id integer NOT NULL,
    command character varying(255) NOT NULL,
    user_id bigint NOT NULL,
    guild_id bigint,
    channel_id bigint NOT NULL,
    execution_time double precision NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.command_stats OWNER TO postgres;

--
-- Name: command_stats_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.command_stats_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.command_stats_id_seq OWNER TO postgres;

--
-- Name: command_stats_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.command_stats_id_seq OWNED BY public.command_stats.id;


--
-- Name: company_earnings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_earnings (
    user_id bigint NOT NULL,
    company_id integer NOT NULL,
    amount double precision
);


ALTER TABLE public.company_earnings OWNER TO postgres;

--
-- Name: company_invites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_invites (
    user_id bigint,
    company_id bigint,
    message_id bigint,
    created bigint
);


ALTER TABLE public.company_invites OWNER TO postgres;

--
-- Name: company_limit_bonus; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_limit_bonus (
    user_id bigint NOT NULL,
    spent double precision,
    date date NOT NULL
);


ALTER TABLE public.company_limit_bonus OWNER TO postgres;

--
-- Name: company_limit_withdraw; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_limit_withdraw (
    user_id bigint NOT NULL,
    spent double precision,
    date date NOT NULL
);


ALTER TABLE public.company_limit_withdraw OWNER TO postgres;

--
-- Name: company_projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_projects (
    "group" bigint,
    name text,
    cost bigint,
    votes bigint,
    earnings bigint,
    reputation bigint,
    description text,
    emoji text,
    image text
);


ALTER TABLE public.company_projects OWNER TO postgres;

--
-- Name: company_projects_started; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_projects_started (
    company_id integer NOT NULL,
    project_name text NOT NULL,
    money double precision NOT NULL,
    votes integer DEFAULT 0 NOT NULL,
    active boolean NOT NULL,
    participant jsonb DEFAULT '{}'::jsonb NOT NULL,
    created bigint NOT NULL
);


ALTER TABLE public.company_projects_started OWNER TO postgres;

--
-- Name: company_upgrades; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_upgrades (
    level bigint,
    cost bigint,
    vault bigint,
    members bigint,
    reputation bigint,
    projects bigint,
    earnings bigint,
    managers bigint,
    bonus bigint
);


ALTER TABLE public.company_upgrades OWNER TO postgres;

--
-- Name: company_vault; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_vault (
    company_id integer,
    user_id bigint,
    amount double precision,
    type text,
    created bigint
);


ALTER TABLE public.company_vault OWNER TO postgres;

--
-- Name: company_voters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.company_voters (
    user_id bigint NOT NULL,
    company_id integer NOT NULL,
    votes bigint
);


ALTER TABLE public.company_voters OWNER TO postgres;

--
-- Name: confess; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess (
    guild_id bigint,
    channel_id bigint,
    confession integer
);


ALTER TABLE public.confess OWNER TO postgres;

--
-- Name: confess_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_members (
    guild_id bigint,
    user_id bigint,
    confession bigint
);


ALTER TABLE public.confess_members OWNER TO postgres;

--
-- Name: confess_mute; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.confess_mute (
    guild_id bigint,
    user_id bigint,
    confession bigint
);


ALTER TABLE public.confess_mute OWNER TO postgres;

--
-- Name: counters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.counters (
    guild_id bigint,
    channel_type text,
    channel_id bigint,
    channel_name text,
    module text,
    role_id bigint
);

ALTER TABLE ONLY public.counters REPLICA IDENTITY FULL;


ALTER TABLE public.counters OWNER TO postgres;

--
-- Name: donor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donor (
    user_id bigint,
    since bigint,
    status text
);

ALTER TABLE ONLY public.donor REPLICA IDENTITY FULL;


ALTER TABLE public.donor OWNER TO postgres;

--
-- Name: economy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy (
    user_id bigint DEFAULT '0'::bigint NOT NULL,
    cash double precision DEFAULT '0'::double precision,
    card double precision DEFAULT '0'::double precision,
    daily bigint DEFAULT '0'::bigint,
    daily_streak bigint DEFAULT 0,
    rob bigint DEFAULT '0'::bigint,
    work bigint DEFAULT '0'::bigint,
    bonus bigint DEFAULT '0'::bigint,
    item_bank bigint DEFAULT '50000'::bigint,
    slut bigint DEFAULT '0'::bigint,
    item_booster bigint DEFAULT '0'::bigint,
    item_booster_until bigint DEFAULT '0'::bigint,
    quest bigint DEFAULT '0'::bigint,
    item_case bigint DEFAULT '0'::bigint,
    beg bigint DEFAULT '0'::bigint,
    terms boolean DEFAULT false,
    item_case_blackice bigint DEFAULT '0'::bigint
);

ALTER TABLE ONLY public.economy REPLICA IDENTITY FULL;


ALTER TABLE public.economy OWNER TO postgres;

--
-- Name: economy_business; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_business (
    user_id bigint NOT NULL,
    last_collected bigint,
    business_id bigint
);


ALTER TABLE public.economy_business OWNER TO postgres;

--
-- Name: economy_business_list; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_business_list (
    name text,
    cost bigint,
    earnings bigint,
    description text,
    emoji text,
    image text,
    business_id bigint
);


ALTER TABLE public.economy_business_list OWNER TO postgres;

--
-- Name: economy_cards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_cards (
    id bigint,
    name text,
    stars bigint,
    image text,
    business text DEFAULT 'business'::text
);


ALTER TABLE public.economy_cards OWNER TO postgres;

--
-- Name: economy_cards_used; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_cards_used (
    user_id bigint,
    card_id bigint,
    business text
);


ALTER TABLE public.economy_cards_used OWNER TO postgres;

--
-- Name: economy_cards_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_cards_user (
    id bigint,
    user_id bigint,
    card_id bigint NOT NULL,
    business text,
    storage bigint,
    multiplier double precision,
    image text,
    active boolean DEFAULT true,
    background text DEFAULT 'standard'::text
);


ALTER TABLE public.economy_cards_user OWNER TO postgres;

--
-- Name: economy_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_config (
    id bigint DEFAULT '0'::bigint,
    active boolean DEFAULT false,
    bonus_min bigint DEFAULT '0'::bigint,
    bonus_max bigint DEFAULT '0'::bigint,
    work_min bigint DEFAULT '0'::bigint,
    work_max bigint DEFAULT '0'::bigint,
    slut_min bigint DEFAULT '0'::bigint,
    slut_max bigint DEFAULT '0'::bigint,
    daily_min bigint DEFAULT '0'::bigint,
    daily_max bigint DEFAULT '0'::bigint,
    vote bigint DEFAULT '0'::bigint,
    beg_min bigint,
    beg_max bigint
);


ALTER TABLE public.economy_config OWNER TO postgres;

--
-- Name: economy_investments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_investments (
    id bigint NOT NULL,
    name text,
    cost double precision,
    earnings double precision,
    days bigint,
    description text
);


ALTER TABLE public.economy_investments OWNER TO postgres;

--
-- Name: economy_investments_started; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_investments_started (
    id bigint,
    user_id bigint,
    "timestamp" bigint,
    active boolean DEFAULT true
);


ALTER TABLE public.economy_investments_started OWNER TO postgres;

--
-- Name: economy_lab; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_lab (
    user_id bigint NOT NULL,
    ampoules integer DEFAULT 0,
    last_collected bigint DEFAULT 0,
    upgrade_state integer DEFAULT 0,
    name text DEFAULT 'Lab'::text
);


ALTER TABLE public.economy_lab OWNER TO postgres;

--
-- Name: economy_limit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_limit (
    user_id bigint NOT NULL,
    spent double precision NOT NULL,
    date date NOT NULL
);


ALTER TABLE public.economy_limit OWNER TO postgres;

--
-- Name: economy_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_logs (
    user_id bigint,
    amount double precision,
    action text,
    type text,
    created bigint,
    cash double precision DEFAULT '0'::double precision,
    card double precision DEFAULT '0'::double precision
);


ALTER TABLE public.economy_logs OWNER TO postgres;

--
-- Name: economy_logs_business; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_logs_business (
    user_id bigint,
    moderator_id bigint,
    amount double precision,
    action text,
    business bigint,
    created bigint
);


ALTER TABLE public.economy_logs_business OWNER TO postgres;

--
-- Name: economy_logs_lab; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_logs_lab (
    user_id bigint,
    moderator_id bigint,
    amount double precision,
    action text,
    upgrade_state bigint,
    created bigint
);


ALTER TABLE public.economy_logs_lab OWNER TO postgres;

--
-- Name: economy_logs_wipe; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_logs_wipe (
    user_id bigint,
    cash double precision,
    card double precision,
    bank bigint,
    lab bigint,
    business bigint,
    created bigint,
    moderator_id bigint
);


ALTER TABLE public.economy_logs_wipe OWNER TO postgres;

--
-- Name: economy_shop; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_shop (
    guild_id bigint,
    state boolean
);


ALTER TABLE public.economy_shop OWNER TO postgres;

--
-- Name: economy_shop_earnings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_shop_earnings (
    guild_id bigint NOT NULL,
    amount double precision DEFAULT '0'::double precision
);


ALTER TABLE public.economy_shop_earnings OWNER TO postgres;

--
-- Name: economy_shop_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy_shop_items (
    guild_id bigint,
    role_id bigint,
    amount double precision,
    name text,
    "limit" bigint,
    "time" bigint
);


ALTER TABLE public.economy_shop_items OWNER TO postgres;

--
-- Name: embeds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.embeds (
    code character varying NOT NULL,
    embed text,
    user_id bigint
);

ALTER TABLE ONLY public.embeds REPLICA IDENTITY FULL;


ALTER TABLE public.embeds OWNER TO postgres;

--
-- Name: embeds_creator; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.embeds_creator (
    user_id bigint
);


ALTER TABLE public.embeds_creator OWNER TO postgres;

--
-- Name: embeds_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.embeds_templates (
    id integer NOT NULL,
    name text,
    user_id bigint,
    code text,
    embed text,
    image text
);


ALTER TABLE public.embeds_templates OWNER TO postgres;

--
-- Name: embeds_templates_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.embeds_templates_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.embeds_templates_id_seq OWNER TO postgres;

--
-- Name: embeds_templates_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.embeds_templates_id_seq OWNED BY public.embeds_templates.id;


--
-- Name: error_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.error_codes (
    code character varying(30) NOT NULL,
    info json
);

ALTER TABLE ONLY public.error_codes REPLICA IDENTITY FULL;


ALTER TABLE public.error_codes OWNER TO postgres;

--
-- Name: fake_perms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fake_perms (
    guild_id bigint,
    role_id bigint,
    perms text
);

ALTER TABLE ONLY public.fake_perms REPLICA IDENTITY FULL;


ALTER TABLE public.fake_perms OWNER TO postgres;

--
-- Name: force_nick; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.force_nick (
    guild_id bigint,
    user_id bigint,
    nickname text
);

ALTER TABLE ONLY public.force_nick REPLICA IDENTITY FULL;


ALTER TABLE public.force_nick OWNER TO postgres;

--
-- Name: freegames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.freegames (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    already_posted text DEFAULT '[]'::text
);


ALTER TABLE public.freegames OWNER TO postgres;

--
-- Name: gamestats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gamestats (
    user_id bigint NOT NULL,
    game text NOT NULL,
    wins integer,
    loses integer,
    ties integer,
    total integer
);

ALTER TABLE ONLY public.gamestats REPLICA IDENTITY FULL;


ALTER TABLE public.gamestats OWNER TO postgres;

--
-- Name: giveaway; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.giveaway (
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    winners integer,
    members text,
    finish timestamp with time zone,
    host bigint,
    title text,
    required_role bigint,
    required_bonus bigint,
    required_messages bigint,
    required_level bigint,
    required_invites bigint,
    required_ignore bigint
);

ALTER TABLE ONLY public.giveaway REPLICA IDENTITY FULL;


ALTER TABLE public.giveaway OWNER TO postgres;

--
-- Name: giveaway_ended; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.giveaway_ended (
    channel_id bigint,
    message_id bigint,
    members text
);

ALTER TABLE ONLY public.giveaway_ended REPLICA IDENTITY FULL;


ALTER TABLE public.giveaway_ended OWNER TO postgres;

--
-- Name: global_beta_commands; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.global_beta_commands (
    command character varying(30) NOT NULL,
    status boolean NOT NULL,
    "user" bigint NOT NULL,
    "time" bigint NOT NULL
);


ALTER TABLE public.global_beta_commands OWNER TO postgres;

--
-- Name: global_disabled_commands; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.global_disabled_commands (
    command character varying(30) NOT NULL,
    status boolean,
    "user" bigint,
    reason text,
    "time" bigint
);

ALTER TABLE ONLY public.global_disabled_commands REPLICA IDENTITY FULL;


ALTER TABLE public.global_disabled_commands OWNER TO postgres;

--
-- Name: globalban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.globalban (
    user_id bigint,
    reason text
);

ALTER TABLE ONLY public.globalban REPLICA IDENTITY FULL;


ALTER TABLE public.globalban OWNER TO postgres;

--
-- Name: growth; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.growth (
    guilds bigint NOT NULL,
    users bigint NOT NULL,
    ping bigint NOT NULL,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.growth OWNER TO postgres;

--
-- Name: guessthenumber; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guessthenumber (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    number bigint
);


ALTER TABLE public.guessthenumber OWNER TO postgres;

--
-- Name: guessthenumber_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guessthenumber_settings (
    guild_id bigint NOT NULL,
    lock boolean
);


ALTER TABLE public.guessthenumber_settings OWNER TO postgres;

--
-- Name: guild_cache; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild_cache (
    guild_id bigint NOT NULL,
    name text NOT NULL,
    cached_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.guild_cache OWNER TO postgres;

--
-- Name: guild_disabled_commands; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild_disabled_commands (
    guild_id bigint,
    cmd text
);

ALTER TABLE ONLY public.guild_disabled_commands REPLICA IDENTITY FULL;


ALTER TABLE public.guild_disabled_commands OWNER TO postgres;

--
-- Name: guild_disabled_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild_disabled_module (
    guild_id bigint NOT NULL,
    module text NOT NULL
);

ALTER TABLE ONLY public.guild_disabled_module REPLICA IDENTITY FULL;


ALTER TABLE public.guild_disabled_module OWNER TO postgres;

--
-- Name: guild_names; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guild_names (
    guild_id bigint NOT NULL,
    guild_name text
);


ALTER TABLE public.guild_names OWNER TO postgres;

--
-- Name: guildnames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guildnames (
    guild_id bigint,
    guild_name text,
    "time" bigint
);


ALTER TABLE public.guildnames OWNER TO postgres;

--
-- Name: guns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.guns (
    user_id bigint NOT NULL,
    uid bigint
);


ALTER TABLE public.guns OWNER TO postgres;

--
-- Name: hardban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hardban (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    reason text,
    moderator_id bigint NOT NULL
);

ALTER TABLE ONLY public.hardban REPLICA IDENTITY FULL;


ALTER TABLE public.hardban OWNER TO postgres;

--
-- Name: history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.history (
    id bigint NOT NULL,
    user_id bigint NOT NULL,
    moderator_id bigint NOT NULL,
    server_id bigint NOT NULL,
    punishment character varying(128) NOT NULL,
    duration character varying(128) NOT NULL,
    reason character varying(512) NOT NULL,
    "time" bigint,
    guild_id bigint NOT NULL,
    proof character varying,
    appeal_id bigint,
    appeal_msg text,
    appeal_msg_id bigint
);

ALTER TABLE ONLY public.history REPLICA IDENTITY FULL;


ALTER TABLE public.history OWNER TO postgres;

--
-- Name: history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.history_id_seq OWNER TO postgres;

--
-- Name: history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.history_id_seq OWNED BY public.history.id;


--
-- Name: instance; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.instance (
    user_id bigint,
    status text,
    paid bigint,
    owner_id bigint,
    guild_id bigint,
    transfers bigint DEFAULT '3'::bigint
);


ALTER TABLE public.instance OWNER TO postgres;

--
-- Name: instance_addon; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.instance_addon (
    user_id bigint,
    paid bigint,
    owner_id bigint,
    guild_id bigint
);


ALTER TABLE public.instance_addon OWNER TO postgres;

--
-- Name: invites; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invites (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    regular_count bigint DEFAULT 0,
    left_count bigint DEFAULT 0,
    fake_count bigint DEFAULT 0,
    bonus bigint DEFAULT 0
);


ALTER TABLE public.invites OWNER TO postgres;

--
-- Name: invites_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invites_rewards (
    guild_id bigint NOT NULL,
    threshold integer NOT NULL,
    role_id bigint
);


ALTER TABLE public.invites_rewards OWNER TO postgres;

--
-- Name: invites_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invites_settings (
    guild_id bigint NOT NULL,
    fake_threshold integer DEFAULT 3,
    message text,
    logs bigint,
    autoupdate boolean DEFAULT false
);


ALTER TABLE public.invites_settings OWNER TO postgres;

--
-- Name: invites_users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invites_users (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    inviter_id bigint,
    invite_code text,
    "timestamp" bigint
);


ALTER TABLE public.invites_users OWNER TO postgres;

--
-- Name: invoices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoices (
    id integer NOT NULL,
    user_id character varying(255),
    invoice_id character varying(50),
    session_id character varying(255),
    plan character varying(50) NOT NULL,
    servers integer DEFAULT 1,
    payment_status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.invoices OWNER TO postgres;

--
-- Name: invoices_authorizations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoices_authorizations (
    id integer NOT NULL,
    invoice_id character varying(50) NOT NULL,
    guild_id bigint NOT NULL,
    authorized_at bigint NOT NULL
);


ALTER TABLE public.invoices_authorizations OWNER TO postgres;

--
-- Name: invoices_authorizations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.invoices_authorizations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoices_authorizations_id_seq OWNER TO postgres;

--
-- Name: invoices_authorizations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.invoices_authorizations_id_seq OWNED BY public.invoices_authorizations.id;


--
-- Name: invoices_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.invoices_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.invoices_id_seq OWNER TO postgres;

--
-- Name: invoices_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.invoices_id_seq OWNED BY public.invoices.id;


--
-- Name: invoke_dm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoke_dm (
    guild_id bigint,
    command text,
    embed text
);


ALTER TABLE public.invoke_dm OWNER TO postgres;

--
-- Name: invoke_message; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoke_message (
    guild_id bigint,
    command text,
    embed text
);

ALTER TABLE ONLY public.invoke_message REPLICA IDENTITY FULL;


ALTER TABLE public.invoke_message OWNER TO postgres;

--
-- Name: jail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jail (
    guild_id bigint,
    channel_id bigint,
    role_id bigint
);

ALTER TABLE ONLY public.jail REPLICA IDENTITY FULL;


ALTER TABLE public.jail OWNER TO postgres;

--
-- Name: jail_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jail_members (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    roles text,
    jailed_at timestamp with time zone,
    jailed_until timestamp with time zone
);

ALTER TABLE ONLY public.jail_members REPLICA IDENTITY FULL;


ALTER TABLE public.jail_members OWNER TO postgres;

--
-- Name: joindm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.joindm (
    guild_id bigint,
    message text
);


ALTER TABLE public.joindm OWNER TO postgres;

--
-- Name: language; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.language (
    user_id bigint NOT NULL,
    languages jsonb DEFAULT '[]'::jsonb NOT NULL
);


ALTER TABLE public.language OWNER TO postgres;

--
-- Name: language_translate; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.language_translate (
    user_id bigint,
    lang text,
    ephemeral boolean DEFAULT true
);


ALTER TABLE public.language_translate OWNER TO postgres;

--
-- Name: lastfm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lastfm (
    user_id bigint,
    username text,
    reactions text,
    customcmd text,
    embed text,
    reply boolean DEFAULT false
);

ALTER TABLE ONLY public.lastfm REPLICA IDENTITY FULL;


ALTER TABLE public.lastfm OWNER TO postgres;

--
-- Name: lastfm_crowns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lastfm_crowns (
    artist text NOT NULL,
    user_id bigint
);


ALTER TABLE public.lastfm_crowns OWNER TO postgres;

--
-- Name: leave; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leave (
    guild_id bigint,
    channel_id bigint,
    message text
);

ALTER TABLE ONLY public.leave REPLICA IDENTITY FULL;


ALTER TABLE public.leave OWNER TO postgres;

--
-- Name: level_multiplier; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.level_multiplier (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    multiplier double precision DEFAULT '1'::double precision
);


ALTER TABLE public.level_multiplier OWNER TO postgres;

--
-- Name: level_multiplier_voice; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.level_multiplier_voice (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    multiplier double precision DEFAULT '1'::double precision NOT NULL
);


ALTER TABLE public.level_multiplier_voice OWNER TO postgres;

--
-- Name: level_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.level_rewards (
    guild_id bigint,
    level integer,
    role_id bigint
);

ALTER TABLE ONLY public.level_rewards REPLICA IDENTITY FULL;


ALTER TABLE public.level_rewards OWNER TO postgres;

--
-- Name: level_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.level_user (
    guild_id bigint,
    user_id bigint,
    xp integer,
    level integer,
    target_xp bigint
);

ALTER TABLE ONLY public.level_user REPLICA IDENTITY FULL;


ALTER TABLE public.level_user OWNER TO postgres;

--
-- Name: leveling; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leveling (
    guild_id bigint,
    channel_id bigint,
    message text,
    booster double precision,
    multiplier double precision,
    users jsonb DEFAULT '[]'::jsonb,
    channels jsonb DEFAULT '[]'::jsonb,
    roles jsonb DEFAULT '[]'::jsonb,
    stack boolean DEFAULT true,
    voice_booster double precision,
    voice_multiplier double precision,
    command boolean DEFAULT false
);

ALTER TABLE ONLY public.leveling REPLICA IDENTITY FULL;


ALTER TABLE public.leveling OWNER TO postgres;

--
-- Name: licenses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.licenses (
    user_id character varying(255) NOT NULL,
    amount integer DEFAULT 0
);


ALTER TABLE public.licenses OWNER TO postgres;

--
-- Name: lockdown_channel; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lockdown_channel (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.lockdown_channel OWNER TO postgres;

--
-- Name: lockdown_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lockdown_role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.lockdown_role OWNER TO postgres;

--
-- Name: logging; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logging (
    guild_id bigint NOT NULL,
    messages bigint,
    guild bigint,
    roles bigint,
    channels bigint,
    moderation bigint,
    members bigint,
    voice bigint,
    ignored_users jsonb DEFAULT '[]'::jsonb,
    ignored_roles jsonb DEFAULT '[]'::jsonb,
    ignored_channels jsonb DEFAULT '[]'::jsonb
);

ALTER TABLE ONLY public.logging REPLICA IDENTITY FULL;


ALTER TABLE public.logging OWNER TO postgres;

--
-- Name: login_attempts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.login_attempts (
    id integer NOT NULL,
    user_id character varying(255) NOT NULL,
    ip_address character varying(255) NOT NULL,
    "timestamp" timestamp without time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.login_attempts OWNER TO postgres;

--
-- Name: login_attempts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.login_attempts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.login_attempts_id_seq OWNER TO postgres;

--
-- Name: login_attempts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.login_attempts_id_seq OWNED BY public.login_attempts.id;


--
-- Name: marry; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marry (
    author bigint,
    soulmate bigint,
    "time" bigint
);

ALTER TABLE ONLY public.marry REPLICA IDENTITY FULL;


ALTER TABLE public.marry OWNER TO postgres;

--
-- Name: modules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.modules (
    guild_id bigint NOT NULL,
    suggestion boolean DEFAULT false,
    starboard boolean DEFAULT false,
    clownboard boolean DEFAULT false
);


ALTER TABLE public.modules OWNER TO postgres;

--
-- Name: music_dj; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.music_dj (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.music_dj OWNER TO postgres;

--
-- Name: mute_images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mute_images (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.mute_images OWNER TO postgres;

--
-- Name: mute_reactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mute_reactions (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.mute_reactions OWNER TO postgres;

--
-- Name: nicknames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nicknames (
    user_id bigint,
    nick_name text,
    "time" bigint
);


ALTER TABLE public.nicknames OWNER TO postgres;

--
-- Name: nuke_scheduler; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.nuke_scheduler (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    schedule bigint,
    last_nuke bigint
);


ALTER TABLE public.nuke_scheduler OWNER TO postgres;

--
-- Name: number_counter; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.number_counter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    last_counted bigint,
    current_number integer DEFAULT 1,
    highest_count integer DEFAULT 1,
    safemode boolean DEFAULT false
);

ALTER TABLE ONLY public.number_counter REPLICA IDENTITY FULL;


ALTER TABLE public.number_counter OWNER TO postgres;

--
-- Name: only_bot; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.only_bot (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);

ALTER TABLE ONLY public.only_bot REPLICA IDENTITY FULL;


ALTER TABLE public.only_bot OWNER TO postgres;

--
-- Name: only_img; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.only_img (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);

ALTER TABLE ONLY public.only_img REPLICA IDENTITY FULL;


ALTER TABLE public.only_img OWNER TO postgres;

--
-- Name: only_link; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.only_link (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);

ALTER TABLE ONLY public.only_link REPLICA IDENTITY FULL;


ALTER TABLE public.only_link OWNER TO postgres;

--
-- Name: only_text; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.only_text (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);

ALTER TABLE ONLY public.only_text REPLICA IDENTITY FULL;


ALTER TABLE public.only_text OWNER TO postgres;

--
-- Name: orders_para; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders_para (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    message_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    platform text NOT NULL,
    amount text NOT NULL,
    receiver text NOT NULL,
    note text,
    button_message_id bigint,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.orders_para OWNER TO postgres;

--
-- Name: orders_para_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.orders_para_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.orders_para_id_seq OWNER TO postgres;

--
-- Name: orders_para_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.orders_para_id_seq OWNED BY public.orders_para.id;


--
-- Name: owner_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.owner_history (
    guild_id bigint,
    old_owner bigint,
    new_owner bigint,
    "timestamp" bigint
);


ALTER TABLE public.owner_history OWNER TO postgres;

--
-- Name: paginate_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paginate_data (
    message_id bigint NOT NULL,
    current_page integer NOT NULL
);


ALTER TABLE public.paginate_data OWNER TO postgres;

--
-- Name: paginate_embeds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paginate_embeds (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    embed text NOT NULL,
    page integer NOT NULL
);


ALTER TABLE public.paginate_embeds OWNER TO postgres;

--
-- Name: payment_currency; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payment_currency (
    guild_id bigint NOT NULL,
    currency text
);


ALTER TABLE public.payment_currency OWNER TO postgres;

--
-- Name: payment_methods; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payment_methods (
    guild_id bigint NOT NULL,
    method text NOT NULL,
    receiver text,
    available boolean
);


ALTER TABLE public.payment_methods OWNER TO postgres;

--
-- Name: paypal; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paypal (
    guild_id bigint,
    channel_id bigint,
    receiver text
);


ALTER TABLE public.paypal OWNER TO postgres;

--
-- Name: paypal_transaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paypal_transaction (
    id integer NOT NULL,
    receiver_email character varying(255) NOT NULL,
    payer_first_name character varying(255),
    payer_last_name character varying(255),
    payer_email character varying(255) NOT NULL,
    payer_id character varying(255) NOT NULL,
    note text,
    payment_send_amount numeric(10,2) NOT NULL,
    payment_fee_amount numeric(10,2) NOT NULL,
    payment_received_amount numeric(10,2) NOT NULL,
    payment_currency character varying(10) NOT NULL,
    transaction_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.paypal_transaction OWNER TO postgres;

--
-- Name: paypal_transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.paypal_transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.paypal_transaction_id_seq OWNER TO postgres;

--
-- Name: paypal_transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.paypal_transaction_id_seq OWNED BY public.paypal_transaction.id;


--
-- Name: paypal_verification; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.paypal_verification (
    user_id bigint,
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    code text,
    mail text
);


ALTER TABLE public.paypal_verification OWNER TO postgres;

--
-- Name: pingtimeout; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.pingtimeout (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL,
    timeout bigint,
    last_ping bigint
);


ALTER TABLE public.pingtimeout OWNER TO postgres;

--
-- Name: prefixes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prefixes (
    guild_id bigint NOT NULL,
    prefix text
);


ALTER TABLE public.prefixes OWNER TO postgres;

--
-- Name: premium; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.premium (
    guild_id bigint,
    user_id bigint,
    since bigint,
    transfers bigint DEFAULT '1'::bigint
);


ALTER TABLE public.premium OWNER TO postgres;

--
-- Name: quests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quests (
    id bigint,
    difficult text,
    mode text,
    amount bigint,
    earnings double precision,
    name text,
    type text
);


ALTER TABLE public.quests OWNER TO postgres;

--
-- Name: quests_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quests_user (
    user_id bigint,
    id bigint,
    difficult text,
    amount bigint,
    completed boolean
);


ALTER TABLE public.quests_user OWNER TO postgres;

--
-- Name: quotes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quotes (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.quotes OWNER TO postgres;

--
-- Name: reactionrole; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reactionrole (
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    emoji text,
    role_id bigint
);

ALTER TABLE ONLY public.reactionrole REPLICA IDENTITY FULL;


ALTER TABLE public.reactionrole OWNER TO postgres;

--
-- Name: reminder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reminder (
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    "time" bigint NOT NULL,
    task text NOT NULL
);

ALTER TABLE ONLY public.reminder REPLICA IDENTITY FULL;


ALTER TABLE public.reminder OWNER TO postgres;

--
-- Name: reposter; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reposter (
    guild_id bigint NOT NULL,
    embed boolean DEFAULT true,
    prefix text DEFAULT 'evelina'::text,
    delete boolean DEFAULT true,
    status boolean DEFAULT true
);


ALTER TABLE public.reposter OWNER TO postgres;

--
-- Name: reposter_channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reposter_channels (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.reposter_channels OWNER TO postgres;

--
-- Name: restore; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restore (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    roles text
);

ALTER TABLE ONLY public.restore REPLICA IDENTITY FULL;


ALTER TABLE public.restore OWNER TO postgres;

--
-- Name: restore_antinuke; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restore_antinuke (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    roles text NOT NULL
);


ALTER TABLE public.restore_antinuke OWNER TO postgres;

--
-- Name: restrictcommand; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restrictcommand (
    guild_id bigint NOT NULL,
    command text NOT NULL,
    role_id bigint NOT NULL
);

ALTER TABLE ONLY public.restrictcommand REPLICA IDENTITY FULL;


ALTER TABLE public.restrictcommand OWNER TO postgres;

--
-- Name: restrictmodule; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restrictmodule (
    guild_id bigint,
    command text,
    role_id bigint
);


ALTER TABLE public.restrictmodule OWNER TO postgres;

--
-- Name: revive; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.revive (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    timeout bigint,
    last_message bigint,
    message text,
    last_revive bigint
);


ALTER TABLE public.revive OWNER TO postgres;

--
-- Name: roleplay; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.roleplay (
    user_id bigint NOT NULL,
    target_id bigint NOT NULL,
    type text NOT NULL,
    count bigint
);


ALTER TABLE public.roleplay OWNER TO postgres;

--
-- Name: safemode; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.safemode (
    guild_id bigint,
    safemode boolean DEFAULT true
);


ALTER TABLE public.safemode OWNER TO postgres;

--
-- Name: seen; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seen (
    user_id bigint NOT NULL,
    guild_id bigint NOT NULL,
    "time" timestamp with time zone
);


ALTER TABLE public.seen OWNER TO postgres;

--
-- Name: selfaliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.selfaliases (
    user_id bigint NOT NULL,
    command text NOT NULL,
    alias text NOT NULL,
    args text
);

ALTER TABLE ONLY public.selfaliases REPLICA IDENTITY FULL;


ALTER TABLE public.selfaliases OWNER TO postgres;

--
-- Name: selfprefix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.selfprefix (
    user_id bigint NOT NULL,
    prefix text
);

ALTER TABLE ONLY public.selfprefix REPLICA IDENTITY FULL;


ALTER TABLE public.selfprefix OWNER TO postgres;

--
-- Name: smoke; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.smoke (
    user_id bigint NOT NULL,
    hits bigint
);


ALTER TABLE public.smoke OWNER TO postgres;

--
-- Name: snipes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.snipes (
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    message_content text,
    attachments text[],
    stickers text[],
    created_at bigint NOT NULL,
    deleted_by bigint
);


ALTER TABLE public.snipes OWNER TO postgres;

--
-- Name: snipes_edit; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.snipes_edit (
    channel_id bigint NOT NULL,
    author_id bigint NOT NULL,
    before_content text NOT NULL,
    after_content text NOT NULL,
    created_at bigint NOT NULL
);


ALTER TABLE public.snipes_edit OWNER TO postgres;

--
-- Name: snipes_reaction; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.snipes_reaction (
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    reaction text NOT NULL,
    user_id bigint NOT NULL,
    created_at bigint NOT NULL
);


ALTER TABLE public.snipes_reaction OWNER TO postgres;

--
-- Name: spotify_devices; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spotify_devices (
    discord_id bigint NOT NULL,
    device_id character varying(255) NOT NULL,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.spotify_devices OWNER TO postgres;

--
-- Name: spotify_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spotify_tokens (
    discord_id bigint NOT NULL,
    access_token text NOT NULL,
    refresh_token text NOT NULL,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.spotify_tokens OWNER TO postgres;

--
-- Name: starboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.starboard (
    guild_id bigint,
    channel_id bigint,
    emoji text,
    count integer
);

ALTER TABLE ONLY public.starboard REPLICA IDENTITY FULL;


ALTER TABLE public.starboard OWNER TO postgres;

--
-- Name: starboard_ignored; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.starboard_ignored (
    guild_id bigint,
    channel_id bigint
);


ALTER TABLE public.starboard_ignored OWNER TO postgres;

--
-- Name: starboard_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.starboard_messages (
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    starboard_message_id bigint
);

ALTER TABLE ONLY public.starboard_messages REPLICA IDENTITY FULL;


ALTER TABLE public.starboard_messages OWNER TO postgres;

--
-- Name: status_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.status_history (
    id integer NOT NULL,
    "timestamp" timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    total_servers integer NOT NULL,
    total_users integer NOT NULL,
    average_latency integer NOT NULL
);


ALTER TABLE public.status_history OWNER TO postgres;

--
-- Name: status_history_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.status_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.status_history_id_seq OWNER TO postgres;

--
-- Name: status_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.status_history_id_seq OWNED BY public.status_history.id;


--
-- Name: stickymessage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stickymessage (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text NOT NULL,
    last_message_id bigint,
    not_delete boolean DEFAULT false
);

ALTER TABLE ONLY public.stickymessage REPLICA IDENTITY FULL;


ALTER TABLE public.stickymessage OWNER TO postgres;

--
-- Name: storagevault; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.storagevault (
    user_id bigint NOT NULL,
    key text,
    domain text DEFAULT 'https://storagevault.cloud'::text
);


ALTER TABLE public.storagevault OWNER TO postgres;

--
-- Name: store_orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.store_orders (
    session_id character varying(255) DEFAULT NULL::character varying,
    invoice_id character varying(255) NOT NULL,
    product_id integer NOT NULL,
    total_price numeric(10,2) NOT NULL,
    serial_code character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    claimed boolean DEFAULT false,
    claimed_by bigint,
    paid boolean DEFAULT false
);


ALTER TABLE public.store_orders OWNER TO postgres;

--
-- Name: store_products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.store_products (
    product_id integer NOT NULL,
    product_name character varying(255) NOT NULL,
    price numeric(10,2) NOT NULL,
    image text,
    information text,
    active boolean,
    stripe boolean,
    crypto boolean
);


ALTER TABLE public.store_products OWNER TO postgres;

--
-- Name: stupidone_raid; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stupidone_raid (
    message bigint,
    slot_1 bigint,
    slot_2 bigint,
    slot_3 bigint,
    slot_4 bigint,
    slot_5 bigint,
    slot_6 bigint,
    slot_7 bigint,
    slot_8 bigint,
    slot_9 bigint,
    slot_10 bigint,
    slot_11 bigint,
    slot_12 bigint,
    slot_13 bigint,
    slot_14 bigint,
    slot_15 bigint,
    event text,
    max bigint,
    uhrzeit text,
    "timestamp" bigint,
    channel bigint,
    guild bigint,
    role bigint
);


ALTER TABLE public.stupidone_raid OWNER TO postgres;

--
-- Name: suggestions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestions (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message_id bigint NOT NULL,
    author_id bigint NOT NULL,
    content text NOT NULL,
    upvotes jsonb DEFAULT '[]'::jsonb NOT NULL,
    downvotes jsonb DEFAULT '[]'::jsonb NOT NULL
);

ALTER TABLE ONLY public.suggestions REPLICA IDENTITY FULL;


ALTER TABLE public.suggestions OWNER TO postgres;

--
-- Name: suggestions_blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestions_blacklist (
    guild_id bigint,
    user_id bigint,
    reason text
);

ALTER TABLE ONLY public.suggestions_blacklist REPLICA IDENTITY FULL;


ALTER TABLE public.suggestions_blacklist OWNER TO postgres;

--
-- Name: suggestions_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suggestions_module (
    guild_id bigint NOT NULL,
    channel_id bigint,
    role_id bigint,
    threads boolean DEFAULT false
);

ALTER TABLE ONLY public.suggestions_module REPLICA IDENTITY FULL;


ALTER TABLE public.suggestions_module OWNER TO postgres;

--
-- Name: tags; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tags (
    guild_id bigint NOT NULL,
    author_id bigint NOT NULL,
    name text NOT NULL,
    response text NOT NULL
);

ALTER TABLE ONLY public.tags REPLICA IDENTITY FULL;


ALTER TABLE public.tags OWNER TO postgres;

--
-- Name: tags_user; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tags_user (
    user_id bigint,
    name text,
    response text
);


ALTER TABLE public.tags_user OWNER TO postgres;

--
-- Name: team_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.team_members (
    user_id bigint NOT NULL,
    rank character varying(50),
    socials jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.team_members OWNER TO postgres;

--
-- Name: testimonials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.testimonials (
    guild_id bigint,
    user_id bigint,
    feedback text,
    approved boolean,
    message_id bigint
);


ALTER TABLE public.testimonials OWNER TO postgres;

--
-- Name: thread_watcher; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.thread_watcher (
    guild_id bigint NOT NULL,
    state boolean
);


ALTER TABLE public.thread_watcher OWNER TO postgres;

--
-- Name: ticket; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket (
    guild_id bigint,
    open_embed text,
    category_id bigint,
    logs bigint,
    support_roles jsonb,
    "limit" integer DEFAULT 1,
    claiming boolean DEFAULT false,
    claiming_privat boolean DEFAULT false,
    owner_role bigint,
    counter bigint DEFAULT '1'::bigint,
    counter_status boolean DEFAULT false,
    closed bigint
);

ALTER TABLE ONLY public.ticket REPLICA IDENTITY FULL;


ALTER TABLE public.ticket OWNER TO postgres;

--
-- Name: ticket_blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_blacklist (
    guild_id bigint,
    user_id bigint,
    reason text
);


ALTER TABLE public.ticket_blacklist OWNER TO postgres;

--
-- Name: ticket_claims; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_claims (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.ticket_claims OWNER TO postgres;

--
-- Name: ticket_modals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_modals (
    guild_id bigint,
    topic text,
    name text,
    description text,
    code text,
    required boolean DEFAULT true,
    style boolean DEFAULT false
);


ALTER TABLE public.ticket_modals OWNER TO postgres;

--
-- Name: ticket_opened; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_opened (
    guild_id bigint,
    channel_id bigint,
    user_id bigint,
    topic text DEFAULT 'Default'::text,
    claimed_by bigint
);

ALTER TABLE ONLY public.ticket_opened REPLICA IDENTITY FULL;


ALTER TABLE public.ticket_opened OWNER TO postgres;

--
-- Name: ticket_statuses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_statuses (
    guild_id bigint,
    name text,
    category_id bigint
);


ALTER TABLE public.ticket_statuses OWNER TO postgres;

--
-- Name: ticket_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_topics (
    guild_id bigint,
    name text,
    description text,
    emoji text,
    embed text,
    category_id bigint,
    support_roles jsonb,
    channel_name text,
    channel_topic text,
    status boolean DEFAULT true,
    weight bigint DEFAULT '0'::bigint
);

ALTER TABLE ONLY public.ticket_topics REPLICA IDENTITY FULL;


ALTER TABLE public.ticket_topics OWNER TO postgres;

--
-- Name: ticket_transcripts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_transcripts (
    guild_id bigint,
    user_id bigint,
    moderator_id bigint,
    id text,
    topic text DEFAULT 'Support'::text,
    "timestamp" bigint
);


ALTER TABLE public.ticket_transcripts OWNER TO postgres;

--
-- Name: ticket_transcripts_access; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_transcripts_access (
    guild_id bigint NOT NULL,
    users jsonb DEFAULT '[]'::jsonb
);


ALTER TABLE public.ticket_transcripts_access OWNER TO postgres;

--
-- Name: timer; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timer (
    guild_id bigint,
    channel_id bigint,
    "interval" bigint,
    code text,
    "time" bigint
);


ALTER TABLE public.timer OWNER TO postgres;

--
-- Name: timezone; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timezone (
    user_id bigint,
    zone text
);

ALTER TABLE ONLY public.timezone REPLICA IDENTITY FULL;


ALTER TABLE public.timezone OWNER TO postgres;

--
-- Name: user_plays; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_plays (
    user_id bigint NOT NULL,
    plays jsonb DEFAULT '{}'::jsonb NOT NULL,
    last_updated bigint DEFAULT 0
);


ALTER TABLE public.user_plays OWNER TO postgres;

--
-- Name: usernames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usernames (
    user_id bigint,
    user_name text,
    "time" bigint
);

ALTER TABLE ONLY public.usernames REPLICA IDENTITY FULL;


ALTER TABLE public.usernames OWNER TO postgres;

--
-- Name: vanity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vanity (
    guild_id bigint NOT NULL,
    channel_id bigint,
    roles jsonb DEFAULT '[]'::jsonb,
    message text,
    trigger text
);

ALTER TABLE ONLY public.vanity REPLICA IDENTITY FULL;


ALTER TABLE public.vanity OWNER TO postgres;

--
-- Name: vanitys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vanitys (
    guild_id bigint,
    vanity text,
    "time" bigint
);


ALTER TABLE public.vanitys OWNER TO postgres;

--
-- Name: vape; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vape (
    guild_id bigint NOT NULL,
    user_id bigint,
    hits bigint
);

ALTER TABLE ONLY public.vape REPLICA IDENTITY FULL;


ALTER TABLE public.vape OWNER TO postgres;

--
-- Name: voiceban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voiceban (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    moderator_id bigint,
    "timestamp" bigint
);


ALTER TABLE public.voiceban OWNER TO postgres;

--
-- Name: voicemaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster (
    guild_id bigint,
    channel_id bigint,
    interface_id bigint,
    region character varying,
    name character varying,
    bitrate integer,
    category bigint,
    savesettings boolean DEFAULT false,
    banned_words text DEFAULT '[]'::text
);

ALTER TABLE ONLY public.voicemaster REPLICA IDENTITY FULL;


ALTER TABLE public.voicemaster OWNER TO postgres;

--
-- Name: voicemaster_buttons; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster_buttons (
    guild_id bigint,
    action text,
    label text,
    emoji text,
    style text
);

ALTER TABLE ONLY public.voicemaster_buttons REPLICA IDENTITY FULL;


ALTER TABLE public.voicemaster_buttons OWNER TO postgres;

--
-- Name: voicemaster_channels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster_channels (
    user_id bigint,
    voice bigint
);

ALTER TABLE ONLY public.voicemaster_channels REPLICA IDENTITY FULL;


ALTER TABLE public.voicemaster_channels OWNER TO postgres;

--
-- Name: voicemaster_names; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster_names (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    name text
);


ALTER TABLE public.voicemaster_names OWNER TO postgres;

--
-- Name: voicemaster_presets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster_presets (
    user_id bigint NOT NULL,
    name text NOT NULL,
    settings jsonb NOT NULL,
    overwrites jsonb NOT NULL,
    autoload boolean DEFAULT false
);


ALTER TABLE public.voicemaster_presets OWNER TO postgres;

--
-- Name: voicerole; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicerole (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    roles jsonb DEFAULT '[]'::jsonb NOT NULL
);


ALTER TABLE public.voicerole OWNER TO postgres;

--
-- Name: voicerole_default; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicerole_default (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.voicerole_default OWNER TO postgres;

--
-- Name: voicetrack; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicetrack (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    joined_time bigint,
    total_time bigint,
    muted_time bigint,
    mute_time bigint
);


ALTER TABLE public.voicetrack OWNER TO postgres;

--
-- Name: voicetrack_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicetrack_settings (
    guild_id bigint NOT NULL,
    state boolean,
    mute_track boolean DEFAULT false,
    level_state boolean DEFAULT false
);


ALTER TABLE public.voicetrack_settings OWNER TO postgres;

--
-- Name: votes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.votes (
    user_id bigint DEFAULT '0'::bigint,
    vote_until bigint DEFAULT '0'::bigint,
    vote_count bigint DEFAULT '0'::bigint,
    vote_reminder boolean DEFAULT false
);


ALTER TABLE public.votes OWNER TO postgres;

--
-- Name: vouches; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vouches (
    id integer NOT NULL,
    user_id bigint NOT NULL,
    author_id bigint NOT NULL,
    message text NOT NULL,
    "timestamp" bigint NOT NULL
);

ALTER TABLE ONLY public.vouches REPLICA IDENTITY FULL;


ALTER TABLE public.vouches OWNER TO postgres;

--
-- Name: vouches_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vouches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vouches_id_seq OWNER TO postgres;

--
-- Name: vouches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vouches_id_seq OWNED BY public.vouches.id;


--
-- Name: vouches_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vouches_settings (
    server_id bigint NOT NULL,
    channel_id bigint
);

ALTER TABLE ONLY public.vouches_settings REPLICA IDENTITY FULL;


ALTER TABLE public.vouches_settings OWNER TO postgres;

--
-- Name: warns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warns (
    guild_id bigint,
    user_id bigint,
    author_id bigint,
    "time" text,
    reason text
);

ALTER TABLE ONLY public.warns REPLICA IDENTITY FULL;


ALTER TABLE public.warns OWNER TO postgres;

--
-- Name: warns_punishment; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warns_punishment (
    guild_id bigint,
    warn integer,
    action text,
    "time" bigint
);


ALTER TABLE public.warns_punishment OWNER TO postgres;

--
-- Name: warns_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.warns_rewards (
    guild_id bigint,
    warn integer,
    role_id bigint
);


ALTER TABLE public.warns_rewards OWNER TO postgres;

--
-- Name: webhook; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.webhook (
    guild_id bigint,
    code text,
    url text,
    channel text,
    name text,
    avatar text
);

ALTER TABLE ONLY public.webhook REPLICA IDENTITY FULL;


ALTER TABLE public.webhook OWNER TO postgres;

--
-- Name: webhook_username; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.webhook_username (
    guild_id bigint,
    webhook_url text,
    length bigint,
    name text,
    avatar text
);

ALTER TABLE ONLY public.webhook_username REPLICA IDENTITY FULL;


ALTER TABLE public.webhook_username OWNER TO postgres;

--
-- Name: webhook_vanity; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.webhook_vanity (
    guild_id bigint,
    webhook_url text,
    length bigint,
    name text,
    avatar text
);

ALTER TABLE ONLY public.webhook_vanity REPLICA IDENTITY FULL;


ALTER TABLE public.webhook_vanity OWNER TO postgres;

--
-- Name: welcome; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.welcome (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text,
    delete boolean DEFAULT false,
    duration bigint DEFAULT '0'::bigint
);

ALTER TABLE ONLY public.welcome REPLICA IDENTITY FULL;


ALTER TABLE public.welcome OWNER TO postgres;

--
-- Name: welcome_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.welcome_messages (
    guild_id bigint,
    user_id bigint,
    channel_id bigint,
    message_id bigint,
    "timestamp" bigint
);


ALTER TABLE public.welcome_messages OWNER TO postgres;

--
-- Name: whitelist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.whitelist (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);

ALTER TABLE ONLY public.whitelist REPLICA IDENTITY FULL;


ALTER TABLE public.whitelist OWNER TO postgres;

--
-- Name: whitelist_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.whitelist_module (
    guild_id bigint NOT NULL,
    embed text DEFAULT 'default'::text,
    punishment text DEFAULT 'kick'::text
);

ALTER TABLE ONLY public.whitelist_module REPLICA IDENTITY FULL;


ALTER TABLE public.whitelist_module OWNER TO postgres;

--
-- Name: command_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.command_history ALTER COLUMN id SET DEFAULT nextval('public.command_history_id_seq'::regclass);


--
-- Name: command_stats id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.command_stats ALTER COLUMN id SET DEFAULT nextval('public.command_stats_id_seq'::regclass);


--
-- Name: company id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company ALTER COLUMN id SET DEFAULT nextval('public.clans_id_seq'::regclass);


--
-- Name: company_requests id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_requests ALTER COLUMN id SET DEFAULT nextval('public.clan_requests_id_seq'::regclass);


--
-- Name: embeds_templates id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.embeds_templates ALTER COLUMN id SET DEFAULT nextval('public.embeds_templates_id_seq'::regclass);


--
-- Name: invoices id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices ALTER COLUMN id SET DEFAULT nextval('public.invoices_id_seq'::regclass);


--
-- Name: invoices_authorizations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices_authorizations ALTER COLUMN id SET DEFAULT nextval('public.invoices_authorizations_id_seq'::regclass);


--
-- Name: login_attempts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.login_attempts ALTER COLUMN id SET DEFAULT nextval('public.login_attempts_id_seq'::regclass);


--
-- Name: orders_para id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders_para ALTER COLUMN id SET DEFAULT nextval('public.orders_para_id_seq'::regclass);


--
-- Name: paypal_transaction id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paypal_transaction ALTER COLUMN id SET DEFAULT nextval('public.paypal_transaction_id_seq'::regclass);


--
-- Name: status_history id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.status_history ALTER COLUMN id SET DEFAULT nextval('public.status_history_id_seq'::regclass);


--
-- Name: vouches id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vouches ALTER COLUMN id SET DEFAULT nextval('public.vouches_id_seq'::regclass);


--
-- Name: activity_leaderboard activity_leaderboard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_leaderboard
    ADD CONSTRAINT activity_leaderboard_pkey PRIMARY KEY (guild_id, type, range);


--
-- Name: activity_timezone activity_timezone_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_timezone
    ADD CONSTRAINT activity_timezone_pkey PRIMARY KEY (guild_id);


--
-- Name: antinuke antinuke_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antinuke
    ADD CONSTRAINT antinuke_pkey PRIMARY KEY (guild_id);


--
-- Name: antinuke_roles antinuke_roles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antinuke_roles
    ADD CONSTRAINT antinuke_roles_pkey PRIMARY KEY (guild_id);


--
-- Name: antiraid_age antiraid_age_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antiraid_age
    ADD CONSTRAINT antiraid_age_pkey PRIMARY KEY (guild_id);


--
-- Name: antiraid_avatar antiraid_avatar_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antiraid_avatar
    ADD CONSTRAINT antiraid_avatar_pkey PRIMARY KEY (guild_id);


--
-- Name: antiraid_massjoin antiraid_massjoin_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antiraid_massjoin
    ADD CONSTRAINT antiraid_massjoin_pkey PRIMARY KEY (guild_id);


--
-- Name: antiraid antiraid_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antiraid
    ADD CONSTRAINT antiraid_pkey PRIMARY KEY (guild_id);


--
-- Name: api_key api_key_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_key
    ADD CONSTRAINT api_key_pkey PRIMARY KEY (user_id);


--
-- Name: application_votes application_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.application_votes
    ADD CONSTRAINT application_votes_pkey PRIMARY KEY (message_id, user_id);


--
-- Name: applications applications_guild_id_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.applications
    ADD CONSTRAINT applications_guild_id_name_key UNIQUE (guild_id, name);


--
-- Name: authorized authorized_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.authorized
    ADD CONSTRAINT authorized_pkey PRIMARY KEY (guild_id);


--
-- Name: autopost_instagram_announced autopost_instagram_announced_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_instagram_announced
    ADD CONSTRAINT autopost_instagram_announced_pkey PRIMARY KEY (channel_id, post_id);


--
-- Name: autopost_instagram autopost_instagram_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_instagram
    ADD CONSTRAINT autopost_instagram_pkey PRIMARY KEY (guild_id, username);


--
-- Name: autopost autopost_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost
    ADD CONSTRAINT autopost_pkey PRIMARY KEY (guild_id, type, category);


--
-- Name: autopost_tiktok_announced autopost_tiktok_announced_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_tiktok_announced
    ADD CONSTRAINT autopost_tiktok_announced_pkey PRIMARY KEY (channel_id, video_id);


--
-- Name: autopost_tiktok autopost_tiktok_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_tiktok
    ADD CONSTRAINT autopost_tiktok_pkey PRIMARY KEY (guild_id, username);


--
-- Name: autopost_twitch_announced autopost_twitch_announced_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_twitch_announced
    ADD CONSTRAINT autopost_twitch_announced_pkey PRIMARY KEY (channel_id, stream_id);


--
-- Name: autopost_twitter_announced autopost_twitter_announced_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_twitter_announced
    ADD CONSTRAINT autopost_twitter_announced_pkey PRIMARY KEY (channel_id, tweet_id);


--
-- Name: autopost_twitter autopost_twitter_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_twitter
    ADD CONSTRAINT autopost_twitter_pkey PRIMARY KEY (guild_id, username);


--
-- Name: autopost_youtube_announced autopost_youtube_announced_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_youtube_announced
    ADD CONSTRAINT autopost_youtube_announced_pkey PRIMARY KEY (channel_id, video_id);


--
-- Name: autopost_youtube autopost_youtube_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_youtube
    ADD CONSTRAINT autopost_youtube_pkey PRIMARY KEY (guild_id, username);


--
-- Name: autopublish autopublish_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopublish
    ADD CONSTRAINT autopublish_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: autoreact_channel autoreact_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoreact_channel
    ADD CONSTRAINT autoreact_channel_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: autoreact autoreact_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoreact
    ADD CONSTRAINT autoreact_pkey PRIMARY KEY (guild_id, trigger);


--
-- Name: autoresponder_permissions autoresponder_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoresponder_permissions
    ADD CONSTRAINT autoresponder_permissions_pkey PRIMARY KEY (guild_id, trigger, state);


--
-- Name: autorole_bots autorole_bots_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autorole_bots
    ADD CONSTRAINT autorole_bots_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: autorole_humans autorole_humans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autorole_humans
    ADD CONSTRAINT autorole_humans_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: autorole autorole_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autorole
    ADD CONSTRAINT autorole_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: avatar_history avatar_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_history
    ADD CONSTRAINT avatar_history_pkey PRIMARY KEY (avatar);


--
-- Name: avatar_privacy avatar_privacy_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_privacy
    ADD CONSTRAINT avatar_privacy_pkey PRIMARY KEY (user_id);


--
-- Name: beta_testers beta_testers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.beta_testers
    ADD CONSTRAINT beta_testers_pkey PRIMARY KEY (user_id);


--
-- Name: bio bio_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bio
    ADD CONSTRAINT bio_pkey PRIMARY KEY (username);


--
-- Name: birthday birthday_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.birthday
    ADD CONSTRAINT birthday_pkey PRIMARY KEY (user_id);


--
-- Name: birthday_reward birthday_reward_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.birthday_reward
    ADD CONSTRAINT birthday_reward_pkey PRIMARY KEY (guild_id);


--
-- Name: blacklist_cog blacklist_cog_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_cog
    ADD CONSTRAINT blacklist_cog_pkey PRIMARY KEY (user_id, cog);


--
-- Name: blacklist_cog_server blacklist_cog_server_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_cog_server
    ADD CONSTRAINT blacklist_cog_server_pkey PRIMARY KEY (guild_id, cog);


--
-- Name: blacklist_command blacklist_command_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_command
    ADD CONSTRAINT blacklist_command_pkey PRIMARY KEY (user_id, command);


--
-- Name: blacklist_command_server blacklist_command_server_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_command_server
    ADD CONSTRAINT blacklist_command_server_pkey PRIMARY KEY (guild_id, command);


--
-- Name: blacklist blacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist
    ADD CONSTRAINT blacklist_pkey PRIMARY KEY (id, type);


--
-- Name: blacklist_server blacklist_server_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_server
    ADD CONSTRAINT blacklist_server_pkey PRIMARY KEY (guild_id);


--
-- Name: blacklist_user blacklist_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist_user
    ADD CONSTRAINT blacklist_user_pkey PRIMARY KEY (user_id);


--
-- Name: booster_allow booster_allow_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booster_allow
    ADD CONSTRAINT booster_allow_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: bumpreminder_leaderboard bumpreminder_leaderboard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bumpreminder_leaderboard
    ADD CONSTRAINT bumpreminder_leaderboard_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: business business_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.business
    ADD CONSTRAINT business_pkey PRIMARY KEY (id);


--
-- Name: button_message button_message_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.button_message
    ADD CONSTRAINT button_message_pkey PRIMARY KEY (guild_id, channel_id, message_id, button_id);


--
-- Name: button_settings button_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.button_settings
    ADD CONSTRAINT button_settings_pkey PRIMARY KEY (guild_id, message_id);


--
-- Name: company_requests clan_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_requests
    ADD CONSTRAINT clan_requests_pkey PRIMARY KEY (id);


--
-- Name: company clans_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company
    ADD CONSTRAINT clans_name_key UNIQUE (name);


--
-- Name: company clans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company
    ADD CONSTRAINT clans_pkey PRIMARY KEY (id);


--
-- Name: clashofclans clashofclans_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.clashofclans
    ADD CONSTRAINT clashofclans_pkey PRIMARY KEY (user_id);


--
-- Name: command_history command_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.command_history
    ADD CONSTRAINT command_history_pkey PRIMARY KEY (id);


--
-- Name: command_stats command_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.command_stats
    ADD CONSTRAINT command_stats_pkey PRIMARY KEY (id);


--
-- Name: company_earnings company_earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_earnings
    ADD CONSTRAINT company_earnings_pkey PRIMARY KEY (user_id, company_id);


--
-- Name: company_limit_bonus company_limit_bonus_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_limit_bonus
    ADD CONSTRAINT company_limit_bonus_pkey PRIMARY KEY (user_id, date);


--
-- Name: company_limit_withdraw company_limit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_limit_withdraw
    ADD CONSTRAINT company_limit_pkey PRIMARY KEY (user_id, date);


--
-- Name: company_voters company_votes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.company_voters
    ADD CONSTRAINT company_votes_pkey PRIMARY KEY (user_id, company_id);


--
-- Name: economy_business economy_business_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_business
    ADD CONSTRAINT economy_business_pkey PRIMARY KEY (user_id);


--
-- Name: economy_cards_user economy_cards_user_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_cards_user
    ADD CONSTRAINT economy_cards_user_pkey PRIMARY KEY (card_id);


--
-- Name: economy_investments economy_investments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_investments
    ADD CONSTRAINT economy_investments_pkey PRIMARY KEY (id);


--
-- Name: economy_limit economy_limit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_limit
    ADD CONSTRAINT economy_limit_pkey PRIMARY KEY (user_id, date);


--
-- Name: economy_shop_earnings economy_shop_earnings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_shop_earnings
    ADD CONSTRAINT economy_shop_earnings_pkey PRIMARY KEY (guild_id);


--
-- Name: embeds embeds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.embeds
    ADD CONSTRAINT embeds_pkey PRIMARY KEY (code);


--
-- Name: embeds_templates embeds_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.embeds_templates
    ADD CONSTRAINT embeds_templates_pkey PRIMARY KEY (id);


--
-- Name: error_codes error_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_codes
    ADD CONSTRAINT error_codes_pkey PRIMARY KEY (code);


--
-- Name: freegames freegames_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.freegames
    ADD CONSTRAINT freegames_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: gamestats gamestats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.gamestats
    ADD CONSTRAINT gamestats_pkey PRIMARY KEY (user_id, game);


--
-- Name: global_beta_commands global_beta_commands_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.global_beta_commands
    ADD CONSTRAINT global_beta_commands_pkey PRIMARY KEY (command);


--
-- Name: global_disabled_commands global_disabled_commands_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.global_disabled_commands
    ADD CONSTRAINT global_disabled_commands_pkey PRIMARY KEY (command);


--
-- Name: guessthenumber guessthenumber_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guessthenumber
    ADD CONSTRAINT guessthenumber_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: guessthenumber_settings guessthenumber_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guessthenumber_settings
    ADD CONSTRAINT guessthenumber_settings_pkey PRIMARY KEY (guild_id);


--
-- Name: guild_cache guild_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guild_cache
    ADD CONSTRAINT guild_cache_pkey PRIMARY KEY (guild_id);


--
-- Name: guild_names guild_names_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guild_names
    ADD CONSTRAINT guild_names_pkey PRIMARY KEY (guild_id);


--
-- Name: guns guns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.guns
    ADD CONSTRAINT guns_pkey PRIMARY KEY (user_id);


--
-- Name: history history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.history
    ADD CONSTRAINT history_pkey PRIMARY KEY (id);


--
-- Name: invites invites_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invites
    ADD CONSTRAINT invites_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: invites_rewards invites_rewards_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invites_rewards
    ADD CONSTRAINT invites_rewards_pkey PRIMARY KEY (guild_id, threshold);


--
-- Name: invites_settings invites_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invites_settings
    ADD CONSTRAINT invites_settings_pkey PRIMARY KEY (guild_id);


--
-- Name: invites_users invites_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invites_users
    ADD CONSTRAINT invites_users_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: invoices_authorizations invoices_authorizations_guild_id_invoice_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices_authorizations
    ADD CONSTRAINT invoices_authorizations_guild_id_invoice_id_key UNIQUE (guild_id, invoice_id);


--
-- Name: invoices_authorizations invoices_authorizations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices_authorizations
    ADD CONSTRAINT invoices_authorizations_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_invoice_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_invoice_id_key UNIQUE (invoice_id);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_session_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_session_id_key UNIQUE (session_id);


--
-- Name: jail_members jail_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jail_members
    ADD CONSTRAINT jail_members_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: economy_lab lab_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.economy_lab
    ADD CONSTRAINT lab_pkey PRIMARY KEY (user_id);


--
-- Name: language language_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.language
    ADD CONSTRAINT language_pkey PRIMARY KEY (user_id);


--
-- Name: lastfm_crowns lastfm_crowns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lastfm_crowns
    ADD CONSTRAINT lastfm_crowns_pkey PRIMARY KEY (artist);


--
-- Name: level_multiplier level_multiplier_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.level_multiplier
    ADD CONSTRAINT level_multiplier_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: level_multiplier_voice level_multiplier_voice_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.level_multiplier_voice
    ADD CONSTRAINT level_multiplier_voice_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: licenses licenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.licenses
    ADD CONSTRAINT licenses_pkey PRIMARY KEY (user_id);


--
-- Name: antinuke_linksedit linkedit_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.antinuke_linksedit
    ADD CONSTRAINT linkedit_pkey PRIMARY KEY (guild_id);


--
-- Name: lockdown_channel lockdown_channel_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lockdown_channel
    ADD CONSTRAINT lockdown_channel_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: lockdown_role lockdown_role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lockdown_role
    ADD CONSTRAINT lockdown_role_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: logging logging_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logging
    ADD CONSTRAINT logging_pkey PRIMARY KEY (guild_id);


--
-- Name: login_attempts login_attempts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.login_attempts
    ADD CONSTRAINT login_attempts_pkey PRIMARY KEY (id);


--
-- Name: activity_messages message_counts_new_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_messages
    ADD CONSTRAINT message_counts_new_pkey PRIMARY KEY (user_id, channel_id, server_id, message_date);


--
-- Name: modules modules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.modules
    ADD CONSTRAINT modules_pkey PRIMARY KEY (guild_id);


--
-- Name: nuke_scheduler nuke_scheduler_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.nuke_scheduler
    ADD CONSTRAINT nuke_scheduler_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: number_counter number_counter_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.number_counter
    ADD CONSTRAINT number_counter_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: orders_para orders_para_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders_para
    ADD CONSTRAINT orders_para_pkey PRIMARY KEY (id);


--
-- Name: paginate_data paginate_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paginate_data
    ADD CONSTRAINT paginate_data_pkey PRIMARY KEY (message_id);


--
-- Name: paginate_embeds paginate_embeds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paginate_embeds
    ADD CONSTRAINT paginate_embeds_pkey PRIMARY KEY (guild_id, channel_id, message_id, page);


--
-- Name: payment_currency payment_currency_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payment_currency
    ADD CONSTRAINT payment_currency_pkey PRIMARY KEY (guild_id);


--
-- Name: paypal_transaction paypal_transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.paypal_transaction
    ADD CONSTRAINT paypal_transaction_pkey PRIMARY KEY (id);


--
-- Name: pingtimeout pingtimeout_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.pingtimeout
    ADD CONSTRAINT pingtimeout_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: prefixes prefixes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.prefixes
    ADD CONSTRAINT prefixes_pkey PRIMARY KEY (guild_id);


--
-- Name: reposter_channels reposter_channels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reposter_channels
    ADD CONSTRAINT reposter_channels_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: reposter reposter_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reposter
    ADD CONSTRAINT reposter_pkey PRIMARY KEY (guild_id);


--
-- Name: restore_antinuke restore_antinuke_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.restore_antinuke
    ADD CONSTRAINT restore_antinuke_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: restore restore_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.restore
    ADD CONSTRAINT restore_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: revive revive_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.revive
    ADD CONSTRAINT revive_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: button_role role_buttons_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.button_role
    ADD CONSTRAINT role_buttons_pkey PRIMARY KEY (guild_id, channel_id, message_id, button_id);


--
-- Name: roleplay roleplay_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.roleplay
    ADD CONSTRAINT roleplay_pkey PRIMARY KEY (user_id, target_id, type);


--
-- Name: seen seen_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.seen
    ADD CONSTRAINT seen_pkey PRIMARY KEY (user_id, guild_id);


--
-- Name: selfprefix selfprefix_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.selfprefix
    ADD CONSTRAINT selfprefix_pkey PRIMARY KEY (user_id);


--
-- Name: smoke smoke_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.smoke
    ADD CONSTRAINT smoke_pkey PRIMARY KEY (user_id);


--
-- Name: spotify_devices spotify_devices_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spotify_devices
    ADD CONSTRAINT spotify_devices_pkey PRIMARY KEY (discord_id);


--
-- Name: spotify_tokens spotify_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.spotify_tokens
    ADD CONSTRAINT spotify_tokens_pkey PRIMARY KEY (discord_id);


--
-- Name: status_history status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.status_history
    ADD CONSTRAINT status_history_pkey PRIMARY KEY (id);


--
-- Name: stickymessage stickymessage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stickymessage
    ADD CONSTRAINT stickymessage_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: storagevault storagevault_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.storagevault
    ADD CONSTRAINT storagevault_pkey PRIMARY KEY (user_id);


--
-- Name: store_orders store_orders_invoice_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_orders
    ADD CONSTRAINT store_orders_invoice_id_key UNIQUE (invoice_id);


--
-- Name: store_products store_products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.store_products
    ADD CONSTRAINT store_products_pkey PRIMARY KEY (product_id);


--
-- Name: suggestions_module suggestions_module_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suggestions_module
    ADD CONSTRAINT suggestions_module_pkey PRIMARY KEY (guild_id);


--
-- Name: team_members team_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.team_members
    ADD CONSTRAINT team_members_pkey PRIMARY KEY (user_id);


--
-- Name: thread_watcher thread_watcher_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.thread_watcher
    ADD CONSTRAINT thread_watcher_pkey PRIMARY KEY (guild_id);


--
-- Name: ticket_claims ticket_claims_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ticket_claims
    ADD CONSTRAINT ticket_claims_pkey PRIMARY KEY (guild_id, user_id, channel_id);


--
-- Name: ticket_transcripts_access ticket_transcripts_access_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ticket_transcripts_access
    ADD CONSTRAINT ticket_transcripts_access_pkey PRIMARY KEY (guild_id);


--
-- Name: autopost_twitch twitch_streamers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autopost_twitch
    ADD CONSTRAINT twitch_streamers_pkey PRIMARY KEY (guild_id, streamer);


--
-- Name: user_plays user_plays_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_plays
    ADD CONSTRAINT user_plays_pkey PRIMARY KEY (user_id);


--
-- Name: vanity vanity_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vanity
    ADD CONSTRAINT vanity_pkey PRIMARY KEY (guild_id);


--
-- Name: vape vape_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vape
    ADD CONSTRAINT vape_pkey PRIMARY KEY (guild_id);


--
-- Name: voiceban voiceban_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voiceban
    ADD CONSTRAINT voiceban_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: voicemaster_names voicemaster_names_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voicemaster_names
    ADD CONSTRAINT voicemaster_names_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: voicemaster_presets voicemaster_presets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voicemaster_presets
    ADD CONSTRAINT voicemaster_presets_pkey PRIMARY KEY (user_id, name);


--
-- Name: voicerole voicerole_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voicerole
    ADD CONSTRAINT voicerole_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: activity_voice voicetrack_dates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.activity_voice
    ADD CONSTRAINT voicetrack_dates_pkey PRIMARY KEY (user_id, channel_id, server_id, voice_date);


--
-- Name: voicetrack voicetrack_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voicetrack
    ADD CONSTRAINT voicetrack_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: voicetrack_settings voicetrack_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.voicetrack_settings
    ADD CONSTRAINT voicetrack_settings_pkey PRIMARY KEY (guild_id);


--
-- Name: vouches vouches_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vouches
    ADD CONSTRAINT vouches_pkey PRIMARY KEY (id);


--
-- Name: vouches_settings vouches_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vouches_settings
    ADD CONSTRAINT vouches_settings_pkey PRIMARY KEY (server_id);


--
-- Name: welcome welcome_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.welcome
    ADD CONSTRAINT welcome_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: whitelist_module whitelist_module_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.whitelist_module
    ADD CONSTRAINT whitelist_module_pkey PRIMARY KEY (guild_id);


--
-- Name: idx_command_stats_command; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_command_stats_command ON public.command_stats USING btree (command);


--
-- Name: idx_command_stats_guild_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_command_stats_guild_id ON public.command_stats USING btree (guild_id);


--
-- Name: idx_command_stats_timestamp; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_command_stats_timestamp ON public.command_stats USING btree ("timestamp");


--
-- Name: idx_command_stats_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_command_stats_user_id ON public.command_stats USING btree (user_id);


--
-- Name: idx_guild_cache_guild_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_guild_cache_guild_id ON public.guild_cache USING btree (guild_id);


--
-- Name: idx_ticket_transcripts_guild_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_ticket_transcripts_guild_id ON public.ticket_transcripts USING btree (guild_id);


--
-- Name: status_history_timestamp_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX status_history_timestamp_idx ON public.status_history USING btree ("timestamp");


--
-- Name: flow_publication; Type: PUBLICATION; Schema: -; Owner: postgres
--

CREATE PUBLICATION flow_publication WITH (publish = 'insert, update, delete, truncate', publish_via_partition_root = true);


ALTER PUBLICATION flow_publication OWNER TO postgres;

--
-- Name: flow_publication afk; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.afk;


--
-- Name: flow_publication aliases; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.aliases;


--
-- Name: flow_publication antinuke; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.antinuke;


--
-- Name: flow_publication antinuke_modules; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.antinuke_modules;


--
-- Name: flow_publication antiraid_massjoin; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.antiraid_massjoin;


--
-- Name: flow_publication api_key; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.api_key;


--
-- Name: flow_publication automod_rules; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.automod_rules;


--
-- Name: flow_publication automod_spam; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.automod_spam;


--
-- Name: flow_publication autopost_twitch; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.autopost_twitch;


--
-- Name: flow_publication autoreact; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.autoreact;


--
-- Name: flow_publication autoresponder; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.autoresponder;


--
-- Name: flow_publication autorole; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.autorole;


--
-- Name: flow_publication birthday; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.birthday;


--
-- Name: flow_publication blacklist; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.blacklist;


--
-- Name: flow_publication boost; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.boost;


--
-- Name: flow_publication booster_award; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.booster_award;


--
-- Name: flow_publication booster_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.booster_module;


--
-- Name: flow_publication booster_roles; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.booster_roles;


--
-- Name: flow_publication bumpreminder; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.bumpreminder;


--
-- Name: flow_publication business; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.business;


--
-- Name: flow_publication business_auction; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.business_auction;


--
-- Name: flow_publication button_role; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.button_role;


--
-- Name: flow_publication channel_disabled_commands; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.channel_disabled_commands;


--
-- Name: flow_publication channel_disabled_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.channel_disabled_module;


--
-- Name: flow_publication color_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.color_module;


--
-- Name: flow_publication color_roles; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.color_roles;


--
-- Name: flow_publication command_history; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.command_history;


--
-- Name: flow_publication company; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.company;


--
-- Name: flow_publication company_requests; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.company_requests;


--
-- Name: flow_publication counters; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.counters;


--
-- Name: flow_publication donor; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.donor;


--
-- Name: flow_publication economy; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.economy;


--
-- Name: flow_publication embeds; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.embeds;


--
-- Name: flow_publication error_codes; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.error_codes;


--
-- Name: flow_publication fake_perms; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.fake_perms;


--
-- Name: flow_publication force_nick; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.force_nick;


--
-- Name: flow_publication gamestats; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.gamestats;


--
-- Name: flow_publication giveaway; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.giveaway;


--
-- Name: flow_publication giveaway_ended; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.giveaway_ended;


--
-- Name: flow_publication global_disabled_commands; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.global_disabled_commands;


--
-- Name: flow_publication globalban; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.globalban;


--
-- Name: flow_publication guild_disabled_commands; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.guild_disabled_commands;


--
-- Name: flow_publication guild_disabled_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.guild_disabled_module;


--
-- Name: flow_publication hardban; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.hardban;


--
-- Name: flow_publication history; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.history;


--
-- Name: flow_publication invoke_message; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.invoke_message;


--
-- Name: flow_publication jail; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.jail;


--
-- Name: flow_publication jail_members; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.jail_members;


--
-- Name: flow_publication lastfm; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.lastfm;


--
-- Name: flow_publication leave; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.leave;


--
-- Name: flow_publication level_rewards; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.level_rewards;


--
-- Name: flow_publication level_user; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.level_user;


--
-- Name: flow_publication leveling; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.leveling;


--
-- Name: flow_publication logging; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.logging;


--
-- Name: flow_publication marry; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.marry;


--
-- Name: flow_publication number_counter; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.number_counter;


--
-- Name: flow_publication only_bot; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.only_bot;


--
-- Name: flow_publication only_img; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.only_img;


--
-- Name: flow_publication only_link; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.only_link;


--
-- Name: flow_publication only_text; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.only_text;


--
-- Name: flow_publication reactionrole; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.reactionrole;


--
-- Name: flow_publication reminder; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.reminder;


--
-- Name: flow_publication restore; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.restore;


--
-- Name: flow_publication restrictcommand; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.restrictcommand;


--
-- Name: flow_publication selfaliases; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.selfaliases;


--
-- Name: flow_publication selfprefix; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.selfprefix;


--
-- Name: flow_publication starboard; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.starboard;


--
-- Name: flow_publication starboard_messages; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.starboard_messages;


--
-- Name: flow_publication stickymessage; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.stickymessage;


--
-- Name: flow_publication suggestions; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.suggestions;


--
-- Name: flow_publication suggestions_blacklist; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.suggestions_blacklist;


--
-- Name: flow_publication suggestions_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.suggestions_module;


--
-- Name: flow_publication tags; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.tags;


--
-- Name: flow_publication ticket; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.ticket;


--
-- Name: flow_publication ticket_opened; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.ticket_opened;


--
-- Name: flow_publication ticket_topics; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.ticket_topics;


--
-- Name: flow_publication timezone; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.timezone;


--
-- Name: flow_publication usernames; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.usernames;


--
-- Name: flow_publication vanity; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.vanity;


--
-- Name: flow_publication vape; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.vape;


--
-- Name: flow_publication voicemaster; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.voicemaster;


--
-- Name: flow_publication voicemaster_buttons; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.voicemaster_buttons;


--
-- Name: flow_publication voicemaster_channels; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.voicemaster_channels;


--
-- Name: flow_publication vouches; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.vouches;


--
-- Name: flow_publication vouches_settings; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.vouches_settings;


--
-- Name: flow_publication warns; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.warns;


--
-- Name: flow_publication webhook; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.webhook;


--
-- Name: flow_publication webhook_username; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.webhook_username;


--
-- Name: flow_publication webhook_vanity; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.webhook_vanity;


--
-- Name: flow_publication welcome; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.welcome;


--
-- Name: flow_publication whitelist; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.whitelist;


--
-- Name: flow_publication whitelist_module; Type: PUBLICATION TABLE; Schema: public; Owner: postgres
--

ALTER PUBLICATION flow_publication ADD TABLE ONLY public.whitelist_module;


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;


--
-- PostgreSQL database dump complete
--

