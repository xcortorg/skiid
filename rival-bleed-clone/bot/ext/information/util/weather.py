from playwright.async_api import async_playwright, Response
from pydantic import BaseModel, create_model
from typing import Union, Optional, List, Any
from json import loads, dumps
from lxml import html
import asyncio


class Coord(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None


class Main(BaseModel):
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    pressure: Optional[int] = None
    humidity: Optional[int] = None
    sea_level: Optional[int] = None
    grnd_level: Optional[int] = None


class Wind(BaseModel):
    speed: Optional[float] = None
    deg: Optional[int] = None


class Sys(BaseModel):
    country: Optional[str] = None


class Clouds(BaseModel):
    all: Optional[int] = None


class WeatherItem(BaseModel):
    id: Optional[int] = None
    main: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class ListItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    coord: Optional[Coord] = None
    main: Optional[Main] = None
    dt: Optional[int] = None
    wind: Optional[Wind] = None
    sys: Optional[Sys] = None
    rain: Optional[Any] = None
    snow: Optional[Any] = None
    clouds: Optional[Clouds] = None
    weather: Optional[List[WeatherItem]] = None


class Coordd(BaseModel):
    lon: Optional[float] = None
    lat: Optional[float] = None


class WeatherItemm(BaseModel):
    id: Optional[int] = None
    main: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class Mainn(BaseModel):
    temp: Optional[float] = None
    feels_like: Optional[float] = None
    temp_min: Optional[int] = None
    temp_max: Optional[float] = None
    pressure: Optional[int] = None
    humidity: Optional[int] = None
    sea_level: Optional[int] = None
    grnd_level: Optional[int] = None


class Windd(BaseModel):
    speed: Optional[float] = None
    deg: Optional[int] = None
    gust: Optional[float] = None


class Cloudss(BaseModel):
    all: Optional[int] = None


class Syss(BaseModel):
    type: Optional[int] = None
    id: Optional[int] = None
    country: Optional[str] = None
    sunrise: Optional[int] = None
    sunset: Optional[int] = None


class Data(BaseModel):
    coord: Optional[Coordd] = None
    weather: Optional[List[WeatherItemm]] = None
    base: Optional[str] = None
    main: Optional[Mainn] = None
    visibility: Optional[int] = None
    wind: Optional[Windd] = None
    clouds: Optional[Cloudss] = None
    dt: Optional[int] = None
    sys: Optional[Syss] = None
    timezone: Optional[int] = None
    id: Optional[int] = None
    name: Optional[str] = None
    cod: Optional[int] = None


class WeatherResponse(BaseModel):
    message: Optional[str] = None
    cod: Optional[str] = None
    count: Optional[int] = None
    list: Optional[List[ListItem]] = None
    data: Optional[Data] = None

    @classmethod
    async def from_city(cls, city: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            await page.goto(
                "https://openweathermap.org/", wait_until="domcontentloaded"
            )
            locator = page.get_by_placeholder("Search city", exact=True)
            async with page.expect_response(
                lambda r: "https://api.openweathermap.org/data/2.5/find" in str(r.url)
            ) as response:
                await locator.fill(city)
                button = page.get_by_text("Search", exact=True)
                await button.click()
                await page.wait_for_selector("ul.search-dropdown-menu")
                # Click the first element in the dropdown
                first_element_selector = "ul.search-dropdown-menu li:first-child"
                await page.click(first_element_selector)
            response = await response.value
            params = str(response.url).split("&", 1)[1]

            headers = await response.all_headers()
            data = await response.json()
            url = f"https://api.openweathermap.org/data/2.5/weather?id={data['list'][0]['id']}&{params}"
            await page.goto(url, wait_until="domcontentloaded")
            data2 = await page.content()
            tree = html.fromstring(data2)
            data2 = loads(tree.xpath("/html/body/pre/text()")[0])
            data = await response.json()
            await page.close()
            await context.close()
            await browser.close()
        await p.stop()
        _ = cls(**data)
        _.data = Data(**data2)
        return _
