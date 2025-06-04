import datetime
import arrow


def is_integerable(n: float) -> bool:
    answer = True if str(n).split(".")[1] == "0" else False
    return answer


def is_leapyear(d: int):
    if d % 4 == 0:
        if str(d)[2] == "0" and str(d)[3] == 0:
            return False
        else:
            return True
    else:
        return False


def get_leapyear():
    now = datetime.datetime.now()
    if now.month > 2 and now.day > 29:
        year = now.year + 1
    else:
        year = now.year
    leap = year % 4 == 0 and year % 100 != 0 or year % 100 == 0 and year % 400 == 0
    return leap


async def get_birthday(b: str, humanize: bool = False):
    if b.split()[1] == "29" and b.lower().split()[0] in ["february", "feb"]:
        d = "March 1"
    else:
        d = b
    form = get_date_format(d)
    year = datetime.datetime.now().year
    if "ago" in arrow.get(f"{d} {year}", form).humanize(granularity="day"):
        year = year + 1
    else:
        year = year
    if humanize is True:
        return arrow.get(f"{d} {year}", form).humanize(granularity="day")
    else:
        return arrow.get(f"{d} {year}", form).datetime


def get_date_format(s: str) -> str:
    data = s.lower().split()
    month = data[0]
    day = data[1]
    m = len(month) if len(month) <= 3 else "MMMM"
    day = day.replace("th", "").replace("st", "")
    d = "D" if len(day) == 1 else "DD"
    return f"{m} {d} YYYY"
