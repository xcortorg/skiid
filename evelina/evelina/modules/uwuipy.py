import re
import random
from typing import Optional


class uwuipy:
    __uwu_pattern = [
        (r"[rl]", "w"),
        (r"[RL]", "W"),
        (r"n([aeiou])", r"ny\g<1>"),
        (r"N([aeiou])", r"Ny\g<1>"),
        (r"N([AEIOU])", r"NY\g<1>"),
        (r"ove", "uv"),
        (r"pog", "poggies"),
    ]

    __exclamations = [
        "!?",
        "?!!",
        "?!?1",
        "!!11",
        "!!1!",
        "?!?!",
        "#",
        "@",
    ]

    __faces = [
        r"(・\`ω\´・)",
        ";;w;;",
        "OwO",
        "owo",
        "UwU",
        r"\>w\<",
        "^w^",
        "ÚwÚ",
        "^-^",
        ":3",
        "x3",
        "Uwu",
        "uwU",
        "(uwu)",
        "(ᵘʷᵘ)",
        "(ᵘﻌᵘ)",
        "(◡ ω ◡)",
        "(◡ ꒳ ◡)",
        "(◡ w ◡)",
        "(◡ ሠ ◡)",
        "(˘ω˘)",
        "(⑅˘꒳˘)",
        "(˘ᵕ˘)",
        "(˘ሠ˘)",
        "(˘³˘)",
        "(˘ε˘)",
        "(˘˘˘)",
        "( ᴜ ω ᴜ )",
        "(„ᵕᴗᵕ„)",
        "(ㅅꈍ ˘ ꈍ)",
        "(⑅˘꒳˘)",
        "( ｡ᵘ ᵕ ᵘ ｡)",
        "( ᵘ ꒳ ᵘ ✼)",
        "( ˘ᴗ˘ )",
        "(ᵕᴗ ᵕ⁎)",
        "*:･ﾟ✧(ꈍᴗꈍ)✧･ﾟ:*",
        "*˚*(ꈍ ω ꈍ).₊̣̇.",
        "(。U ω U。)",
        "(U ᵕ U❁)",
        "(U ﹏ U)",
        "(◦ᵕ ˘ ᵕ◦)",
        "ღ(U꒳Uღ)",
        "♥(。U ω U。)",
        "– ̗̀ (ᵕ꒳ᵕ) ̖́-",
        "( ͡U ω ͡U )",
        "( ͡o ᵕ ͡o )",
        "( ͡o ꒳ ͡o )",
        "( ˊ.ᴗˋ )",
        "(ᴜ‿ᴜ✿)",
        "~(˘▾˘~)",
        "(｡ᴜ‿‿ᴜ｡)",
    ]
    
    def __init__(self, seed: Optional[int] = None, stutter_chance: float = 1, face_chance: float = 1, exclamation_chance: float = 1,):
        if not 0.0 <= stutter_chance <= 1.0:
            raise ValueError("Invalid input value for stutterChance, supported range is 0-1.0")
        if not 0.0 <= face_chance <= 1.0:
            raise ValueError("Invalid input value for faceChance, supported range is 0-1.0")
        if not 0.0 <= exclamation_chance <= 1.0:
            raise ValueError("Invalid input value for exclamationChance, supported range is 0-1.0")
        random.seed(seed)
        self._stutter_chance = stutter_chance
        self._face_chance = face_chance
        self._exclamation_chance = exclamation_chance

    def _uwuify_words(self, _msg):
        words = _msg.split(" ")
        for idx, word in enumerate(words):
            if not word:
                continue
            if re.search(r"((http:|https:)//[^ \<]*[^ \<\.])", word):
                continue
            if word[0] == ":" or word[0] == "<":
                continue
            for pattern, substitution in self.__uwu_pattern:
                word = re.sub(pattern, substitution, word)
            words[idx] = word
        return " ".join(words)

    def _uwuify_spaces(self, _msg):
        words = _msg.split(" ")
        for idx, word in enumerate(words):
           next_char_case = word[1].isupper() if len(word) > 1 else False
        _word = ""
        if random.random() <= self._stutter_chance:
                stutter_len = random.randrange(1, 3)
                for j in range(stutter_len + 1):
                    _word += (
                        word[0]
                        if j == 0
                        else (word[0].upper() if next_char_case else word[0].lower())
                    ) + "-"
                _word += (
                    word[0].upper() if next_char_case else word[0].lower()
                ) + word[1:]
        if random.random() <= self._face_chance:
                _word = (_word or word) + " " + random.choice(self.__faces)
        words[idx] = _word or word
        return " ".join(words)

    def _uwuify_exclamations(self, _msg):
        words = _msg.split(" ")
        for idx, word in enumerate(words):
            if not word:
                continue
            if (
                not re.search(r"[?!]+$", word)
            ) or random.random() > self._exclamation_chance:
                continue
            word = re.sub(r"[?!]+$", "", word) + random.choice(self.__exclamations)
            words[idx] = word
        return " ".join(words)

    def uwuify(self, msg):
        msg = self._uwuify_words(msg)
        msg = self._uwuify_spaces(msg)
        msg = self._uwuify_exclamations(msg)
        return msg