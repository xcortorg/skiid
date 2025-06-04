import os
import json
import logging
import asyncio
import datetime
import threading

from flask import Flask, jsonify, request

from discord import Spotify
from discord.ext import commands

from modules.evelinabot import Evelina

app = Flask(__name__)
bot_instance = None
loop = asyncio.get_event_loop()

log = logging.getLogger('werkzeug')
log.disabled = True

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVELINA_DIR = os.path.join(BASE_DIR, '../..', 'bot')

commands_file_path = os.path.join(EVELINA_DIR, 'commands.json')
shards_file_path = os.path.join(EVELINA_DIR, 'shards.json')
topservers_file_path = os.path.join(EVELINA_DIR, 'topservers.json')
banners = {}
decorations = {}

@app.route('/shards', methods=['GET'])
def get_shards():
    try:
        with open(shards_file_path, 'r') as f:
            shards_data = json.load(f)
        return jsonify(shards_data), 200
    except FileNotFoundError:
        return jsonify({"error": "Shards file not found"}), 404

@app.route('/commands', methods=['GET'])
def get_commands():
    try:
        with open(commands_file_path, 'r') as f:
            commands_data = json.load(f)
        return jsonify(commands_data), 200
    except FileNotFoundError:
        return jsonify({"error": "Commands file not found"}), 404
    
@app.route('/team', methods=['GET'])
def get_team():
    try:
        team = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM team_members"), loop).result()
        team_info = []
        for member in team:
            team_info.append({
                'user_id': str(member['user_id']),
                'rank': member['rank'],
                'socials': member['socials']
            })
        return jsonify(team_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/templates', methods=['GET'])
def get_templates():
    try:
        templates = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM embeds_templates ORDER BY id DESC"), loop).result()
        templates_info = []
        for template in templates:
            templates_info.append({
                'id': str(template['id']),
                'name': str(template['name']),
                'user_id': str(template['user_id']),
                'code': str(template['code']),
                'embed': str(template['embed']),
                'image': str(template['image']),
            })
        return jsonify(templates_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/feedback', methods=['GET'])
def get_feedback():
    try:
        feedback = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM testimonials"), loop).result()
        feedback_info = []
        for message in feedback:
            feedback_info.append({
                'guild_id': str(message['guild_id']),
                'user_id': str(message['user_id']),
                'message_id': str(message['message_id']),
                'feedback': str(message['feedback']),
                'approved': message['approved'],
            })
        return jsonify(feedback_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/avatars', methods=['GET'])
def get_avatars():
    try:
        avatars = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM avatar_history"), loop).result()
        avatars_info = []
        for avatar in avatars:
            avatars_info.append({
                'user_id': str(avatar['user_id']),
                'avatar': str(avatar['avatar']),
                'timestamp': avatar['timestamp'],
            })
        return jsonify(avatars_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/avatars/<int:user_id>', methods=['GET'])
def get_user_avatars(user_id):
    try:
        avatars = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM avatar_history WHERE user_id = $1", user_id), loop).result()
        avatars_info = []
        for avatar in avatars:
            avatars_info.append({
                'user_id': str(avatar['user_id']),
                'avatar': str(avatar['avatar']),
                'timestamp': avatar['timestamp'],
            })
        return jsonify(avatars_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/history", methods=['GET'])
def get_history():
    try:
        history = asyncio.run_coroutine_threadsafe(bot_instance.db.fetch("SELECT * FROM growth"), loop).result()
        history_info = []
        for entry in history:
            history_info.append({
                'guilds': entry['guilds'],
                'users': entry['users'],
                'ping': entry['ping'],
                'timestamp': entry['timestamp']
            })
        return jsonify(history_info), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/user/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = bot_instance.get_user(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        guild = bot_instance.get_guild(bot_instance.logging_guild)
        member = guild.get_member(user.id)

        activity_name = ""
        activity_details = ""
        activity_state = ""
        activity_image = ""
        activity_emoji = ""

        if member and member.activity:
            if member.activity.type.value == 4:
                activity_name = member.activity.name
                activity_state = ""
                activity_emoji = member.activity.emoji.url if member.activity.emoji else ""
            elif isinstance(member.activity, Spotify):
                activity_name = "Spotify"
                activity_details = f"{member.activity.title}"
                activity_state = f"by {member.activity.artist}"
                activity_image = member.activity.album_cover_url
            elif member.activity.type.value in [0, 1, 2, 3]:
                activity_name = member.activity.name
                activity_details = getattr(member.activity, 'details', '')
                activity_state = getattr(member.activity, 'state', '')
                activity_image = getattr(member.activity, 'large_image_url', '')

        if user_id in banners:
            banner = banners[user_id]
        else:
            user_obj = asyncio.run_coroutine_threadsafe(bot_instance.fetch_user(user_id), loop).result()
            banner = user_obj.banner.url if user_obj.banner else f"https://place-hold.it/680x240/000001?text=%20"
            banners[user_id] = banner
            threading.Timer(60, lambda: banners.pop(user_id, None)).start()

        if user_id in decorations:
            decoration = decorations[user_id]
        else:
            decoration = user_obj.avatar_decoration.url if user_obj.avatar_decoration else None
            decorations[user_id] = decoration
            threading.Timer(60, lambda: decorations.pop(user_id, None)).start()

        return jsonify({
            'user': user.name,
            'avatar': user.avatar.url if user.avatar else user.default_avatar.url,
            'banner': user.banner.url if user.banner else banner,
            'decoration': user.avatar_decoration.url if user.avatar_decoration else decoration,
            'activity': {
                'name': activity_name,
                'details': activity_details,
                'state': activity_state,
                'image': activity_image,
                'emoji': activity_emoji
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@commands.command(name="start")
async def start(ctx):
    allowed_role_ids = [1237426196422328381, 1305786245942743061, 1293528425763704915, 1267401506555166793, 1272482302227910708]
    if not any(role.id in allowed_role_ids for role in ctx.author.roles):
        return await ctx.send("You are not allowed to use this command.")
    os.system("pm2 restart 0")
    return await ctx.send("Trying to restart Evelina")

async def get_used_card(user_id: int, business: str):
    card_used = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, business)
    if card_used:
        card_user = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
        if card_user:
            card_info = await bot_instance.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
            if card_info:
                name = card_info["name"]
                stars = card_info["stars"]
                storage = card_user["storage"]
                multiplier = card_user["multiplier"]
                return name, stars, storage, multiplier
    return None, None, None, None

async def calculate_lab_earnings_and_upgrade(user_id: int, upgrade_state: int):
    hours = 6
    multiplier = 1
    card_used = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, "lab")
    if card_used:
        card_user = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
        if card_user:
            card_info = await bot_instance.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
            if card_info:
                hours = card_user["storage"]
                multiplier = card_user["multiplier"]
    base_earnings_per_hour = 10000 + (5000 * upgrade_state)
    earnings_multiplier = 1 + (0.1 * upgrade_state)
    earnings_per_hour = base_earnings_per_hour * earnings_multiplier
    earnings_per_hour *= multiplier
    earnings_cap = earnings_per_hour * hours
    next_upgrade_cost = (base_earnings_per_hour * 24) * (1 + 0.1 * upgrade_state)
    return earnings_per_hour, earnings_cap, next_upgrade_cost
    
async def calculate_business_earning(user_id: int, last_collected, hourrevenue):
    earnings = 0
    hours = 6
    multiplier = 1
    card_used = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, "business")
    if card_used:
        card_user = await bot_instance.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
        if card_user:
            card_info = await bot_instance.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
            if card_info:
                hours = card_user["storage"]
                multiplier = card_user["multiplier"]
    time_difference = datetime.datetime.now().timestamp() - last_collected
    if time_difference >= 3600:
        earnings = hourrevenue * (time_difference // 3600)
    earnings_cap = hourrevenue * hours
    if earnings > earnings_cap:
        earnings = earnings_cap
    earnings *= multiplier
    return earnings

def run_flask():
    app.run(host='0.0.0.0', port=1338, threaded=False)

async def setup(bot: Evelina) -> None:
    global bot_instance
    bot_instance = bot
    bot.add_command(start)
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()