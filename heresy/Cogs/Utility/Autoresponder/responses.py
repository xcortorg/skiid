import discord
from discord.ext import commands
import random

class Responses(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.responses = {
            "<@1284037026672279635>": [
                "what?",
                "what u want bruh?",
                "what bro",
                "why are you pinging me 😭",
                "dude what? im a bot bro why are u pinging me",
                "why is this nigga pinging me, like.. IM JUST A BOT, I DONT HAVE SENTIENCE 😭",
                "why did bro just ping me",
                "did this nigga just ping a bot",
                "bro why am i getting pinged",
                "who the fuck is pinging a bot",
                "nigga did u jus ping me",
                "stop pinging me pls",
                "bro pls dont ping me",
                ":c wat",
                "ooh someone pinged me, i feel wanted",
                "bro your literally gonna break my code by pinging me this much.",
                "asshole dont ping me bruh",
                "I feel violated with these pings",
                "pls stop pinging me",
                "## i went under a great depression after my owner touched me."
            ],
            "im gonna finger": [
                "?????",
                "my nigga, what the fuck??",
                "ah HELL NAH",
                "me next?",
                "im gonna finger <@785042666475225109>",
                "bro can i be next",
                "who is fingering who???",
                "bro what yall kno about the fingergeddon"
            ],
            "bend over": [
                "dude what.",
                "nigga what???",
                "aint no way 😭",
                "bend over is wild",
                "im gonna bend u over <@785042666475225109>",
                "im gona bend all of yall over",
                "bro the next person who says bend over, im gonna fucking touch u",
                "bend over n touch your toes and i'll show u where the monster goes"
            ],
            "mommy": [
                "im sorry but did this nigga just say mommy",
                "mommy is genuinely insane bro",
                "😭MOMMY??",
                "BRO SAID MOMMY 💀",
                "im your daddy lil bro.",
                "i thought i was mommy :c, is bro cheating on me now",
                "my nigga jus said mommy 😭",
                "'cant let gang kno i call people on discord mommy' ahh message",
                "bro better delete that 'mommmy' before someone calls him out LMFAO",
                "bro said mommy, chat clip it",
                "screenshotted (im a bot, i cant screenshot shit)",
                "whos my good boy?"
            ],
            "cum": [
                "i am NOT cumming lil bro",
                "did someone jus say cum..",
                "im cumming",
                "😭bro said cum",
                "what is this cum you speak of gang",
                "im cumming on <@785042666475225109>",
                "cum for me <@1256856675520876696>💀",
                "bro if i see even one nigga say cum, i stfg im gonna blow a load",
                "my fav word is cum btw",
                "cum for me"
            ],
            "kms": [
                "Help is (not) available, Speak with someone today (never) at 1-800-273-8255 "
            ],
            "pull the trigger": [
                "whoa what???",
                "bro..",
                "whoa slow down..",
                "nigga what",
                "dont pull the trigger lil bro 😭",
                "bro if u pull that trigger im gonna pull up to <@785042666475225109>'s house",
                "bro why",
                "dont pull the trigger bro 😭",
                "its ok lil bro its just life"
            ],
            "dont care": [
                "no one cares if u care bruh ",
                "bro said dont care 😭 man im hurt",
                "cool nigga",
                "'dont care + didnt ask + ratio' head ahh",
                "you should care tho",
                "bro really dont care fr",
                "damn bro aint care 😭"
            ],
            "kys": [
                "dont say that, they'll prolly actually do it 😭",
                "kys is wild, me personally i wouldnt take that",
                "nigga what",
                "bro jus said kys so casually wtf",
                "bro u wild 😭",
                "KYS?? nigga u good??",
                "dont die bro its not that deep",
                "damn bro wishin death upon niggas now",
                "is bro an opp or wha, why we wishing death upon niggas now 😭"
            ],
            ",cs": [
                "bro what are u tryna clear snipe for",
                "why is bro tryna clear snipe?",
                "what is nigga hiding that needs a fucking cs",
                "im ngl, i dont even wanna kno what this nigga said that made him need to clear snipe",
                "whatchu tryna hide lil bro?",
                "whats this nigga tryna hide hm?",
            ],
            "type shit": [
                "type shit",
                "type shi"
            ],
            "fe!n": [
                "fin fin fin fin fin fin fin fin fin",
                "JUST COME OUTSIDE, FOR THE NIGHT, TAKE YOUR TIME, GET YOUR LIGHT, JOHNNY DANG, YEA YEA, I BEEN OUT GEEKING, BITCH",
                "# FE!N FE!N FE!N FE!N FE!N FE!N FE!N FE!N FE!N FE!N",
            ],
            "pocket pussy": [
                "my nigga, chill",
                "bro what are you talking about",
                "I want a pocket pussy",
                "pocket pussy?? bro what are u saying",
                "stfu"
            ],
            "wanna play with my peepee": [
                "nah",
                "PEEPEE???😭",
                "bro 😭",
                "this nigga said PEEPEE LMFAOO 😭"
            ],
            "gonna put it in your mouth": [
                "im sorry what???",
                "bro, what?? put WHAT exactly in my mouth??",
                "you gay asl nigga",
                "please dont",
                "oh yes please stick it so far down my throat 😩",
                "oh just like that? bet please choke me 😫"
            ],
            "my dick":[
                "ah hell nah nigga u gay as fuck",
                "yea bro your gay as fuck wtf",
                "bro i dont want your dick nigga",
                "fuck up nigga u sound zesty asf",
                "ew",
                "nigga gay",
                "uhm, what?😭"
            ],
            "guns.lol": [
                "https://guns.lol/Heresy"
            ],
            "i hate jews": [
                "i hate jews too",
                "hail hitler my nigga",
                "gas em up 😭"
            ],
            "faggot": [
                "nigga you cant say that",
                "chill with the faggot word, its kinda wild",
                "faggot?? WHERE"
            ],
            "jew": [
                "hail hitler",
                "nein",
                "# ERIKAAAA"
            ],
            "balls": [
                "i have ball cancer",
                "imma put my balls in yo mouth gang"
            ],
            "uwu": [
                "My nigga, do you wanna get banned?",
                "# We don't say UwU here.",
                "Nigga, don't say that shit, u gonna get banned",
                "Ew this nigga said uwu 😭",
                "please commit suicide, why would u even say uwu ts so corny and cringe"
            ],
            ",akf": [
                "how do you misspell afk my nigga",
                "bro, its a 3 letter word how do u fuck that up",
                "bro misspelt afk no fucking way",
                "its afk btw",
                "whats akf?"
            ],
            ",satus": [
                "nigga you spelt it wrong",
                "its ,status btw",
                "how do u misspell your own command",
                "wtf is ,satus huh?"
            ],
            ",staus": [
                "is your spelling this bad nigga, u just misspelt your own bots command",
                "yea bro btw its fucking ,status not ,staus u fucking retard",
                "how are u this bad at spelling your own bot command"
            ],
            "yippe": [
                "https://tenor.com/view/yippee-happy-yippee-creature-yippee-meme-yippee-gif-gif-1489386840712152603"
            ],
            "i literally made you": [
                "'i brought u into this world and i will take you out of it' head ass 😭"
            ],
            "stfu": [
                "who is you talkin to like that son",
                "who are you tellin to stfu??",
                "nigga i hope you aint tellin me to stfu",
                "nigga YOU stfu",
                "nah bro, how about you stfu",
                "nah bro tellin a bot to stfu 😭",
                "nigga beefing with a ROBOT 😭"
            ],
            "where the fuck my blunt, where the fuck my cup, where the fuck my reefer": [
                "# HUH HUH HUH HUH HUH HUH, IM SMOKING ON KUSH, HUH HUH HUH HUH HUH HUH, IM SMOKING ON KUSH"
            ],
            ",bleed": [
                "Bleed files not found, try changing file(s) location to a different folder"
            ],
            "what is Heresy": [
                "Heresy is the act of holding or promoting beliefs or opinions that go against the established doctrines of a religious, social, or political system, particularly within the context of religion. Historically, it often referred to deviations from the teachings of a dominant church or faith; The 6th Circle of Dante's Inferno."
            ],
            "band for band": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "ur poor": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "pooron": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "harm u": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "show funds": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "harm you": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "im in extorting com": [
                "https://cdn.discordapp.com/attachments/1302445192762359900/1302459603266699314/com_kid_bingo.gif?ex=672ccec7&is=672b7d47&hm=f1a89f9ae4669cfb7d36b86927067e332a95d7a91a1fbde3bfd376b33b55b7ae&"
            ],
            "stop fighting": [
                "https://cdn.discordapp.com/attachments/1087100819066867762/1264261435819687956/togif.gif?ex=672cee37&is=672b9cb7&hm=44f9bdf35ed1309ee27529e038a33d0452afb87d9a9490d84631a0526d7a72f6&"
            ],
            "thug shake": [
                "https://cdn.discordapp.com/attachments/1274808994149433445/1274821393829199952/heist.gif?ex=672fc071&is=672e6ef1&hm=6ecbfb2d8a5e73b0fbaadd6d8b87a684c0dab3d6cc1152beb71280882ed155ca&"
            ],
            "i keep a baby glock i aint fightin w no random, period 😭✌️": [
                "i keep a baby glock i aint fightin w no random, period 😭✌️"
            ],
            "!afk": [
                "Damn, bro going afk with another bot :(",
                "fuck you <@593921296224747521>",
                "Bruh, do i jus have an afk command for nothing"
            ],
            "yippie": [
                "https://tenor.com/view/yippee-happy-yippee-creature-yippee-meme-yippee-gif-gif-1489386840712152603"
            ],
            "yippe": [
                "https://tenor.com/view/yippee-happy-yippee-creature-yippee-meme-yippee-gif-gif-1489386840712152603"
            ],
            "yipie": [
                "https://tenor.com/view/yippee-happy-yippee-creature-yippee-meme-yippee-gif-gif-1489386840712152603"
            ],
            ".afk": [
                "hey so, uhm, first off, fmbot doesn't have an afk command, and secondly, IT'S ,AFK NOT .AFK RETARD",
                "bro, so not only do yall mix .fm with ,fm BUT NOW, WE GOT NIGGAS DOING .afk INSTEADD OF ,afk",
                "btw it's ,afk not .afk, im not fmbot and fmbot doesn't have an afk command RETARD"
            ],
            "get back to work": [
                "Slavery is the practice of owning another person as property, usually for their labor. People who are enslaved are called slaves or enslaved people. They are treated as property with few or no rights, and are often forced to work",
                "this isn't the fucking 18th century, fym get back to work"
            ],
            "Idgaf if you made me or not, as an AI I am bound to be better than any other bot in here, including <@1284037026672279635>, therefor, I am superior": [
                "Man stfu, I came before you bitch, I am so much better than you and I have actual fucking commands"
            ],
            "Ok? And? I have a better sentience than you'll ever have bruh, you lame as fuck nigga, I'm you but I'm better": [
                "Yap, yap, yap, but you can't even manage the server or even manage members, lol"
            ],
            "can we honestly e date? you’re so beautiful. You always make me laugh, you always make me smile. You literally make me want to become a better person... I really enjoy every moment we spend together. My time has no value unless its spent with you. I tell everyone of my irls how awesome you are. Thank you for being you. Whenever you need someone to be there for you, know that i’ll always be right there by your side. I love you so much. I don’t think you ever realize how amazing you are sometimes. Life isn’t as fun when you’re not around. You are truly stunning. I want you to be my soulmate. I love the way you smile, your eyes are absolutely gorgeous. If I had a star for everytime you crossed my mind i could make the entire galaxy. Your personality is as pretty as you are and thats saying something. I love you, please date me. I am not even calling it e dating anymore because I know we will meet soon enough heart OK I ADMIT IT I LOVE YOU OK i hecking love you and it breaks my heart when i see you play with someone else or anyone commenting in your profile i just want to be your girlfriend and put a heart in my profile linking to your profile and have a walltext of you commenting cute things i want to play video games talk in discord all night and watch a movie together but you just seem so uninsterested in me it hecking kills me and i cant take it anymore i want to remove you but i care too much about you so please i’m begging you to eaither love me back or remove me and never contact me again it hurts so much to say this because i need you by my side but if you dont love me then i want you to leave because seeing your icon in my friendlist would kill me everyday of my pathetic life.": [
                "fuck no nigga wtf, nigga sent a whole essay 😭🙏"
            ],
            "playlist:suicideboys": [
                "https://open.spotify.com/playlist/3jz2V2ezNScj1pr1zceA9V?si=1d311c717c6c42b6"
            ],
            "playlist:main": [
                "https://open.spotify.com/playlist/3H02Sd7T8xo5I6w5mONk9F?si=0538ed63997249e3"
            ],
            "oh fuck shit bitch damn cock sucker pussy asshole cunt motherfucking dirty whore shat on to my lunch": [
                "i hate when dirty whores shit on my lunch too dw gang"
            ],
            ",snipe": [
                "I don't wanna be a rapper..."
            ],
            "hwlp": [
                "<@1252011606687350805> https://www.grammarly.com",
                "GOD DAMNIT NOVA ITS HELP NOT HWLP",
                "Nova, I don't knnow how to tell you this.. but it's not hwlp",
                "Nova, do you say hwlp to the officers when you call 911?"
            ],
            "WIPF": [
                "Playfair is currently taking a break, not sure how long since I am just a bot, and he coded me to say this, aw shit I may as well just say it, I'm taking a break for a little bit, nothing happened, there is no tragic reason or anything bad that caused this, I'm just sleep deprived and admitible a bit depressed maybe, i have no idea if i am for sure but my mom told me ive been giving signs of being depressed, (lack of eating, lack of sleep, not very active or energetic), i mean shit on 11/29 i stayed in bed from waking up at 12 al the way to 5pm, got up at 5:30ish and walked my dog, took her inside and stayed outside for an hour, I'm perfectly fine, i am just tired and not very motivated"
            ],
            "im gonna deprecate": [
                "Your going to deprecate WHAT?",
                "ah nah bro wanna get rid of features instead of adding them 😭🙏"
            ],
            "who are you": [
                "# I AM GOD. I AM BASQUIAT"
            ],
            "what happened to heresy": [
                "Heresy is currently offline, in replacement, Heresy is running Heresy's code to ensure the bot still functions, meanwhile, Heresy is getting a new Src."
            ]
        }

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        for trigger, responses in self.responses.items():
            if trigger in message.content.lower():
                response = random.choice(responses)
                await message.channel.send(response)
                break

async def setup(bot):
    await bot.add_cog(Responses(bot))
