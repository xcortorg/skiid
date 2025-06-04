from discord.ext.commands import (
    Cog,
    CommandError,
    command,
    group,
    has_permissions,
    Boolean,
)
from discord import Client, Color, Embed, File, Member, User
from typing import Union, Optional
from .util import Images
from lib.patch.context import Context
from io import BytesIO
from lib.classes.builtins import plural

ACTION_MAP = {
    "hug": "**hugs** {}",
    "kiss": "**kisses** {}",
    "pat": "**pats** {}",
    "poke": "**pokes** {}",
    "slap": "**slaps** {}",
    "bite": "**bites** {}",
    "kick": "**kicks** {}",
    "punch": "**punches** {}",
    "headpat": "**headpats** {}",
    "tickle": "**tickle** {}",
    "highfive": "**highfives** {}",
    "shrug": "**shrugs** {}",
    "wave": "**waves** {}",
    "blush": "**blushes** {}",
    "cry": "**cries** {}",
    "laugh": "**laughs** {}",
    "airkiss": "**air kisses** {}",
    "angrystare": "**angrily stares at** {}",
    "bleh": "**blehs at** {}",
    "brofist": "**brofists** {}",
    "celebrate": "**celebrates with** {}",
    "cheers": "**stares angrily at** {}",
    "clap": "**claps for** {}",
    "confused": "**is confused at** {}",
    "cool": "**is cooling with** {}",
    "cuddle": "**cuddles with** {}",
    "dance": "**dances with** {}",
    "drool": "**drools at** {}",
    "evillaugh": "**laughs evilly at** {}",
    "facepalm": "**face palmes** {}",
    "handhold": "**holds hands with** {}",
    "happy": "**is happy with**",
    "headbang": "**bangs their head at** {}",
    "huh": "**missed what** {} **said**",
    "lick": "**licks** {}",
    "love": "**gives love and affection to** {}",
    "mad": "**is mad at** {}",
    "nervous": "**gets nervous around** {}",
    "no": "**says no to** {}",
    "nom": "**nibbles** {}",
    "nuzzle": "**nuzzles** {}",
    "nyah": "**nyahhh's** {}",
    "peek": "**peeks** {}",
    "pinch": "**pinches** {}",
    "pout": "**pouts at** {}",
    "roll": "**has a temper tantrum because of** {}",
    "run": "**runs to** {}",
    "sad": "**is sad because of** {}",
    "scared": "**is scared of** {}",
    "shout": "**shouts at** {}",
    "shy": "**gets shy around** {}",
    "sigh": "**sighs at** {}",
    "sip": "**sips** {}",
    "sleep": "**sleeps with** {}",
    "slowclap": "**slowly claps at** {}",
    "smack": "**smacks** {}",
    "smile": "**smiles at** {}",
    "smug": "**smugs at** {}",
    "sneeze": "**sneezes on** {}",
    "sorry": "**is sorry to** {}",
    "stare": "**stares at** {}",
    "surprised": "**is surprised by** {}",
    "sweat": "**sweats around** {}",
    "thumbsup": "**gives a thumbs up to** {}",
    "tired": "**gets tired around** {}",
    "wink": "**winks at** {}",
    "woah": "**gasps at** {}",
    "yawn": "**yawns at** {}",
    "yay": "**gets excited around** {}",
    "yes": "**says yes to** {}",
}


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    async def cog_check(self, ctx: Context):
        if ctx.command.qualified_name != "roleplay":
            value = (
                await self.bot.db.fetchval(
                    """SELECT status FROM roleplay.status WHERE guild_id = $1""",
                    ctx.guild.id,
                )
                or False
            )
            if value is True:
                return True
            else:
                raise CommandError(
                    f"**Roleplay** commands are automatically disabled. Server administrators can use {ctx.prefix}roleplay enable to allow roleplay command usage."
                )
        else:
            return True

    async def execute(self, ctx: Context, member: Optional[Member] = None):
        if not member:
            member = ctx.author
        action = ctx.command.qualified_name.lower()
        file = File(fp=BytesIO(await Images.get(action)), filename="action.gif")

        amount = int(
            await self.bot.db.execute(
                """
			INSERT INTO roleplay.actions (action, giver, receiver, amount) 
			VALUES ($1, $2, $3, $4) 
			ON CONFLICT (action, giver, receiver) 
			DO UPDATE SET amount = roleplay.actions.amount + excluded.amount 
			RETURNING amount
		""",
                action,
                ctx.author.id,
                member.id,
                1,
            )
        )

        return await ctx.send(
            file=file,
            embed=Embed(
                color=self.bot.color,
                description=f"{ctx.author.mention} {ACTION_MAP[action].format(member.mention if member != ctx.author else 'themselves')} for the **{amount.ordinal()}** time!",
            ).set_image(url="attachment://action.gif"),
        )

    @command(name="roleplay", description="", example=",roleplay enable")
    @has_permissions(administrator=True)
    async def roleplay(self, ctx: Context, status: Boolean):
        await self.bot.db.execute(
            """INSERT INTO roleplay.status (guild_id, status) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET status = excluded.status""",
            ctx.guild.id,
            status,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if status else 'DISABLED'}** roleplay commands"
        )

    @command(
        name="hug", description="hug a member through the bot", example=",hug @aiohttp"
    )
    async def hug(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="kiss",
        description="kiss towards a member in chat",
        example=",kiss @aiohttp",
    )
    async def kiss(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="pat", description="pat towards a member in chat", example=",pat @aiohttp"
    )
    async def pat(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="poke",
        description="poke towards a member in chat",
        example=",poke @aiohttp",
    )
    async def poke(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="slap",
        description="slap towards a member in chat",
        example=",slap @aiohttp",
    )
    async def slap(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="bite",
        description="bite towards a member in chat",
        example=",bite @aiohttp",
    )
    async def bite(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="punch",
        description="punch towards a member in chat",
        example=",punch @aiohttp",
    )
    async def punch(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="headpat",
        description="headpat towards a member in chat",
        example=",headpat @aiohttp",
    )
    async def headpat(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="tickle",
        description="tickle towards a member in chat",
        example=",tickle @aiohttp",
    )
    async def tickle(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="highfive",
        description="highfive towards a member in chat",
        example=",highfive @aiohttp",
    )
    async def highfive(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="shrug",
        description="shrug towards a member in chat",
        example=",shrug @aiohttp",
    )
    async def shrug(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="wave",
        description="wave towards a member in chat",
        example=",wave @aiohttp",
    )
    async def wave(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="blush",
        description="blush towards a member in chat",
        example=",blush @aiohttp",
    )
    async def blush(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="cry", description="cry towards a member in chat", example=",cry @aiohttp"
    )
    async def cry(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="laugh",
        description="laugh towards a member in chat",
        example=",laugh @aiohttp",
    )
    async def laugh(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="airkiss",
        description="airkiss towards a member in chat",
        example=",airkiss @aiohttp",
    )
    async def airkiss(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="angrystare",
        description="angrystare towards a member in chat",
        example=",angrystare @aiohttp",
    )
    async def angrystare(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="bleh",
        description="bleh towards a member in chat",
        example=",bleh @aiohttp",
    )
    async def bleh(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="brofist",
        description="brofist towards a member in chat",
        example=",brofist @aiohttp",
    )
    async def brofist(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="celebrate",
        description="celebrate towards a member in chat",
        example=",celebrate @aiohttp",
    )
    async def celebrate(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="cheers",
        description="cheers towards a member in chat",
        example=",cheers @aiohttp",
    )
    async def cheers(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="clap",
        description="clap towards a member in chat",
        example=",clap @aiohttp",
    )
    async def clap(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="confused",
        description="confused towards a member in chat",
        example=",confused @aiohttp",
    )
    async def confused(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="cool",
        description="cool towards a member in chat",
        example=",cool @aiohttp",
    )
    async def cool(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="cuddle",
        description="cuddle towards a member in chat",
        example=",cuddle @aiohttp",
    )
    async def cuddle(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="dance",
        description="dance towards a member in chat",
        example=",dance @aiohttp",
    )
    async def dance(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="drool",
        description="drool towards a member in chat",
        example=",drool @aiohttp",
    )
    async def drool(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="evillaugh",
        description="evillaugh towards a member in chat",
        example=",evillaugh @aiohttp",
    )
    async def evillaugh(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="facepalm",
        description="facepalm towards a member in chat",
        example=",facepalm @aiohttp",
    )
    async def facepalm(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="handhold",
        description="handhold towards a member in chat",
        example=",handhold @aiohttp",
    )
    async def handhold(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="happy",
        description="happy towards a member in chat",
        example=",happy @aiohttp",
    )
    async def happy(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="headbang",
        description="headbang towards a member in chat",
        example=",headbang @aiohttp",
    )
    async def headbang(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="huh", description="huh towards a member in chat", example=",huh @aiohttp"
    )
    async def huh(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="lick",
        description="lick towards a member in chat",
        example=",lick @aiohttp",
    )
    async def lick(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="love",
        description="love towards a member in chat",
        example=",love @aiohttp",
    )
    async def love(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="mad", description="mad towards a member in chat", example=",mad @aiohttp"
    )
    async def mad(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="nervous",
        description="nervous towards a member in chat",
        example=",nervous @aiohttp",
    )
    async def nervous(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="no", description="no towards a member in chat", example=",no @aiohttp"
    )
    async def no(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="nom", description="nom towards a member in chat", example=",nom @aiohttp"
    )
    async def nom(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="nosebleed",
        description="nosebleed towards a member in chat",
        example=",nosebleed @aiohttp",
    )
    async def nosebleed(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="nuzzle",
        description="nuzzle towards a member in chat",
        example=",nuzzle @aiohttp",
    )
    async def nuzzle(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="nyah",
        description="nyah towards a member in chat",
        example=",nyah @aiohttp",
    )
    async def nyah(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="peek",
        description="peek towards a member in chat",
        example=",peek @aiohttp",
    )
    async def peek(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="pinch",
        description="pinch towards a member in chat",
        example=",pinch @aiohttp",
    )
    async def pinch(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="pout",
        description="pout towards a member in chat",
        example=",pout @aiohttp",
    )
    async def pout(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="roll",
        description="roll towards a member in chat",
        example=",roll @aiohttp",
    )
    async def roll(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="run", description="run towards a member in chat", example=",run @aiohttp"
    )
    async def run(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sad", description="sad towards a member in chat", example=",sad @aiohttp"
    )
    async def sad(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="scared",
        description="scared towards a member in chat",
        example=",scared @aiohttp",
    )
    async def scared(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="shout",
        description="shout towards a member in chat",
        example=",shout @aiohttp",
    )
    async def shout(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="shy", description="shy towards a member in chat", example=",shy @aiohttp"
    )
    async def shy(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sigh",
        description="sigh towards a member in chat",
        example=",sigh @aiohttp",
    )
    async def sigh(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sip", description="sip towards a member in chat", example=",sip @aiohttp"
    )
    async def sip(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sleep",
        description="sleep towards a member in chat",
        example=",sleep @aiohttp",
    )
    async def sleep(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="slowclap",
        description="slowclap towards a member in chat",
        example=",slowclap @aiohttp",
    )
    async def slowclap(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="smack",
        description="smack towards a member in chat",
        example=",smack @aiohttp",
    )
    async def smack(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="smile",
        description="smile towards a member in chat",
        example=",smile @aiohttp",
    )
    async def smile(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="smug",
        description="smug towards a member in chat",
        example=",smug @aiohttp",
    )
    async def smug(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sneeze",
        description="sneeze towards a member in chat",
        example=",sneeze @aiohttp",
    )
    async def sneeze(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sorry",
        description="sorry towards a member in chat",
        example=",sorry @aiohttp",
    )
    async def sorry(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="stare",
        description="stare towards a member in chat",
        example=",stare @aiohttp",
    )
    async def stare(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="surprised",
        description="surprised towards a member in chat",
        example=",surprised @aiohttp",
    )
    async def surprised(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="sweat",
        description="sweat towards a member in chat",
        example=",sweat @aiohttp",
    )
    async def sweat(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="thumbsup",
        description="thumbsup towards a member in chat",
        example=",thumbsup @aiohttp",
    )
    async def thumbsup(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="tired",
        description="tired towards a member in chat",
        example=",tired @aiohttp",
    )
    async def tired(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="wink",
        description="wink towards a member in chat",
        example=",wink @aiohttp",
    )
    async def wink(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="woah",
        description="woah towards a member in chat",
        example=",woah @aiohttp",
    )
    async def woah(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="yawn",
        description="yawn towards a member in chat",
        example=",yawn @aiohttp",
    )
    async def yawn(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="yay", description="yay towards a member in chat", example=",yay @aiohttp"
    )
    async def yay(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)

    @command(
        name="yes", description="yes towards a member in chat", example=",yes @aiohttp"
    )
    async def yes(self, ctx: Context, *, member: Optional[Member] = None):
        return await self.execute(ctx, member)
