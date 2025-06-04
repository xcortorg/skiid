<center><a href="https://greed.best/discord" target="_blank"><img src="https://r2.greed.best/Greed%20Discovery%20Cover.png" alt="Greed Discovery Cover"/></a</center>

# 👋 The official repostiry for the greed discord bot 
IMPORTANT! This is a closed source discord bot, having access to this means that you are probably a developer or owner of greed, note that this is a responsibility which can result in consequences if not treated properly.

## ⚙️ Getting Started

### Requirements

[`Python Version: 3.10`](https://www.python.org/downloads/release/python-3100/): Runs the bot that is developed in Python.<br />
[`Ubuntu: 22.04 LTS (Jammy Jellyfish)`](https://releases.ubuntu.com/jammy/): Operating System where the bot is hosted.<br />
[`Cloudflared`](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/): Tunnels and hides the IP from the public to avoid [DDoS](https://www.cloudflare.com/learning/ddos/what-is-a-ddos-attack/) attacks as much as possible.<br />
[`Redis 7.4.2 (Self Managed)`](https://redis.io/downloads/): Memory data structure store used as a Database, cache & message broker.<br />
[`Postgres SQL Linux`](https://www.postgresql.org/download/): The open source database that greed uses to store necessary data.

### Running the bot 

- greed uses [`screen`](https://linuxize.com/post/how-to-use-linux-screen/) to run the bot, for further information visit any development website that has decent documentations for [`screen`](https://linuxize.com/post/how-to-use-linux-screen/)
- You must install all requirements from the requirements.txt, however some may be missing! Debug if necessary 
- You can use the `install.sh` file, however, further installation will be needed (if you are not experienced with setting up bots and their services that were listed under requirements, do not bother and dont waste your time.)

## 📓 Contributing 

- Use conventional commits for your commits to be understood better by other developers. [`reference`](https://www.conventionalcommits.org/)
- Format your code before pushing it, ensure its working on a development bot before publishing to production.
- If its a major update, check with your line manager before pushing it. (Do not present if there are multiple bugs, once its semi-functional inform so that further testing could take place before pushing onto production.)

