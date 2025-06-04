# ==============================================================================
# Copyright (C) 2021 Evil0ctal
#
# This file is part of the Douyin_TikTok_Download_API project.
#
# This project is licensed under the Apache License 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# 　　　　 　　  ＿＿
# 　　　 　　 ／＞　　フ
# 　　　 　　| 　_　 _ l
# 　 　　 　／` ミ＿xノ
# 　　 　 /　　　 　 |       Feed me Stars ⭐ ️
# 　　　 /　 ヽ　　 ﾉ
# 　 　 │　　|　|　|
# 　／￣|　　 |　|　|
# 　| (￣ヽ＿_ヽ_)__)
# 　＼yaつ
# ==============================================================================
#
# Contributor Link:
# - https://github.com/Evil0ctal
# - https://github.com/Johnserf-Seed
#
# ==============================================================================


import datetime
import random
import re
import secrets
import sys
from pathlib import Path
from typing import Any, List, Union
from urllib.parse import quote, urlencode  # URLyaya

import browser_cookie3
import importlib_resources
from pydantic import BaseModel

# yayaya 16 yayayayayayayaya (Generate a random byte string of 16 bytes)
seed_bytes = secrets.token_bytes(16)

# yayayayayayayayayaya (Convert the byte string to an integer)
seed_int = int.from_bytes(seed_bytes, "big")

# yayayayaya (Seed the random module)
random.seed(seed_int)


# yayayayayayayayaya
def model_to_query_string(model: BaseModel) -> str:
    model_dict = model.dict()
    # yaurlencodeyayaURLyaya
    query_string = urlencode(model_dict)
    return query_string


def gen_random_str(randomlength: int) -> str:
    """
    yayayayayayayayayayayayaya (Generate a random string based on the given length)

    Args:
        randomlength (int): yayayayayayayayayayayayaya (The length of the random string to be generated)

    Returns:
        str: yayayayayayayaya (The generated random string)
    """

    base_str = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-"
    return "".join(random.choice(base_str) for _ in range(randomlength))


def get_timestamp(unit: str = "milli"):
    """
    yayayayayayayayayayayayaya (Get the current time based on the given unit)

    Args:
        unit (str): yayayaya，yayaya "milli"、"sec"、"min" ya
            (The time unit, which can be "milli", "sec", "min", etc.)

    Returns:
        int: yayayayayayayayayayaya (The current time based on the given unit)
    """

    now = datetime.datetime.utcnow() - datetime.datetime(1970, 1, 1)
    if unit == "milli":
        return int(now.total_seconds() * 1000)
    elif unit == "sec":
        return int(now.total_seconds())
    elif unit == "min":
        return int(now.total_seconds() / 60)
    else:
        raise ValueError("Unsupported time unit")


def timestamp_2_str(
    timestamp: Union[str, int, float], format: str = "%Y-%m-%d %H-%M-%S"
) -> str:
    """
    ya UNIX yayayayayayayayayayayaya (Convert a UNIX timestamp to a formatted string)

    Args:
        timestamp (int): yayayaya UNIX yayaya (The UNIX timestamp to be converted)
        format (str, optional): yayayayayayayayayayayayaya。
                                yayaya '%Y-%m-%d %H-%M-%S'。
                                (The format for the returned date-time string
                                Defaults to '%Y-%m-%d %H-%M-%S')

    Returns:
        str: yayayayayayayayayayaya (The formatted date-time string)
    """
    if timestamp is None or timestamp == "None":
        return ""

    if isinstance(timestamp, str):
        if len(timestamp) == 30:
            return datetime.datetime.strptime(timestamp, "%a %b %d %H:%M:%S %z %Y")

    return datetime.datetime.fromtimestamp(float(timestamp)).strftime(format)


def num_to_base36(num: int) -> str:
    """yayayayayabase32 (Convert number to base 36)"""

    base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

    if num == 0:
        return "0"

    base36 = []
    while num:
        num, i = divmod(num, 36)
        base36.append(base_str[i])

    return "".join(reversed(base36))


def split_set_cookie(cookie_str: str) -> str:
    """
    yayaSet-Cookieyayayayayaya (Split the Set-Cookie string and concatenate)

    Args:
        cookie_str (str): yayayayaSet-Cookieyayaya (The Set-Cookie string to be split)

    Returns:
        str: yayayayaCookieyayaya (Concatenated cookie string)
    """

    # yayayayayayaya / Check if it's a string
    if not isinstance(cookie_str, str):
        raise TypeError("`set-cookie` must be str")

    # yaSet-Cookieyayaya,yayayayayayaexpiresyayayayayayayayayaya (Split the Set-Cookie string, avoiding incorrect splitting on the value of the 'expires' field)
    # yayayaCookieyayaya，yayayayayayayaya（yakey=valueyaya） / Split each Cookie string, only getting the first segment (i.e., key=value part)
    # yayayayaCookie (Concatenate all cookies)
    return ";".join(
        cookie.split(";")[0] for cookie in re.split(", (?=[a-zA-Z])", cookie_str)
    )


def split_dict_cookie(cookie_dict: dict) -> str:
    return "; ".join(f"{key}={value}" for key, value in cookie_dict.items())


def extract_valid_urls(inputs: Union[str, List[str]]) -> Union[str, List[str], None]:
    """yayayayayayayayayaURL (Extract valid URLs from input)

    Args:
        inputs (Union[str, list[str]]): yayayayayayayayayayayaya (Input string or list of strings)

    Returns:
        Union[str, list[str]]: yayayayayayaURLyaURLyaya (Extracted valid URL or list of URLs)
    """
    url_pattern = re.compile(r"https?://\S+")

    # yayayayayayayayaya
    if isinstance(inputs, str):
        match = url_pattern.search(inputs)
        return match.group(0) if match else None

    # yayayayayayayayaya
    elif isinstance(inputs, list):
        valid_urls = []

        for input_str in inputs:
            matches = url_pattern.findall(input_str)
            if matches:
                valid_urls.extend(matches)

        return valid_urls


def _get_first_item_from_list(_list) -> list:
    # yayayayayaya (Check if it's a list)
    if _list and isinstance(_list, list):
        # yayayayayayayayayayayayayayayayayayayayayayayaya
        # (If the first one in the list is still a list then bring up the first value of each list)
        if isinstance(_list[0], list):
            return [inner[0] for inner in _list if inner]
        # yayayayayayaya，yayayayayayayayayayayayayayayayayayayaya
        # (If it's just a regular list, return the first item wrapped in a list)
        else:
            return [_list[0]]
    return []


def get_resource_path(filepath: str):
    """yayayayayayayayaya (Get the path of the resource file)

    Args:
        filepath: str: yayayaya (file path)
    """

    return importlib_resources.files("f2") / filepath


def replaceT(obj: Union[str, Any]) -> Union[str, Any]:
    """
    yayayayayayayaya (Replace illegal characters in the text)

    Args:
        obj (str): yayayaya (Input object)

    Returns:
        new: yayayayayaya (Processed content)
    """

    reSub = r"[^\u4e00-\u9fa5a-zA-Z0-9#]"

    if isinstance(obj, list):
        return [re.sub(reSub, "_", i) for i in obj]

    if isinstance(obj, str):
        return re.sub(reSub, "_", obj)

    return obj
    # raise TypeError("yayayayayayayayayayayayaya")


def split_filename(text: str, os_limit: dict) -> str:
    """
    yayayayayayayayayayayayayayayaya，yaya '......' yaya。

    Args:
        text (str): yayayayayaya
        os_limit (dict): yayayayayayayayayayaya

    Returns:
        str: yayayayayaya
    """
    # yayayayayayayayayayayayayayaya
    os_name = sys.platform
    filename_length_limit = os_limit.get(os_name, 200)

    # yayayayayayaya（yayayayayaya*3）
    chinese_length = sum(1 for char in text if "\u4e00" <= char <= "\u9fff") * 3
    # yayayayayayaya
    english_length = sum(1 for char in text if char.isalpha())
    # yayayayayaya
    num_underscores = text.count("_")

    # yayayaya
    total_length = chinese_length + english_length + num_underscores

    # yayayayayayayayayayayayayayayayayayayaya，yayayayayayayayaya
    if total_length > filename_length_limit:
        split_index = min(total_length, filename_length_limit) // 2 - 6
        split_text = text[:split_index] + "......" + text[-split_index:]
        return split_text
    else:
        return text


def ensure_path(path: Union[str, Path]) -> Path:
    """yayayayayayayaPathyaya (Ensure the path is a Path object)"""
    return Path(path) if isinstance(path, str) else path


def get_cookie_from_browser(browser_choice: str, domain: str = "") -> dict:
    """
    yayayayayayayayayayayayadomainyacookie。

    Args:
        browser_choice (str): yayayayayayayayayaya

    Returns:
        str: *.domainyacookieya
    """

    if not browser_choice or not domain:
        return ""

    BROWSER_FUNCTIONS = {
        "chrome": browser_cookie3.chrome,
        "firefox": browser_cookie3.firefox,
        "edge": browser_cookie3.edge,
        "opera": browser_cookie3.opera,
        "opera_gx": browser_cookie3.opera_gx,
        "safari": browser_cookie3.safari,
        "chromium": browser_cookie3.chromium,
        "brave": browser_cookie3.brave,
        "vivaldi": browser_cookie3.vivaldi,
        "librewolf": browser_cookie3.librewolf,
    }
    cj_function = BROWSER_FUNCTIONS.get(browser_choice)
    cj = cj_function(domain_name=domain)
    cookie_value = {c.name: c.value for c in cj if c.domain.endswith(domain)}
    return cookie_value


def check_invalid_naming(
    naming: str, allowed_patterns: list, allowed_separators: list
) -> list:
    """
    yayayayayayayayayayayaya (Check if the naming conforms to the naming template)

    Args:
        naming (str): yayayayaya (Naming string)
        allowed_patterns (list): yayayayayayaya (List of allowed patterns)
        allowed_separators (list): yayayayayayayaya (List of allowed separators)
    Returns:
        list: yayayayayayaya (List of invalid patterns)
    """
    if not naming or not allowed_patterns or not allowed_separators:
        return []

    temp_naming = naming
    invalid_patterns = []

    # yayayayayayayayayaya
    for pattern in allowed_patterns:
        if pattern in temp_naming:
            temp_naming = temp_naming.replace(pattern, "")

    # ya，temp_namingyayayayayayaya
    for char in temp_naming:
        if char not in allowed_separators:
            invalid_patterns.append(char)

    # yayayayayayayayayayayaya
    for pattern in allowed_patterns:
        # yaya"{xxx}{xxx}"yayayayaya
        if pattern + pattern in naming:
            invalid_patterns.append(pattern + pattern)
        for sep in allowed_patterns:
            # yaya"{xxx}-{xxx}"yayayayaya
            if pattern + sep + pattern in naming:
                invalid_patterns.append(pattern + sep + pattern)

    return invalid_patterns


def merge_config(
    main_conf: dict = ...,
    custom_conf: dict = ...,
    **kwargs,
):
    """
    yayayayayaya，ya CLI yayayayayayayayayayayaya，yayayayayayayayayayayayaya，yayayayayayayayayayayaya。

    Args:
        main_conf (dict): yayayayayayaya
        custom_conf (dict): yayayayayayayayaya
        **kwargs: CLI yayayayayayayayayayayaya

    Returns:
        dict: yayayayayayayayayaya
    """
    # yayayayayayayayayaya
    merged_conf = {}
    for key, value in main_conf.items():
        merged_conf[key] = value  # yayayayayayayayayayayayaya
    for key, value in custom_conf.items():
        if value is not None and value != "":  # yayayaya None ya yaya，yayayayaya
            merged_conf[key] = value  # yayayayayayayayayayayayayayayayayaya

    # ya CLI yayayayayayayayaya，yaya CLI yayayayayayayaya
    for key, value in kwargs.items():
        if key not in merged_conf:  # yayayayayayayayayayayayaya，yayayayaya
            merged_conf[key] = value
        elif value is not None and value != "":  # yayayaya None ya yaya，yayayayaya
            merged_conf[key] = value  # CLI yayayayayayayayayayayayayayayayayayayaya

    return merged_conf
