from redis.asyncio import Redis
from .Base import BaseService, cache
from typing import Optional
from ..models.IP import ASNScrapeResponse, IPLookupResponse, IPScrapeResponse


class IPService(BaseService):
    def __init__(self: "IPService", redis: Redis, ttl: Optional[int] = None):
        super().__init__(redis, ttl)

    @cache()
    async def scrape(self: "IPService", ip: str) -> IPScrapeResponse:
        """Scrape IP information from various sources."""
        return await IPScrapeResponse.from_ip(ip)

    @cache()
    async def lookup(self: "IPService", ip: str) -> IPLookupResponse:
        """Lookup IP information from various sources."""
        return await IPLookupResponse.from_ip(ip)

    @cache()
    async def asn(self: "IPService", asn: str) -> ASNScrapeResponse:
        if not asn.startswith("ASN"):
            asn = f"ASN:{asn}"
        return await ASNScrapeResponse.from_asn(asn)
