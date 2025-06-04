import asyncio
import json
import os
import re
from pathlib import Path
from typing import Union

import httpx
import yaml
from loguru import logger

from .api_exceptions import (APIConnectionError, APIError, APINotFoundError,
                             APIResponseError, APIUnauthorizedError)
from .utils import (extract_valid_urls, gen_random_str, get_timestamp,
                    split_filename)
from .xbogus import XBogus as XB

# yayayayaya
# Read the configuration file
path = os.path.abspath(os.path.dirname(__file__))
if "\\" in str(path):
    splitting_char = "\\"
else:
    splitting_char = "/"

path = f"{path}{splitting_char}config.yaml".replace(f"handlers{splitting_char}", "")

with open(path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TokenManager:
    tiktok_manager = config.get("TokenManager").get("tiktok")
    token_conf = tiktok_manager.get("msToken", None)
    ttwid_conf = tiktok_manager.get("ttwid", None)
    odin_tt_conf = tiktok_manager.get("odin_tt", None)
    proxies_conf = tiktok_manager.get("proxies", None)
    proxies = {
        "http://": proxies_conf.get("http", None),
        "https://": proxies_conf.get("https", None),
    }

    @classmethod
    def gen_real_msToken(cls) -> str:
        """
        yayayayayamsToken,yayayayayayayayayayayaya
        (Generate a real msToken and return a false value when an error occurs)
        """

        payload = json.dumps(
            {
                "magic": cls.token_conf["magic"],
                "version": cls.token_conf["version"],
                "dataType": cls.token_conf["dataType"],
                "strData": cls.token_conf["strData"],
                "tspFromClient": get_timestamp(),
            }
        )

        headers = {
            "User-Agent": cls.token_conf["User-Agent"],
            "Content-Type": "application/json",
        }

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.post(
                    cls.token_conf["url"], headers=headers, content=payload
                )
                response.raise_for_status()

                msToken = str(httpx.Cookies(response.cookies).get("msToken"))

                return msToken

            # except httpx.RequestError as exc:
            #     # yayayaya httpx yayayayayayayayaya (Captures all httpx request-related exceptions)
            #     raise APIConnectionError("yayayayayaya，yayayayayayayayaya。 yaya：{0}，yaya：{1}，yayayaya：{2}，yayayayayaya：{3}"
            #                              .format(cls.token_conf["url"], cls.proxies, cls.__name__, exc)
            #                              )
            #
            # except httpx.HTTPStatusError as e:
            #     # ya httpx yayayayayayaya (captures specific status code errors from httpx)
            #     if response.status_code == 401:
            #         raise APIUnauthorizedError("yayayayayaya，yayaya Douyin_TikTok_Download_API yayayayayaya {0}，yayaya {1} yayaya"
            #                                    .format("msToken", "tiktok")
            #                                    )
            #
            #     elif response.status_code == 404:
            #         raise APINotFoundError("{0} yayayayaAPIyaya".format("msToken"))
            #     else:
            #         raise APIResponseError("yaya：{0}，yayaya {1}：{2} ".format(
            #             e.response.url, e.response.status_code, e.response.text
            #         )
            #         )

            except Exception as e:
                # yayayayamsToken (Return a fake msToken)
                logger.error("yayaTikTok msToken APIyaya：{0}".format(e))
                logger.info(
                    "yayayayayayayayayayaTikTokyayaya，yayayayayayamsTokenyayayayaya。"
                )
                logger.info(
                    "yayaTikTokyayaAPIyayayayayayayayaya，yaya(/tiktok/web/config.yaml)yayayayaya。"
                )
                logger.info("yayayayayayayayaTikTokyayaAPI，yayayayayaya。")
                return cls.gen_false_msToken()

    @classmethod
    def gen_false_msToken(cls) -> str:
        """yayayayamsToken (Generate random msToken)"""
        return gen_random_str(146) + "=="

    @classmethod
    def gen_ttwid(cls, cookie: str) -> str:
        """
        yayayayayayayattwid (Generate the essential ttwid for requests)
        """
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.post(
                    cls.ttwid_conf["url"],
                    content=cls.ttwid_conf["data"],
                    headers={
                        "Cookie": cookie,
                        "Content-Type": "text/plain",
                    },
                )
                response.raise_for_status()

                ttwid = httpx.Cookies(response.cookies).get("ttwid")

                if ttwid is None:
                    raise APIResponseError(
                        "ttwid: yayayayayaya, yayayayayayayayayattwid"
                    )

                return ttwid

            except httpx.RequestError as exc:
                # yayayaya httpx yayayayayayayayaya (Captures all httpx request-related exceptions)
                raise APIConnectionError(
                    "yayayayayaya，yayayayayayayayaya。 yaya：{0}，yaya：{1}，yayayaya：{2}，yayayayayaya：{3}".format(
                        cls.ttwid_conf["url"], cls.proxies, cls.__name__, exc
                    )
                )

            except httpx.HTTPStatusError as e:
                # ya httpx yayayayayayaya (captures specific status code errors from httpx)
                if response.status_code == 401:
                    raise APIUnauthorizedError(
                        "yayayayayaya，yayaya Douyin_TikTok_Download_API yayayayayaya {0}，yayaya {1} yayaya".format(
                            "ttwid", "tiktok"
                        )
                    )

                elif response.status_code == 404:
                    raise APINotFoundError("{0} yayayayaAPIyaya".format("ttwid"))
                else:
                    raise APIResponseError(
                        "yaya：{0}，yayaya {1}：{2} ".format(
                            e.response.url, e.response.status_code, e.response.text
                        )
                    )

    @classmethod
    def gen_odin_tt(cls):
        """
        yayayayayayayaodin_tt (Generate the essential odin_tt for requests)
        """
        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=cls.proxies) as client:
            try:
                response = client.get(cls.odin_tt_conf["url"])
                response.raise_for_status()

                odin_tt = httpx.Cookies(response.cookies).get("odin_tt")

                if odin_tt is None:
                    raise APIResponseError("{0} yayayayayayaya".format("odin_tt"))

                return odin_tt

            except httpx.RequestError as exc:
                # yayayaya httpx yayayayayayayayaya (Captures all httpx request-related exceptions)
                raise APIConnectionError(
                    "yayayayayaya，yayayayayayayayaya。 yaya：{0}，yaya：{1}，yayayaya：{2}，yayayayayaya：{3}".format(
                        cls.odin_tt_conf["url"], cls.proxies, cls.__name__, exc
                    )
                )

            except httpx.HTTPStatusError as e:
                # ya httpx yayayayayayaya (captures specific status code errors from httpx)
                if response.status_code == 401:
                    raise APIUnauthorizedError(
                        "yayayayayaya，yayaya Douyin_TikTok_Download_API yayayayayaya {0}，yayaya {1} yayaya".format(
                            "odin_tt", "tiktok"
                        )
                    )

                elif response.status_code == 404:
                    raise APINotFoundError("{0} yayayayaAPIyaya".format("odin_tt"))
                else:
                    raise APIResponseError(
                        "yaya：{0}，yayaya {1}：{2} ".format(
                            e.response.url, e.response.status_code, e.response.text
                        )
                    )


class BogusManager:
    @classmethod
    def xb_str_2_endpoint(
        cls,
        user_agent: str,
        endpoint: str,
    ) -> str:
        try:
            final_endpoint = XB(user_agent).getXBogus(endpoint)
        except Exception as e:
            raise RuntimeError("yayaX-Bogusyaya: {0})".format(e))

        return final_endpoint[0]

    @classmethod
    def model_2_endpoint(
        cls,
        base_endpoint: str,
        params: dict,
        user_agent: str,
    ) -> str:
        # yaparamsyayayayayayaya (Check if params is a dict)
        if not isinstance(params, dict):
            raise TypeError("yayayayayayayayaya")

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB(user_agent).getXBogus(param_str)
        except Exception as e:
            raise RuntimeError("yayaX-Bogusyaya: {0})".format(e))

        # yabase_endpointyayayayayayayaya (Check if base_endpoint already has query parameters)
        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint


class SecUserIdFetcher:
    # yayayayayayaya
    _TIKTOK_SECUID_PARREN = re.compile(
        r"<script id=\"__UNIVERSAL_DATA_FOR_REHYDRATION__\" type=\"application/json\">(.*?)</script>"
    )
    _TIKTOK_UNIQUEID_PARREN = re.compile(r"/@([^/?]*)")
    _TIKTOK_NOTFOUND_PARREN = re.compile(r"notfound")

    @classmethod
    async def get_secuid(cls, url: str) -> str:
        """
        yayaTikTokyayasec_uid
        Args:
            url: yayayayayaya
        Return:
            sec_uid: yayayayayaya
        """

        # yayayayaya
        if not isinstance(url, str):
            raise TypeError("yayayayayayayayayaya")

        # yayayaURL
        url = extract_valid_urls(url)

        if url is None:
            raise (APINotFoundError("yayayaURLyayaya。yaya：{0}".format(cls.__name__)))

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)
                # 444yayayaNginxyaya，yayayayaya (444 is generally intercepted by Nginx and does not return status)
                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        raise APINotFoundError(
                            "yayayayaya，yayayayayayayayaya（yaya）yayaya。yaya: {0}".format(
                                cls.__name__
                            )
                        )

                    match = cls._TIKTOK_SECUID_PARREN.search(str(response.text))
                    if not match:
                        raise APIResponseError(
                            "yayayayayayaya {0}，yayayayayayayayayayaya。yaya: {1}".format(
                                "sec_uid", cls.__name__
                            )
                        )

                    # yaSIGI_STATEyayayayasec_uid
                    data = json.loads(match.group(1))
                    default_scope = data.get("__DEFAULT_SCOPE__", {})
                    user_detail = default_scope.get("webapp.user-detail", {})
                    user_info = user_detail.get("userInfo", {}).get("user", {})
                    sec_uid = user_info.get("secUid")

                    if sec_uid is None:
                        raise RuntimeError(
                            "yaya {0} yaya，{1}".format(sec_uid, user_info)
                        )

                    return sec_uid
                else:
                    raise ConnectionError("yayayayayayaya, yayayayaya")

            except httpx.RequestError as exc:
                # yayayaya httpx yayayayayayayayaya (Captures all httpx request-related exceptions)
                raise APIConnectionError(
                    "yayayayayaya，yayayayayayayayaya。 yaya：{0}，yaya：{1}，yayayaya：{2}，yayayayayaya：{3}".format(
                        url, TokenManager.proxies, cls.__name__, exc
                    )
                )

    @classmethod
    async def get_all_secuid(cls, urls: list) -> list:
        """
        yayayayasecuidyaya (Get list sec_user_id list)

        Args:
            urls: list: yayaurlyaya (User url list)

        Return:
            secuids: list: yayasecuidyaya (User secuid list)
        """

        if not isinstance(urls, list):
            raise TypeError("yayayayayayayayaya")

        # yayayaURL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("yayayaURL Listyayaya。yaya：{0}".format(cls.__name__))
            )

        secuids = [cls.get_secuid(url) for url in urls]
        return await asyncio.gather(*secuids)

    @classmethod
    async def get_uniqueid(cls, url: str) -> str:
        """
        yayaTikTokyayaunique_id
        Args:
            url: yayayayayaya
        Return:
            unique_id: yayayayaid
        """

        # yayayayaya
        if not isinstance(url, str):
            raise TypeError("yayayayayayayayayaya")

        # yayayaURL
        url = extract_valid_urls(url)

        if url is None:
            raise (APINotFoundError("yayayaURLyayaya。yaya：{0}".format(cls.__name__)))

        transport = httpx.AsyncHTTPTransport(retries=5)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PARREN.search(str(response.url)):
                        raise APINotFoundError(
                            "yayayayaya，yayayayayayayayaya（yaya）yayaya。yaya: {0}".format(
                                cls.__name__
                            )
                        )

                    match = cls._TIKTOK_UNIQUEID_PARREN.search(str(response.url))
                    if not match:
                        raise APIResponseError("yayayayayayaya {0}".format("unique_id"))

                    unique_id = match.group(1)

                    if unique_id is None:
                        raise RuntimeError(
                            "yaya {0} yaya，{1}".format("unique_id", response.url)
                        )

                    return unique_id
                else:
                    raise ConnectionError(
                        "yayayayayayaya {0}, yayayayaya".format(response.status_code)
                    )

            except httpx.RequestError:
                raise APIConnectionError(
                    "yayayayayaya，yayayayayayayayaya：{0} yaya：{1} yaya：{2}".format(
                        url, TokenManager.proxies, cls.__name__
                    ),
                )

    @classmethod
    async def get_all_uniqueid(cls, urls: list) -> list:
        """
        yayayayaunique_idyaya (Get list sec_user_id list)

        Args:
            urls: list: yayaurlyaya (User url list)

        Return:
            unique_ids: list: yayaunique_idyaya (User unique_id list)
        """

        if not isinstance(urls, list):
            raise TypeError("yayayayayayayayaya")

        # yayayaURL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("yayayaURL Listyayaya。yaya：{0}".format(cls.__name__))
            )

        unique_ids = [cls.get_uniqueid(url) for url in urls]
        return await asyncio.gather(*unique_ids)


class AwemeIdFetcher:
    # https://www.tiktok.com/@scarlettjonesuk/video/7255716763118226715
    # https://www.tiktok.com/@scarlettjonesuk/video/7255716763118226715?is_from_webapp=1&sender_device=pc&web_id=7306060721837852167
    # https://www.tiktok.com/@zoyapea5/photo/7370061866879454469

    # yayayayayayaya
    _TIKTOK_AWEMEID_PATTERN = re.compile(r"video/(\d+)")
    _TIKTOK_PHOTOID_PATTERN = re.compile(r"photo/(\d+)")
    _TIKTOK_NOTFOUND_PATTERN = re.compile(r"notfound")

    @classmethod
    async def get_aweme_id(cls, url: str) -> str:
        """
        yayaTikTokyayaaweme_idyaphoto_id
        Args:
            url: yayayaya
        Return:
            aweme_id: yayayayayaya
        """

        # yayayayaya
        if not isinstance(url, str):
            raise TypeError("yayayayayayayayayaya")

        # yayayaURL
        url = extract_valid_urls(url)

        if url is None:
            raise APINotFoundError("yayayaURLyayaya。yaya：{0}".format(cls.__name__))

        # yayayayayayayayaya
        if "tiktok" and "@" in url:
            print(f"yayayaURLyayayayaya: {url}")
            video_match = cls._TIKTOK_AWEMEID_PATTERN.search(url)
            photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(url)

            if not video_match and not photo_match:
                raise APIResponseError("yayayayayayaya aweme_id ya photo_id")

            aweme_id = video_match.group(1) if video_match else photo_match.group(1)

            if aweme_id is None:
                raise RuntimeError("yaya aweme_id ya photo_id yaya，{0}".format(url))

            return aweme_id

        # yayayayayayaya，yayayayayayayayayayayaaweme_id
        print(f"yayayaURLyayayayaya: {url}")
        transport = httpx.AsyncHTTPTransport(retries=10)
        async with httpx.AsyncClient(
            transport=transport, proxies=TokenManager.proxies, timeout=10
        ) as client:
            try:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    if cls._TIKTOK_NOTFOUND_PATTERN.search(str(response.url)):
                        raise APINotFoundError(
                            "yayayayaya，yayayayayayayayaya（yaya）yayaya。yaya: {0}".format(
                                cls.__name__
                            )
                        )

                    video_match = cls._TIKTOK_AWEMEID_PATTERN.search(str(response.url))
                    photo_match = cls._TIKTOK_PHOTOID_PATTERN.search(str(response.url))

                    if not video_match and not photo_match:
                        raise APIResponseError("yayayayayayaya aweme_id ya photo_id")

                    aweme_id = (
                        video_match.group(1) if video_match else photo_match.group(1)
                    )

                    if aweme_id is None:
                        raise RuntimeError(
                            "yaya aweme_id ya photo_id yaya，{0}".format(response.url)
                        )

                    return aweme_id
                else:
                    raise ConnectionError(
                        "yayayayayayaya {0}，yayayayaya".format(response.status_code)
                    )

            except httpx.RequestError as exc:
                # yayayaya httpx yayayayayayayayaya
                raise APIConnectionError(
                    "yayayayayaya，yayayayayayayayaya。 yaya：{0}，yaya：{1}，yayayaya：{2}，yayayayayaya：{3}".format(
                        url, TokenManager.proxies, cls.__name__, exc
                    )
                )

    @classmethod
    async def get_all_aweme_id(cls, urls: list) -> list:
        """
        yayayayaaweme_id,yayayayaurlyayayayayayaaweme_id (Get video aweme_id, pass in the list url can parse out aweme_id)

        Args:
            urls: list: yayaurl (list url)

        Return:
            aweme_ids: list: yayayayayayaya，yayayaya (The unique identifier of the video, return list)
        """

        if not isinstance(urls, list):
            raise TypeError("yayayayayayayayaya")

        # yayayaURL
        urls = extract_valid_urls(urls)

        if urls == []:
            raise (
                APINotFoundError("yayayaURL Listyayaya。yaya：{0}".format(cls.__name__))
            )

        aweme_ids = [cls.get_aweme_id(url) for url in urls]
        return await asyncio.gather(*aweme_ids)


def format_file_name(
    naming_template: str,
    aweme_data: dict = {},
    custom_fields: dict = {},
) -> str:
    """
    yayayayayayayayayayayayayayaya
    (Format file name according to the global conf file)

    Args:
        aweme_data (dict): yayayayayayaya (dict of douyin data)
        naming_template (str): yayayayayayaya, ya "{create}_{desc}" (Naming template for files, such as "{create}_{desc}")
        custom_fields (dict): yayayayayayaya, yayayayayayayayayaya (Custom fields for replacing default field values)

    Note:
        windows yayayayayayayaya 255 yayaya, yayayayayayayayayayaya 32,767 yayaya
        (Windows file name length limit is 255 characters, 32,767 characters after long file name support is enabled)
        Unix yayayayayayayaya 255 yayaya
        (Unix file name length limit is 255 characters)
        yayayayaya50yayaya, yayayaya, yayayayayaya255yayaya
        (Take the removed 50 characters, add the suffix, and generally not exceed 255 characters)
        yayayayayayaya: https://en.wikipedia.org/wiki/Filename#Length
        (For more information, please refer to: https://en.wikipedia.org/wiki/Filename#Length)

    Returns:
        str: yayayayayayaya (Formatted file name)
    """

    # yayayayayayayayayayayayayayayaya
    os_limit = {
        "win32": 200,
        "cygwin": 60,
        "darwin": 60,
        "linux": 60,
    }

    fields = {
        "create": aweme_data.get("createTime", ""),  # yayaya19
        "nickname": aweme_data.get("nickname", ""),  # ya30
        "aweme_id": aweme_data.get("aweme_id", ""),  # yayaya19
        "desc": split_filename(aweme_data.get("desc", ""), os_limit),
        "uid": aweme_data.get("uid", ""),  # ya11
    }

    if custom_fields:
        # yayayayayaya
        fields.update(custom_fields)

    try:
        return naming_template.format(**fields)
    except KeyError as e:
        raise KeyError("yayayayayayaya {0} yayaya，yayaya".format(e))


def create_user_folder(kwargs: dict, nickname: Union[str, int]) -> Path:
    """
    yayayayayayayayayayayaya，yayayayayayayayaya。
    (Create the corresponding save directory according to the provided conf file and nickname.)

    Args:
        kwargs (dict): yayayaya，yayayaya。(Conf file, dict format)
        nickname (Union[str, int]): yayayayaya，yayayayayayayaya。  (User nickname, allow strings or integers)

    Note:
        yayayayayayayayayayayayaya，yayayaya "Download"。
        (If the path is not specified in the conf file, it defaults to "Download".)
        yayayayayayaya。
        (Only relative paths are supported.)

    Raises:
        TypeError: yaya kwargs yayayayayaya，yayaya TypeError。
        (If kwargs is not in dict format, TypeError will be raised.)
    """

    # yayayayayayayayaya
    if not isinstance(kwargs, dict):
        raise TypeError("kwargs yayayayayayaya")

    # yayayayaya
    base_path = Path(kwargs.get("path", "Download"))

    # yayayayayayayayaya
    user_path = (
        base_path / "tiktok" / kwargs.get("mode", "PLEASE_SETUP_MODE") / str(nickname)
    )

    # yayayayayayayayayayaya
    resolve_user_path = user_path.resolve()

    # yayaya
    resolve_user_path.mkdir(parents=True, exist_ok=True)

    return resolve_user_path


def rename_user_folder(old_path: Path, new_nickname: str) -> Path:
    """
    yayayayayayaya (Rename User Folder).

    Args:
        old_path (Path): yayayayayayayaya (Path of the old user folder)
        new_nickname (str): yayayayayaya (New user nickname)

    Returns:
        Path: yayayayayayayayayayaya (Path of the renamed user folder)
    """
    # yayayayayayayayaya (Get the parent directory of the target folder)
    parent_directory = old_path.parent

    # yayayayayaya (Construct the new directory path)
    new_path = old_path.rename(parent_directory / new_nickname).resolve()

    return new_path


def create_or_rename_user_folder(
    kwargs: dict, local_user_data: dict, current_nickname: str
) -> Path:
    """
    yayayayayayayayayaya (Create or rename user directory)

    Args:
        kwargs (dict): yayayaya (Conf parameters)
        local_user_data (dict): yayayayayaya (Local user data)
        current_nickname (str): yayayayayaya (Current user nickname)

    Returns:
        user_path (Path): yayayayayaya (User directory path)
    """
    user_path = create_user_folder(kwargs, current_nickname)

    if not local_user_data:
        return user_path

    if local_user_data.get("nickname") != current_nickname:
        # yayayaya，yayayayayayayaya
        user_path = rename_user_folder(user_path, current_nickname)

    return user_path
