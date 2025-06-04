--
-- PostgreSQL database dump
--

-- Dumped from database version 14.11 (Ubuntu 14.11-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.11 (Ubuntu 14.11-0ubuntu0.22.04.1)

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
-- Name: adminpack; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS adminpack WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION adminpack; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION adminpack IS 'administrative functions for PostgreSQL';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: access_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.access_tokens (
    user_id bigint,
    refresh_token text
);


ALTER TABLE public.access_tokens OWNER TO postgres;

--
-- Name: afk; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.afk (
    guild_id bigint,
    user_id bigint,
    reason text,
    "time" timestamp with time zone
);


ALTER TABLE public.afk OWNER TO postgres;

--
-- Name: aliases; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.aliases (
    guild_id bigint NOT NULL,
    command text NOT NULL,
    alias text NOT NULL
);


ALTER TABLE public.aliases OWNER TO postgres;

--
-- Name: anti_join; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.anti_join (
    guild_id bigint,
    rate integer
);


ALTER TABLE public.anti_join OWNER TO postgres;

--
-- Name: antinuke; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke (
    guild_id bigint,
    configured text,
    owner_id bigint,
    whitelisted jsonb,
    admins jsonb,
    logs bigint
);


ALTER TABLE public.antinuke OWNER TO postgres;

--
-- Name: antinuke_modules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antinuke_modules (
    guild_id bigint,
    module text,
    punishment text,
    threshold integer
);


ALTER TABLE public.antinuke_modules OWNER TO postgres;

--
-- Name: antispam; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.antispam (
    guild_id bigint,
    rate integer,
    timeout bigint,
    users text,
    channels text
);


ALTER TABLE public.antispam OWNER TO postgres;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_keys (
    user_id bigint,
    key text
);


ALTER TABLE public.api_keys OWNER TO postgres;

--
-- Name: authorize; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.authorize (
    guild_id bigint,
    user_id bigint,
    till timestamp with time zone,
    transfers integer
);


ALTER TABLE public.authorize OWNER TO postgres;

--
-- Name: autoping; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoping (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text NOT NULL
);


ALTER TABLE public.autoping OWNER TO postgres;

--
-- Name: autoreact; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoreact (
    guild_id bigint NOT NULL,
    trigger text NOT NULL,
    reactions text NOT NULL
);


ALTER TABLE public.autoreact OWNER TO postgres;

--
-- Name: autoreacts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoreacts (
    guild_id bigint NOT NULL,
    trigger text NOT NULL,
    reaction text NOT NULL
);


ALTER TABLE public.autoreacts OWNER TO postgres;

--
-- Name: autoresponder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autoresponder (
    guild_id bigint,
    trigger text,
    response text,
    strict boolean DEFAULT true
);


ALTER TABLE public.autoresponder OWNER TO postgres;

--
-- Name: autorole; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.autorole (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.autorole OWNER TO postgres;

--
-- Name: avatar_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_history (
    user_id bigint NOT NULL,
    name text,
    avatars text,
    background text
);


ALTER TABLE public.avatar_history OWNER TO postgres;

--
-- Name: avatar_urls; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatar_urls (
    user_id bigint,
    token text,
    data bytea
);


ALTER TABLE public.avatar_urls OWNER TO postgres;

--
-- Name: avatars; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.avatars (
    user_id bigint NOT NULL,
    name text NOT NULL,
    avatar text NOT NULL,
    key text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL
);


ALTER TABLE public.avatars OWNER TO postgres;

--
-- Name: bday; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bday (
    user_id bigint,
    month integer,
    day integer
);


ALTER TABLE public.bday OWNER TO postgres;

--
-- Name: birthday; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.birthday (
    user_id bigint,
    bday timestamp with time zone,
    said text
);


ALTER TABLE public.birthday OWNER TO postgres;

--
-- Name: blacklist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.blacklist (
    id bigint NOT NULL,
    type text NOT NULL
);


ALTER TABLE public.blacklist OWNER TO postgres;

--
-- Name: boost; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.boost (
    guild_id bigint,
    channel_id bigint,
    message text
);


ALTER TABLE public.boost OWNER TO postgres;

--
-- Name: booster_module; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_module (
    guild_id bigint,
    base bigint
);


ALTER TABLE public.booster_module OWNER TO postgres;

--
-- Name: booster_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booster_roles (
    guild_id bigint,
    user_id bigint,
    role_id bigint
);


ALTER TABLE public.booster_roles OWNER TO postgres;

--
-- Name: br_award; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.br_award (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.br_award OWNER TO postgres;

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


ALTER TABLE public.bumpreminder OWNER TO postgres;

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
-- Name: counters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.counters (
    guild_id bigint,
    channel_type text,
    channel_id bigint,
    channel_name text,
    module text
);


ALTER TABLE public.counters OWNER TO postgres;

--
-- Name: disablecmd; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.disablecmd (
    guild_id bigint,
    cmd text
);


ALTER TABLE public.disablecmd OWNER TO postgres;

--
-- Name: donor; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.donor (
    user_id bigint,
    since bigint,
    status text
);


ALTER TABLE public.donor OWNER TO postgres;

--
-- Name: economy; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.economy (
    user_id bigint,
    cash double precision,
    card double precision,
    daily bigint,
    dice bigint
);


ALTER TABLE public.economy OWNER TO postgres;

--
-- Name: error_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.error_codes (
    code character varying(30) NOT NULL,
    info json
);


ALTER TABLE public.error_codes OWNER TO postgres;

--
-- Name: fake_perms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.fake_perms (
    guild_id bigint,
    role_id bigint,
    perms text
);


ALTER TABLE public.fake_perms OWNER TO postgres;

--
-- Name: filter; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.filter (
    guild_id bigint,
    mode text,
    rule_id bigint
);


ALTER TABLE public.filter OWNER TO postgres;

--
-- Name: force_nick; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.force_nick (
    guild_id bigint,
    user_id bigint,
    nickname text
);


ALTER TABLE public.force_nick OWNER TO postgres;

--
-- Name: gamestats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gamestats (
    user_id bigint,
    game text,
    wins integer,
    loses integer,
    total integer
);


ALTER TABLE public.gamestats OWNER TO postgres;

--
-- Name: give_roles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.give_roles (
    guild_id bigint,
    role_id bigint
);


ALTER TABLE public.give_roles OWNER TO postgres;

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
    title text
);


ALTER TABLE public.giveaway OWNER TO postgres;

--
-- Name: global_disabled_cmds; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.global_disabled_cmds (
    cmd character varying(30) NOT NULL,
    disabled boolean,
    disabled_by text
);


ALTER TABLE public.global_disabled_cmds OWNER TO postgres;

--
-- Name: globalban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.globalban (
    user_id bigint,
    reason text
);


ALTER TABLE public.globalban OWNER TO postgres;

--
-- Name: gw_ended; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.gw_ended (
    channel_id bigint,
    message_id bigint,
    members text
);


ALTER TABLE public.gw_ended OWNER TO postgres;

--
-- Name: hardban; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hardban (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    reason text,
    moderator_id bigint NOT NULL
);


ALTER TABLE public.hardban OWNER TO postgres;

--
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.images (
    id text,
    url text
);


ALTER TABLE public.images OWNER TO postgres;

--
-- Name: invoke; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.invoke (
    guild_id bigint,
    command text,
    embed text
);


ALTER TABLE public.invoke OWNER TO postgres;

--
-- Name: jail; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jail (
    guild_id bigint,
    channel_id bigint,
    role_id bigint
);


ALTER TABLE public.jail OWNER TO postgres;

--
-- Name: jail_members; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jail_members (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    roles text,
    jailed_at timestamp with time zone
);


ALTER TABLE public.jail_members OWNER TO postgres;

--
-- Name: lastfm; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lastfm (
    user_id bigint,
    username text,
    reactions text,
    customcmd text,
    embed text
);


ALTER TABLE public.lastfm OWNER TO postgres;

--
-- Name: leave; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leave (
    guild_id bigint,
    channel_id bigint,
    message text
);


ALTER TABLE public.leave OWNER TO postgres;

--
-- Name: level_rewards; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.level_rewards (
    guild_id bigint,
    level integer,
    role_id bigint
);


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


ALTER TABLE public.level_user OWNER TO postgres;

--
-- Name: leveling; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leveling (
    guild_id bigint,
    channel_id bigint,
    message text,
    booster_boost text
);


ALTER TABLE public.leveling OWNER TO postgres;

--
-- Name: lock_role; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lock_role (
    guild_id bigint NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.lock_role OWNER TO postgres;

--
-- Name: lockdown_ignore; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lockdown_ignore (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL
);


ALTER TABLE public.lockdown_ignore OWNER TO postgres;

--
-- Name: logging; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logging (
    guild_id bigint NOT NULL,
    messages bigint,
    guild bigint
);


ALTER TABLE public.logging OWNER TO postgres;

--
-- Name: logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.logs (
    key text NOT NULL,
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    author jsonb DEFAULT '{}'::jsonb NOT NULL,
    logs jsonb DEFAULT '{}'::jsonb NOT NULL
);


ALTER TABLE public.logs OWNER TO postgres;

--
-- Name: marry; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.marry (
    author bigint,
    soulmate bigint,
    "time" bigint
);


ALTER TABLE public.marry OWNER TO postgres;

--
-- Name: number_counter; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.number_counter (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    last_counted bigint,
    current_number integer
);


ALTER TABLE public.number_counter OWNER TO postgres;

--
-- Name: opened_tickets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.opened_tickets (
    guild_id bigint,
    channel_id bigint,
    user_id bigint
);


ALTER TABLE public.opened_tickets OWNER TO postgres;

--
-- Name: prefixes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.prefixes (
    guild_id bigint NOT NULL,
    prefix text
);


ALTER TABLE public.prefixes OWNER TO postgres;

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


ALTER TABLE public.reactionrole OWNER TO postgres;

--
-- Name: reminder; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reminder (
    user_id bigint,
    channel_id bigint,
    guild_id bigint,
    date timestamp with time zone,
    task text
);


ALTER TABLE public.reminder OWNER TO postgres;

--
-- Name: reskin; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reskin (
    user_id bigint,
    username text,
    avatar_url text
);


ALTER TABLE public.reskin OWNER TO postgres;

--
-- Name: reskin_enabled; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reskin_enabled (
    guild_id bigint
);


ALTER TABLE public.reskin_enabled OWNER TO postgres;

--
-- Name: restore; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restore (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL,
    roles text
);


ALTER TABLE public.restore OWNER TO postgres;

--
-- Name: restrictcommand; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.restrictcommand (
    guild_id bigint NOT NULL,
    command text NOT NULL,
    role_id bigint NOT NULL
);


ALTER TABLE public.restrictcommand OWNER TO postgres;

--
-- Name: seen; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.seen (
    user_id bigint,
    guild_id bigint,
    "time" timestamp with time zone
);


ALTER TABLE public.seen OWNER TO postgres;

--
-- Name: selfprefix; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.selfprefix (
    user_id bigint NOT NULL,
    prefix text
);


ALTER TABLE public.selfprefix OWNER TO postgres;

--
-- Name: spotify; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.spotify (
    user_id bigint,
    access_token text
);


ALTER TABLE public.spotify OWNER TO postgres;

--
-- Name: starboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.starboard (
    guild_id bigint,
    channel_id bigint,
    emoji text,
    count integer,
    role_id bigint
);


ALTER TABLE public.starboard OWNER TO postgres;

--
-- Name: starboard_messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.starboard_messages (
    guild_id bigint,
    channel_id bigint,
    message_id bigint,
    starboard_message_id bigint
);


ALTER TABLE public.starboard_messages OWNER TO postgres;

--
-- Name: stickymessage; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stickymessage (
    guild_id bigint NOT NULL,
    channel_id bigint NOT NULL,
    message text NOT NULL
);


ALTER TABLE public.stickymessage OWNER TO postgres;

--
-- Name: ticket_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ticket_topics (
    guild_id bigint,
    name text,
    description text
);


ALTER TABLE public.ticket_topics OWNER TO postgres;

--
-- Name: tickets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tickets (
    guild_id bigint,
    open_embed text,
    category_id bigint,
    logs bigint,
    support_id bigint
);


ALTER TABLE public.tickets OWNER TO postgres;

--
-- Name: timezone; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.timezone (
    user_id bigint,
    zone text
);


ALTER TABLE public.timezone OWNER TO postgres;

--
-- Name: trials; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.trials (
    guild_id bigint NOT NULL,
    expires bigint NOT NULL
);


ALTER TABLE public.trials OWNER TO postgres;

--
-- Name: username_track; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.username_track (
    guild_id bigint,
    webhook_url text
);


ALTER TABLE public.username_track OWNER TO postgres;

--
-- Name: usernames; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usernames (
    user_id bigint,
    user_name text,
    "time" bigint
);


ALTER TABLE public.usernames OWNER TO postgres;

--
-- Name: vcs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vcs (
    user_id bigint,
    voice bigint
);


ALTER TABLE public.vcs OWNER TO postgres;

--
-- Name: vm_buttons; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vm_buttons (
    guild_id bigint,
    action text,
    label text,
    emoji text,
    style text
);


ALTER TABLE public.vm_buttons OWNER TO postgres;

--
-- Name: voicemaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.voicemaster (
    guild_id bigint,
    channel_id bigint,
    interface_id bigint
);


ALTER TABLE public.voicemaster OWNER TO postgres;

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


ALTER TABLE public.warns OWNER TO postgres;

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


ALTER TABLE public.webhook OWNER TO postgres;

--
-- Name: welcome; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.welcome (
    guild_id bigint,
    channel_id bigint,
    message text
);


ALTER TABLE public.welcome OWNER TO postgres;

--
-- Name: whitelist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.whitelist (
    guild_id bigint NOT NULL,
    user_id bigint NOT NULL
);


ALTER TABLE public.whitelist OWNER TO postgres;

--
-- Name: whitelist_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.whitelist_state (
    guild_id bigint NOT NULL,
    embed text
);


ALTER TABLE public.whitelist_state OWNER TO postgres;

--
-- Name: xray; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.xray (
    guild_id bigint,
    target_id bigint,
    webhook_url text
);


ALTER TABLE public.xray OWNER TO postgres;

--
-- Name: autoping autoping_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoping
    ADD CONSTRAINT autoping_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: autoreact autoreact_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoreact
    ADD CONSTRAINT autoreact_pkey PRIMARY KEY (guild_id, trigger);


--
-- Name: autoreacts autoreacts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autoreacts
    ADD CONSTRAINT autoreacts_pkey PRIMARY KEY (guild_id, trigger, reaction);


--
-- Name: autorole autorole_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.autorole
    ADD CONSTRAINT autorole_pkey PRIMARY KEY (guild_id, role_id);


--
-- Name: avatar_history avatar_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatar_history
    ADD CONSTRAINT avatar_history_pkey PRIMARY KEY (user_id);


--
-- Name: avatars avatars_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.avatars
    ADD CONSTRAINT avatars_pkey PRIMARY KEY (user_id, key);


--
-- Name: blacklist blacklist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.blacklist
    ADD CONSTRAINT blacklist_pkey PRIMARY KEY (id, type);


--
-- Name: error_codes error_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.error_codes
    ADD CONSTRAINT error_codes_pkey PRIMARY KEY (code);


--
-- Name: global_disabled_cmds global_disabled_cmds_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.global_disabled_cmds
    ADD CONSTRAINT global_disabled_cmds_pkey PRIMARY KEY (cmd);


--
-- Name: jail_members jail_members_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jail_members
    ADD CONSTRAINT jail_members_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: lock_role lock_role_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lock_role
    ADD CONSTRAINT lock_role_pkey PRIMARY KEY (role_id);


--
-- Name: lockdown_ignore lockdown_ignore_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lockdown_ignore
    ADD CONSTRAINT lockdown_ignore_pkey PRIMARY KEY (channel_id);


--
-- Name: logs logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.logs
    ADD CONSTRAINT logs_pkey PRIMARY KEY (key);


--
-- Name: number_counter number_counter_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.number_counter
    ADD CONSTRAINT number_counter_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: restore restore_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.restore
    ADD CONSTRAINT restore_pkey PRIMARY KEY (guild_id, user_id);


--
-- Name: selfprefix selfprefix_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.selfprefix
    ADD CONSTRAINT selfprefix_pkey PRIMARY KEY (user_id);


--
-- Name: stickymessage stickymessage_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stickymessage
    ADD CONSTRAINT stickymessage_pkey PRIMARY KEY (guild_id, channel_id);


--
-- Name: trials trials_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.trials
    ADD CONSTRAINT trials_pkey PRIMARY KEY (guild_id);


--
-- Name: whitelist_state whitelist_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.whitelist_state
    ADD CONSTRAINT whitelist_state_pkey PRIMARY KEY (guild_id);


--
-- PostgreSQL database dump complete
--
