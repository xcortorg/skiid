# SETUP INSTRUCTIONS

get a /64 from your hosting provider aswell as setup a Hurricane Electric IPV6 Tunnel

the tunnel will be used to be a CIDR
whilest the /64 will be used to actually proxy

edit /etc/docker/daemon.json
add "ipv6": true,
add "fixed-cidr-v6": "tunnel-addr"

# STARTUP COMMANDS

`cd proxy-server`
`docker build -t ipv6_proxy .`
`docker run --privileged -d --name ipv6-proxy --network host --restart always --memory=2g ipv6_proxy`

if all goes well then you should be able to use something like the code below

```
import asyncio
import random
from aiohttp import ClientSession

async def get_3proxy_ports():
    process = await asyncio.create_subprocess_exec(
        'netstat', '-tlnp',
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if stderr:
        print(f"Error: {stderr.decode().strip()}")
        return []

    ports = []
    for line in stdout.decode().splitlines():
        if '3proxy' in line:
            parts = line.split()
            if len(parts) > 3:
                port_info = parts[3]
                port = port_info.split(':')[-1]  # Get the port number
                ports.append(port)

    return ports

async def get_random_proxy():
    ports = await get_3proxy_ports()
    port = random.choice(ports)
    return f"http://0.0.0.0:{port}"

async def test():
    proxy = await get_random_proxy()
    async with ClientSession() as session:
        async with session.get('http://v6.ipinfo.io/json', proxy=proxy) as response:
            print(await response.json())

if __name__ == "__main__":
    asyncio.run(test())
```

If it didnt work then u didnt do something correctly :shrug:
