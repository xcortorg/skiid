from pydantic import BaseModel, Field
from typing import Optional, Any, List
from aiohttp import ClientSession
from asyncio import run, sleep
from playwright.async_api import async_playwright
from lxml import html
from lxml.html import tostring
import json, re

COOKIES = [
    {
        "name": "jwt-express",
        "value": "eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjk3NjIwLCJlbWFpbCI6ImRha290YXNob21ld29ya0BnbWFpbC5jb20iLCJjcmVhdGVkIjoiYSBmZXcgc2Vjb25kcyBhZ28oMjAyNC0xMS0xNlQyMTowMTo0Ny41MDRaKSIsInN0cmlwZV9pZCI6bnVsbCwiaWF0IjoxNzMxNzkwOTA3LCJleHAiOjE3NjMzNDg1MDd9.AO25bW2wMGJbt6sN7LkK-wLiHHdvfgIAh3WU48fx17GfeZrNGeBd-B0pl-yqKuHKyDiG8nIz8t9qYSVMzLe9YbtcAS9bSZQ-I-FHRL9a4GOhGDR8aUi86mTY9GfIQrAu9r4ojjZXI5Z_7JpvtGw5R-HYe2dhOoUKKuM4E5tjrNPtQesT",
        "domain": "ipinfo.io",
        "path": "/",
        "expires": 1747342907.38095,
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
    },
    {
        "name": "flash",
        "value": "",
        "domain": "ipinfo.io",
        "path": "/",
        "expires": -1,
        "httpOnly": False,
        "secure": False,
    },
]


class IPLookupResponse(BaseModel):
    ip: str
    country_code: str
    country_name: str
    region_name: str
    city_name: str
    latitude: float
    longitude: float
    zip_code: str
    time_zone: str
    asn: str
    asn_name: str
    is_proxy: bool

    @classmethod
    async def from_ip(cls, ip: str):
        async with ClientSession() as session:
            async with session.get(
                "https://api.ip2location.io/",
                params={"key": "0CD62D5D6B70C67099393D4CD4809953", "ip": ip},
            ) as response:
                data = await response.json()
        data["asn_name"] = data.pop("as")
        return cls(**data)


class GeoLocation(BaseModel):
    city: str
    state: str
    country: str
    postal: str
    local_time: str
    timezone: str
    coordinates: str


class ASN(BaseModel):
    number: int
    name: str


class IPScrapeResponse(BaseModel):
    ip: str
    asn: ASN
    hostname: str
    range: str
    company: str
    privacy: bool
    anycast: bool
    asn_type: str
    abuse_contact: str
    geolocation: GeoLocation

    @classmethod
    async def from_ip(cls, ip: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            url = f"https://ipinfo.io/{ip}"
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            data = await page.content()
            await page.close()
            await browser.close()
        await p.stop()

        tree = html.fromstring(data)
        d = {"ip": ip}
        g = {}
        rows = tree.xpath("//tr ")
        for row in rows:
            try:
                key = row.xpath(".//td[1]/span/text()")[
                    0
                ].strip()  # Get the key from the first cell
            except Exception:
                continue
            value = row.xpath(".//td[2]//text()")  # Get all text from the second cell
            value = " ".join(
                [v.strip() for v in value if v.strip()]
            )  # Clean up the value
            d[key.lower().replace(" ", "_")] = value  # Store in the dictionary
        rows = tree.xpath(
            '//*[@id="block-geolocation"]/div/div[1]/div[1]/table/tbody/tr'
        )
        for row in rows:
            key = row.xpath(".//td[1]/text()")[
                0
            ].strip()  # Get the key from the first cell
            value = row.xpath(".//td[2]//text()")  # Get all text from the second cell
            value = " ".join(
                [v.strip() for v in value if v.strip()]
            )  # Clean up the value
            g[key.lower().replace(" ", "_")] = value  # Store in the dictionary
        d["geolocation"] = g
        asn_number, asn_name = d.pop("asn").split(" - ")
        d["asn"] = {
            "number": int("".join(m for m in asn_number if m.isdigit())),
            "asn": asn_name,
        }
        return cls(**d)


class V4Item(BaseModel):
    netblock: Optional[str] = None
    company: Optional[str] = None
    count: Optional[int] = None


class V6Item(BaseModel):
    netblock: Optional[str] = None
    company: Optional[str] = None
    count: Optional[int] = None


class Ranges(BaseModel):
    v4: Optional[List[V4Item]] = None
    v6: Optional[List[V6Item]] = None


class Whois(BaseModel):
    ashandle: Optional[str] = None
    orgid: Optional[str] = None
    asname: Optional[str] = None
    asnumber: Optional[str] = None
    regdate: Optional[str] = None
    comment: Optional[str] = None
    updated: Optional[str] = None
    source: Optional[str] = None
    orgname: Optional[str] = None
    canallocate: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state_prov: Optional[str] = Field(None, alias="state/prov")
    country: Optional[str] = None
    postalcode: Optional[str] = None
    orgadminhandle: Optional[str] = None
    orgtechhandle: Optional[str] = None
    orgabusehandle: Optional[str] = None
    orgnochandle: Optional[str] = None
    pochandle: Optional[str] = None
    isrole: Optional[str] = None
    lastname: Optional[str] = None
    firstname: Optional[str] = None
    officephone: Optional[str] = None
    mailbox: Optional[str] = None


class Domain(BaseModel):
    ip: Optional[str] = None
    domain: Optional[str] = None
    count: Optional[int] = None


class HostedDomains(BaseModel):
    total: Optional[int] = None
    domains: Optional[List[Domain]] = None


class Peer(BaseModel):
    asn: Optional[str] = None
    name: Optional[str] = None


class Upstream(BaseModel):
    asn: Optional[str] = None
    name: Optional[str] = None


class ASNScrapeResponse(BaseModel):
    asn: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    number_of_ipv4: Optional[str] = None
    number_of_ipv6: Optional[float] = None
    asn_type: Optional[str] = None
    registry: Optional[str] = None
    allocated: Optional[str] = None
    updated: Optional[str] = None
    ranges: Optional[Ranges] = None
    whois: Optional[Whois] = None
    hosted_domains: Optional[HostedDomains] = None
    peers: Optional[List[Peer]] = None
    upstreams: Optional[List[Upstream]] = None

    @classmethod
    async def from_asn(cls, asn: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            await context.add_cookies(COOKIES)
            page = await context.new_page()
            url = f"https://ipinfo.io/{asn}"
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            data = await page.content()
            await page.close()
            await browser.close()
        await p.stop()
        tree = html.fromstring(data)
        d = {"asn": asn}
        rows = tree.xpath("//tr ")
        for row in rows:
            try:
                key = row.xpath(".//td[1]/span/text()")[
                    0
                ].strip()  # Get the key from the first cell
            except Exception:
                continue
            value = row.xpath(".//td[2]//text()")  # Get all text from the second cell
            value = " ".join(
                [v.strip() for v in value if v.strip()]
            )  # Clean up the value
            d[key.lower().replace(" ", "_")] = value  # Store in the dictionary

        def extract_ip_ranges(table_id):

            def calculate_ip_addresses(cidr):
                # Extract the prefix length from the CIDR notation
                prefix_length = int(cidr.split("/")[1])

                # For IPv6, the total number of addresses is 2^(128 - prefix_length)
                if prefix_length <= 128:
                    num_ips = 2 ** (128 - prefix_length)
                    return num_ips
                else:
                    raise ValueError("Invalid CIDR prefix length for IPv6.")

            data = []
            rows = tree.xpath(f'//div[@id="{table_id}"]/table/tbody/tr')
            for row in rows:
                netblock = row.xpath(".//td[1]/a/text()")[0].strip()  # Get the netblock
                try:
                    company = row.xpath(".//td[2]/span/text()")[
                        0
                    ].strip()  # Get the company
                except Exception:
                    company = "N/A"
                if table_id == "ipv4-data":
                    num_ips = row.xpath(".//td[3]/text()")[
                        0
                    ].strip()  # Get the number of IPs for IPv4
                    data.append(
                        {
                            "netblock": netblock,
                            "company": company,
                            "count": int(num_ips),
                        }
                    )
                else:
                    if not "::" in netblock:
                        continue
                    if "/" in netblock:
                        num_ips = calculate_ip_addresses(netblock)
                    else:
                        num_ips = None
                    data.append(
                        {"netblock": netblock, "company": company, "count": num_ips}
                    )  # For IPv6, only netblock and company
            return data

        def extract_domains():
            rows = tree.xpath('//*[@id="block-domains"]//table/tbody/tr')

            # Initialize a list to hold the extracted data
            extracted_data = []

            # Loop through each row and extract the relevant information
            for row in rows:
                ip_address = row.xpath("./td[1]/a/text()")[0].strip()
                try:
                    domain = row.xpath("./td[2]/a/text()")[0].strip()
                except Exception:
                    # //*[@id="ipv6-data"]/table/tbody/tr[1]/td[2]/a
                    domain = "N/A"
                domains_on_ip = row.xpath("./td[3]/text()")[0].strip()

                extracted_data.append(
                    {"ip": ip_address, "domain": domain, "count": int(domains_on_ip)}
                )
            return extracted_data

        def extract_peers():
            rows = tree.xpath('//*[@id="block-peers"]/div/div[1]/table/tbody/tr')

            # Initialize a list to hold the extracted data
            extracted_peers = []

            # Loop through each row and extract the relevant information
            for row in rows:
                peer_asn = row.xpath("./td[1]/a/text()")[0].strip()  # Extract ASN
                peer_name = row.xpath("./td[2]/text()")[0].strip()  # Extract Name
                extracted_peers.append({"asn": peer_asn, "name": peer_name})
            return extracted_peers

        def extract_upstreams():
            rows = tree.xpath('//*[@id="block-upstreams"]//table/tbody/tr')

            # Initialize a list to hold the extracted data
            extracted_upstreams = []

            # Loop through each row and extract the relevant information
            for row in rows:
                upstream_asn = row.xpath("./td[1]/a/text()")[0].strip()  # Extract ASN
                upstream_name = row.xpath("./td[2]/text()")[0].strip()  # Extract Name

                extracted_upstreams.append({"asn": upstream_asn, "name": upstream_name})
            return extracted_upstreams

        d["ranges"] = {
            "v4": extract_ip_ranges("ipv4-data"),
            "v6": extract_ip_ranges("ipv6-data"),
        }
        try:
            who_is = tree.xpath(
                '//*[@id="block-whois"]/div/div[1]/div/div[2]/pre/text()'
            )[0]
            d["whois"] = {}
            for line in who_is.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    d["whois"][key.strip().lower()] = value.strip()
        except Exception:
            pass

        d["hosted_domains"] = {
            "total": int(d.pop("hosted_domains", 0)),
            "domains": extract_domains(),
        }
        d["peers"] = extract_peers()
        d["number_of_ipv6"] = eval(
            d["number_of_ipv6"].replace("\u00d7", "*").replace(" ", "")
        )
        d["upstreams"] = extract_upstreams()
        return cls(**d)
