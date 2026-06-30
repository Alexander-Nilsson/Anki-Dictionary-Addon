from __future__ import annotations

import re

from ..utils.logger import get_logger

logger = get_logger(__name__.split(".")[-1])


class HtmlCleaner:
    @staticmethod
    def cleanHTML(text: str) -> str:
        # Switch bold style to <b>
        text = re.sub(
            r"(<span style=\"[^\"]*?)font-weight:600;(.*?\">.*?</span>)",
            r"<b>\1\2</b>",
            text,
            flags=re.S,
        )
        text = re.sub(
            r"(<span style=\"[^\"]*?)font-style:italic;(.*?\">.*?</span>)",
            r"<i>\1\2</i>",
            text,
            flags=re.S,
        )
        text = re.sub(
            r"(<span style=\"[^\"]*?)text-decoration: underline;(.*?\">.*?</span>)",
            r"<u>\1\2</u>",
            text,
            flags=re.S,
        )

        # Switch paragraphs to <br>
        text = re.sub(r"</p>", r"<br />", text, flags=re.S)

        # Trim unneeded bits
        text = re.sub(r".+</head>", r"", text, flags=re.S)
        text = re.sub(
            r"(<html[^>]*?>|</html>|<body[^>]*?>|</body>|<p[^>]*?>|<span[^>]*?>|</span>)",
            r"",
            text,
            flags=re.S,
        )
        text = text.strip()

        # Remove any trailing <br /> (there can be two)
        text = re.sub(r"<br />$", r"", text)
        text = re.sub(r"<br />$", r"", text)

        return text
