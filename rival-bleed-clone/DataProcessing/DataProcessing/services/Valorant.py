from .Base import BaseService, cache, Redis, Optional
from playwright.async_api import async_playwright
from asyncio import sleep
from lxml import html


class Valorant(BaseService):
    def __init__(self, redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__(redis, ttl)

    def try_extract(self, tree, path):
        try:
            return tree.xpath(path)[0]
        except:
            return None

    async def get_profile(self, username: str) -> Optional[ValorantProfile]:
        username = username.replace("#", "%23")
        url = f"https://tracker.gg/valorant/profile/riot/{username}/overview"
        d = {}
        async with PageManager(self.controller) as page:
            await page.page.goto(url, wait_until="domcontentloaded")
            try:
                await page.page.solve_recaptcha()
            except:
                pass
            await sleep(2)
            data = await page.page.content()
        tree = html.fromstring(data)

        async def fetch_profile(tree) -> None:
            if tree.xpath(
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[1]/div[2]/div[2]/div[2]/div[1]/div/svg[2]/path'
            ):
                d["claimed"] = True
            d["region"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[1]/div[2]/div[1]/img[1]/@title',
            )
            d["peak"] = (
                self.try_extract(
                    tree,
                    '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[1]/div[1]/div[2]/div/div/div/div/div[2]/div[1]/text()',
                ).strip()
                or None
            )
            d["avatar_url"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[1]/div[2]/div[1]/img[2]/@src',
            )
            try:
                d["views"] = self.try_extract(
                    tree,
                    '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[1]/div[2]/div[2]/div[1]/span/div[1]/span/text()',
                )
                d["views"] = int(d["views"].split(" ", 1)[0])
            except:
                d["views"] = 0
            d["rank"] = (
                self.try_extract(
                    tree,
                    '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[1]/span[2]/text()',
                )
                or "unranked"
            )
            d["level"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[2]/span[2]/text()',
            )
            d["win-loss"] = {
                "win": convert_value(
                    self.try_extract(
                        tree,
                        '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[3]/svg/g[2]/text[1]/text()',
                    )
                    or "0"
                ),
                "loss": convert_value(
                    self.try_extract(
                        tree,
                        '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[2]/div[2]/div/div[1]/div/div[3]/svg/g[2]/text[2]/text()',
                    )
                    or "0"
                ),
            }
            d["kd"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[3]/div[2]/div/div[2]/span[2]/span/text()',
            )
            d["dpr"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[3]/div[1]/div/div[2]/span[2]/span/text()',
            )
            d["headshot-ratio"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[3]/div[3]/div/div[2]/span[2]/span/text()',
            )
            d["wlr"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[3]/div[4]/div/div[2]/span[2]/span/text()',
            )
            d["kast"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[2]/div/div[2]/span[2]/span/text()',
            )
            d["ddr"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[3]/div/div[2]/span[2]/span/text()',
            )
            d["kills"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[4]/div/div[2]/span[2]/span/text()',
            )
            d["deaths"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[5]/div/div[1]/span[2]/span/text()',
            )
            d["assists"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[6]/div/div[1]/span[2]/span/text()',
            )
            d["acs"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[7]/div/div[2]/span[2]/span/text()',
            )
            d["kadr"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[8]/div/div[1]/span[2]/span/text()',
            )
            d["krr"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[9]/div/div[1]/span[2]/span/text()',
            )
            d["first-bloods"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[10]/div/div[1]/span[2]/span/text()',
            )
            d["flawless-rounds"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[11]/div/div[1]/span[2]/span/text()',
            )
            d["aces"] = self.try_extract(
                tree,
                '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[1]/div[5]/div[12]/div/div[1]/span[2]/span/text()',
            )
            d["rwp"] = (
                self.try_extract(
                    tree,
                    '//*[@id="app"]/div[2]/div[3]/div/main/div[3]/div[2]/div[2]/div[2]/div[1]/div[2]/div[2]/div[2]/div[1]/div[2]/text()',
                )
                or "N/A"
            )
            user, tag = username.split("%23", 1)
            d["user"] = user
            d["tag"] = tag
            IGNORED_KEYS = ("user", "tag", "win-loss")
            for key, value in d.items():
                if key in IGNORED_KEYS:
                    continue
                if isinstance(value, str):
                    try:
                        d[key] = convert_value(d[key])
                    except:
                        pass
            return None

        async def get_agents(tree) -> None:
            d["agents"] = await extract_agent_data(tree)
            return None

        async def get_accuracy(tree) -> None:
            d["accuracy"] = await extract_accuracy_data(tree)
            return None

        async def get_roles(tree) -> None:
            d["roles"] = await extract_role_data(tree)
            return None

        async def get_maps(tree) -> None:
            d["maps"] = await extract_map_data(tree)
            return None

        async def get_weapons(tree) -> None:
            d["weapons"] = await extract_weapon_data(tree)
            return None

        async def get_matches(tree) -> None:
            try:
                d["matches"] = await extract_match_data(tree)
            except Exception as error:
                exc = "".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
                print(exc)
            return None

        await gather(
            *[
                fetch_profile(tree),
                get_accuracy(tree),
                get_roles(tree),
                get_maps(tree),
                get_weapons(tree),
                get_matches(tree),
                get_agents(tree),
            ]
        )

        # with open("data.json", "wb") as file:
        #     file.write(orjson.dumps(d))
        return ValorantProfile(**d)
