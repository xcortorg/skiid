import hashlib
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
from cryptography.hazmat.backends import default_backend
import time
from typing import Union


class XBogus:
    def __init__(self, user_agent: str):
        self.byte_array = (
            [None] * 48 + list(range(10)) + [None] * 7 + list(range(10, 16))
        )
        self.character = (
            "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
        )
        self.ua_key = b"\x00\x01\x0c"
        self.user_agent = user_agent

    def md5_to_array(self, md5: str) -> list:
        if len(md5) > 32:
            return [ord(c) for c in md5]
        array = []
        idx = 0
        while idx < len(md5):
            array.append(
                (self.byte_array[ord(md5[idx])] << 4)
                | self.byte_array[ord(md5[idx + 1])]
            )
            idx += 2
        return array

    def md5_encrypt(self, url_params: str) -> list:
        hashed_url_params = self.md5_to_array(
            self.md5(self.md5_to_array(self.md5(url_params)))
        )
        return hashed_url_params

    def md5(self, input_data: Union[str, list]) -> str:
        if isinstance(input_data, str):
            array = self.md5_to_array(input_data)
        elif isinstance(input_data, list):
            array = input_data
        else:
            raise ValueError("Invalid input type. Expected string or array.")

        md5hash = hashlib.md5()
        md5hash.update(bytes(array))
        return md5hash.hexdigest()

    def encoding_conversion(self, *args) -> str:
        segment = [args[0], args[9]] + list(args[1:9]) + list(args[10:])
        return bytes(segment).decode("latin1")

    def encoding_conversion_alternative(self, a: int, b: int, c: str) -> str:
        return chr(a) + chr(b) + c

    def rc4_encrypt(self, key: bytes, data: bytes) -> bytes:
        cipher = Cipher(algorithms.ARC4(key), mode=None, backend=default_backend())
        encryptor = cipher.encryptor()
        return encryptor.update(data)

    def calculation(self, a1: int, a2: int, a3: int) -> str:
        x1 = (a1 & 255) << 16
        x2 = (a2 & 255) << 8
        x3 = x1 | x2 | a3
        return (
            self.character[(x3 & 16515072) >> 18]
            + self.character[(x3 & 258048) >> 12]
            + self.character[(x3 & 4032) >> 6]
            + self.character[x3 & 63]
        )

    def get_x_bogus(self, url_params: str) -> str:
        array1 = self.md5_to_array(
            self.md5(
                self.rc4_encrypt(self.ua_key, self.user_agent.encode("latin1")).decode(
                    "latin1"
                )
            )
        )
        array2 = self.md5_to_array(
            self.md5(self.md5_to_array("d41d8cd98f00b204e9800998ecf8427e"))
        )
        url_params_array = self.md5_encrypt(url_params)

        timer = int(time.time())
        ct = 536919696
        new_array = [
            64,
            0.00390625,
            1,
            12,
            url_params_array[14],
            url_params_array[15],
            array2[14],
            array2[15],
            array1[14],
            array1[15],
            (timer >> 24) & 255,
            (timer >> 16) & 255,
            (timer >> 8) & 255,
            timer & 255,
            (ct >> 24) & 255,
            (ct >> 16) & 255,
            (ct >> 8) & 255,
            ct & 255,
        ]

        xor_result = new_array[0]
        for i in range(1, len(new_array)):
            if isinstance(new_array[i], (int, float)):
                xor_result ^= new_array[i]

        new_array.append(xor_result)

        array3 = new_array[::2]
        array4 = new_array[1::2]
        merged_array = array3 + array4

        garbled_code = self.encoding_conversion_alternative(
            2,
            255,
            self.rc4_encrypt(
                b"\xff", self.encoding_conversion(*merged_array).encode("latin1")
            ).decode("latin1"),
        )

        result = ""
        idx = 0
        while idx < len(garbled_code):
            result += self.calculation(
                ord(garbled_code[idx]),
                ord(garbled_code[idx + 1]),
                ord(garbled_code[idx + 2]),
            )
            idx += 3

        return result
