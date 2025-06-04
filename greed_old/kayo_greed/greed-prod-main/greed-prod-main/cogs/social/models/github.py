from lxml import html
from typing import List, Optional
from pydantic import BaseModel, Field
from yarl import URL
from datetime import datetime
from aiohttp import ClientSession

class GitHubProfile(BaseModel):
    username: Optional[str] = Field(None, description="GitHub username")
    avatar_url: Optional[URL] = Field(None, description="GitHub avatar URL")
    followers: Optional[int] = 0
    following: Optional[int] = 0
    stars: Optional[int] = 0
    repositories: Optional[int] = 0
    created_at: Optional[str] = Field(default=None)
    updated_at: Optional[str] = Field(default=None)
    contributions: Optional[int] = 0
    organizations: Optional[List[str]] = []
    pinned_repositories: Optional[List[str]] = []
    top_languages: Optional[List[str]] = []
    top_repositories: Optional[List[str]] = []
    top_contributions: Optional[List[str]] = []
    name: Optional[str] = Field(None, description="GitHub name")
    bio: Optional[str] = Field(None, description="GitHub bio")
    location: Optional[str] = Field(None, description="GitHub location")
    email: Optional[str] = Field(None, description="GitHub email")
    website: Optional[URL] = Field(None, description="GitHub website")
    twitter: Optional[str] = Field(None, description="GitHub twitter")
    facebook: Optional[str] = Field(None, description="GitHub facebook")
    linkedin: Optional[str] = Field(None, description="GitHub linkedin")
    instagram: Optional[str] = Field(None, description="GitHub instagram")
    url: Optional[URL] = Field(None, description="GitHub profile URL")

    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    async def from_username(cls, username: str) -> "GitHubProfile":
        url = URL.build(
            scheme="https",
            host="github.com",
            path=f"/{username}",
        )
        async with ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
        return cls.from_html(text)
    
    @classmethod
    def from_html(cls, html_text: str) -> "GitHubProfile":
        tree = html.fromstring(html_text)
        profile = cls()
        profile.username = tree.xpath('//span[@class="p-nickname vcard-username d-block"]/text()')[0].strip()
        profile.name = tree.xpath('//span[@class="p-name vcard-fullname d-block overflow-hidden"]/text()')[0].strip()
        profile.avatar_url = URL(tree.xpath('//img[@class="avatar avatar-user width-full border color-bg-default"]/@src')[0]) if tree.xpath('//img[@class="avatar avatar-user width-full border color-bg-default"]/@src') else None

        bio_elements = tree.xpath('//div[@class="p-note user-profile-bio mb-3 js-user-profile-bio f4"]/div/text()')
        profile.bio = bio_elements[0] if bio_elements else None

        profile.location = tree.xpath('//span[@class="p-label"]/text()')
        profile.email = tree.xpath('//li[@itemprop="email"]/a[@class="Link--primary"]/text()')
        profile.website = URL(tree.xpath('//li[@itemprop="url"]/a[@class="Link--primary"]/text()')[0]) if tree.xpath('//li[@itemprop="url"]/a[@class="Link--primary"]/text()') else None
        profile.twitter = tree.xpath('//li[@style="max-width: 230px"]/a[@class="Link--primary"]/text()')[0] if tree.xpath('//li[@style="max-width: 230px"]/a[@class="Link--primary"]/text()') else None
        profile.linkedin = tree.xpath('//a[@class="Link--primary" and contains(@href, "linkedin.com")]/text()')[0] if tree.xpath('//a[@class="Link--primary" and contains(@href, "linkedin.com")]/text()') else None
        profile.instagram = tree.xpath('//a[@class="Link--primary" and contains(@href, "instagram.com")]/text()')[0] if tree.xpath('//a[@class="Link--primary" and contains(@href, "instagram.com")]/text()') else None
        profile.followers = int(tree.xpath('//a[@class="Link--secondary no-underline no-wrap"]/span[@class="text-bold color-fg-default"]/text()')[0]) if tree.xpath('//a[@class="Link--secondary no-underline no-wrap"]/span[@class="text-bold color-fg-default"]/text()') else 0
        profile.following = int(tree.xpath('//a[@class="Link--secondary no-underline no-wrap"]/span[@class="text-bold color-fg-default"]/text()')[0]) if tree.xpath('//a[@class="Link--secondary no-underline no-wrap"]/span[@class="text-bold color-fg-default"]/text()') else 0
        profile.stars = int(tree.xpath(f'//a[@data-selected-links="stars /{profile.username}?tab=stars"]/span[@class="Counter"]/text()')[0]) if tree.xpath(f'//a[@data-selected-links="stars /{profile.username}?tab=stars"]/span[@class="Counter"]/text()') else 0
        profile.repositories = int(tree.xpath(f'//a[@data-selected-links="repositories /{profile.username}?tab=repositories"]/span[@class="Counter"]/text()')[0]) if tree.xpath(f'//a[@data-selected-links="repositories /{profile.username}?tab=repositories"]/span[@class="Counter"]/text()') else 0

        
        created_at_xpath_result = tree.xpath('//time[@class="d-inline-block mb-2"]/text()')
        profile.created_at = datetime.strptime(created_at_xpath_result[0], "on %B %d, %Y") if created_at_xpath_result else None
        profile.contributions = int(tree.xpath('//h2[@class="f4 text-normal mb-2"]/text()')[0].strip().split()[0]) if tree.xpath('//h2[@class="f4 text-normal mb-2"]/text()') else 0
        profile.organizations = tree.xpath('//a[@class="orgs-member"]')
        profile.pinned_repositories = tree.xpath('//span[@class="repo js-pinnable-item"]')
        profile.top_languages = tree.xpath('//span[@class="lang"]')
        profile.top_repositories = tree.xpath('//span[@class="repo"]')
        profile.top_contributions = tree.xpath('//span[@class="repo"]')
        profile.username = profile.username.strip() if profile.username else None
        profile.url = URL.build(
            scheme="https",
            host="github.com",
            path=f"/{profile.username}",
        )
        return profile
