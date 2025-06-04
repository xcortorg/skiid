import unittest
import unittest.async_case
from unittest.mock import patch
from system.base.embed import EmbedScript, get_color
from discord import Color

# AUTO GENERATED


class TestEmbedScript(unittest.async_case.IsolatedAsyncioTestCase):
    @patch("discord.Color.random", return_value=Color(0x123456))
    def test_get_color(self, mock_random):
        self.assertEqual(get_color("random"), Color(0x123456))
        self.assertEqual(get_color("invisible"), Color.from_str("#2B2D31"))
        self.assertEqual(get_color("blurple"), Color.blurple())
        self.assertEqual(get_color("black"), Color.from_str("#000001"))
        self.assertIsNone(get_color("invalid_color"))

    def test_embed_script_initialization(self):
        script = "{embed}\n{color: 000000}\n{title: tittle}\n{description: desc}"
        embed_script = EmbedScript(script)
        self.assertEqual(embed_script.script, script)

    async def test_add_button(self):
        script = "{button: https://example.com && Click Me && 👆}"
        embed_script = EmbedScript(script)
        embed_script.objects["button"] = []
        embed_script.parser.tags = []
        embed_script.embed_parser.tags = []
        await embed_script.resolve_objects()
        self.assertEqual(len(embed_script.objects["button"]), 1)
        self.assertEqual(
            embed_script.objects["button"][0]["url"], "https://example.com"
        )
        self.assertEqual(embed_script.objects["button"][0]["label"], "Click Me")
        self.assertEqual(embed_script.objects["button"][0]["emoji"], "👆")

    async def test_add_multiple_buttons(self):
        script = "{button: https://example.com && Click Me && 👆}\n{button: https://discord.com && Discord && 🎮}"
        embed_script = EmbedScript(script)
        embed_script.objects["button"] = []
        embed_script.parser.tags = []
        embed_script.embed_parser.tags = []
        await embed_script.resolve_objects()
        self.assertEqual(len(embed_script.objects["button"]), 2)
        self.assertEqual(
            embed_script.objects["button"][0]["url"], "https://example.com"
        )
        self.assertEqual(embed_script.objects["button"][0]["label"], "Click Me")
        self.assertEqual(embed_script.objects["button"][0]["emoji"], "👆")
        self.assertEqual(
            embed_script.objects["button"][1]["url"], "https://discord.com"
        )
        self.assertEqual(embed_script.objects["button"][1]["label"], "Discord")
        self.assertEqual(embed_script.objects["button"][1]["emoji"], "🎮")


# AUTO GENERATED
if __name__ == "__main__":
    unittest.main()
