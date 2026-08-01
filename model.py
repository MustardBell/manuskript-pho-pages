import re
from dataclasses import dataclass, field


class PhoModelError(ValueError):
    pass


def split_markdown_frontmatter(source):
    """Return a Markdown frontmatter prefix and the remaining body."""
    normalized = str(source or "").replace("\r\n", "\n").replace(
        "\r", "\n"
    )
    patterns = (
        r"\A\ufeff?---[ \t]*\n.*?^(?:---|\.\.\.)[ \t]*(?:\n|$)",
        r"\A\ufeff?\+\+\+[ \t]*\n.*?^\+\+\+[ \t]*(?:\n|$)",
    )
    match = next((
        match
        for pattern in patterns
        for match in [re.search(pattern, normalized, re.M | re.S)]
        if match is not None
    ), None)
    if match is None:
        return "", normalized
    end = match.end()
    spacing = re.match(r"(?:[ \t]*\n)*", normalized[end:])
    if spacing is not None:
        end += spacing.end()
    return normalized[:end], normalized[end:]


@dataclass
class PhoReply:
    metadata: list[str] = field(default_factory=lambda: ["User"])
    body: str = ""

    @property
    def user(self):
        return self.metadata[0].strip() if self.metadata else "User"

    def set_fields(self, user, metadata):
        user = str(user).strip() or "User"
        extra = [
            value.strip()
            for value in str(metadata).split("\t")
            if value.strip()
        ]
        self.metadata = [user] + extra

    def to_source(self):
        return "{}\n------\n{}".format(
            "\t".join(self.metadata),
            self.body.strip("\n"),
        )


@dataclass
class PhoThread:
    topic: str = "A question"
    board: str = "General"
    poster: str = "Original Poster"
    original_post: str = ""
    replies: list[PhoReply] = field(default_factory=list)
    no_original_post: bool = False
    extra_directives: list[str] = field(default_factory=list)

    FIELD = re.compile(r"(?m)^(TOPIC|BOARD|POSTER)\t([^\n]*)$")
    ORIGINAL_POST = re.compile(r"(?ms)^BOOP\s*\n(.*?)^EOOP\s*$")
    REPLIES = re.compile(
        r"(?ms)^REPLIES\s*\n(.*?)^EOREPLIES\s*$"
    )

    @classmethod
    def parse(cls, source):
        original = cls.ORIGINAL_POST.search(source)
        replies_match = cls.REPLIES.search(source)
        shell = cls.ORIGINAL_POST.sub("", source)
        shell = cls.REPLIES.sub("", shell)
        values = {
            match.group(1): match.group(2).strip()
            for match in cls.FIELD.finditer(shell)
        }
        replies = (
            cls._parse_replies(replies_match.group(1))
            if replies_match is not None
            else []
        )
        known = cls.FIELD.sub("", shell)
        no_original_post = bool(re.search(
            r"(?m)^\s*NOOP\s*$",
            known,
        ))
        known = re.sub(r"(?m)^\s*NOOP\s*$", "", known)
        extra = [
            block.strip("\n")
            for block in re.split(r"\n{2,}", known)
            if block.strip()
        ]
        return cls(
            topic=values.get("TOPIC", "A question"),
            board=values.get("BOARD", "General"),
            poster=values.get("POSTER", "Original Poster"),
            original_post=(
                original.group(1).strip("\n")
                if original is not None
                else ""
            ),
            replies=replies,
            no_original_post=no_original_post,
            extra_directives=extra,
        )

    @staticmethod
    def _parse_replies(source):
        replies = []
        for raw_reply in re.split(r"(?m)^\*{3,}\s*$", source):
            if not raw_reply.strip():
                continue
            parts = re.split(
                r"(?m)^-{3,}\s*$",
                raw_reply,
                maxsplit=1,
            )
            if len(parts) != 2:
                raise PhoModelError(
                    "Every PHO reply must have metadata, a line of at "
                    "least three dashes, and a message body."
                )
            metadata, body = parts
            fields = [
                value.strip()
                for value in metadata.strip().split("\t")
            ]
            if not fields or not fields[0]:
                raise PhoModelError(
                    "Every PHO reply requires a username."
                )
            replies.append(PhoReply(fields, body.strip("\n")))
        return replies

    def to_source(self):
        values = [
            "THREAD",
            "TOPIC\t{}".format(self.topic.strip()),
            "BOARD\t{}".format(self.board.strip()),
            "POSTER\t{}".format(self.poster.strip()),
        ]
        if self.no_original_post:
            values.append("NOOP")
        if self.extra_directives:
            values.extend(self.extra_directives)
        values.extend([
            "BOOP",
            self.original_post.strip("\n"),
            "EOOP",
        ])
        if self.replies:
            values.extend([
                "REPLIES",
                "\n*****\n".join(
                    reply.to_source() for reply in self.replies
                ),
                "EOREPLIES",
            ])
        values.append("EOTHREAD")
        return "\n".join(values)


@dataclass
class PhoPage:
    settings: dict[str, str] = field(default_factory=dict)
    welcome: bool = True
    users_source: str = ""
    threads: list[PhoThread] = field(default_factory=list)
    extra_blocks: list[str] = field(default_factory=list)
    prefix: str = ""
    suffix: str = ""

    SCENE = re.compile(
        r"(?ms)^PHO Interlude[^\n]*\n(.*?)"
        r"^EOPHO Interlude[^\n]*$"
    )
    TOKENS = re.compile(
        r"(?ms)^SETTINGS\b[^\n]*$"
        r"|^USERS\s*\n.*?^EOUSERS\s*$"
        r"|^WELCOME[\t ]*$"
        r"|^THREAD\s*\n.*?^EOTHREAD\s*$"
    )

    @classmethod
    def parse(cls, source):
        source = str(source or "").replace("\r\n", "\n").replace(
            "\r", "\n"
        )
        scene = cls.SCENE.search(source)
        if scene is None:
            raise PhoModelError(
                "The page is not wrapped in PHO Interlude and "
                "EOPHO Interlude directives."
            )
        page = cls(
            prefix=source[:scene.start()],
            suffix=source[scene.end():],
            welcome=False,
        )
        body = scene.group(1)
        position = 0
        for token in cls.TOKENS.finditer(body):
            page._preserve_extra(body[position:token.start()])
            value = token.group(0)
            if value.startswith("SETTINGS"):
                page._parse_settings(value)
            elif value.startswith("USERS"):
                page.users_source = re.sub(
                    r"(?ms)^USERS\s*\n|^EOUSERS\s*$",
                    "",
                    value,
                ).strip("\n")
            elif value.startswith("WELCOME"):
                page.welcome = True
            elif value.startswith("THREAD"):
                body_match = re.match(
                    r"(?ms)^THREAD\s*\n(.*?)^EOTHREAD\s*$",
                    value,
                )
                page.threads.append(
                    PhoThread.parse(body_match.group(1))
                )
            position = token.end()
        page._preserve_extra(body[position:])
        if not page.threads:
            page.threads.append(PhoThread())
        return page

    @classmethod
    def initialize(cls, original_post=""):
        return cls(
            settings={
                "reader": "Reader",
                "posts": "10",
                "date": "2011-01-01T00:00:00-05:00",
                "startpage": "1",
            },
            welcome=True,
            threads=[PhoThread(original_post=str(original_post))],
        )

    @classmethod
    def initialize_from_markdown(cls, source):
        prefix, body = split_markdown_frontmatter(source)
        page = cls.initialize(body if body.strip() else "")
        page.prefix = prefix
        return page

    def _parse_settings(self, source):
        raw = source[len("SETTINGS"):].lstrip("\t ")
        for field in raw.split("\t"):
            if ":" not in field:
                if field.strip():
                    self.extra_blocks.append(field.strip())
                continue
            key, value = field.split(":", 1)
            if key:
                self.settings[key] = value

    def _preserve_extra(self, value):
        if value.strip():
            self.extra_blocks.append(value.strip("\n"))

    def setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        value = str(value).strip()
        if value:
            self.settings[key] = value
        else:
            self.settings.pop(key, None)

    def to_source(self):
        body = []
        if self.settings:
            body.append(
                "SETTINGS\t" + "\t".join(
                    "{}:{}".format(key, value)
                    for key, value in self.settings.items()
                )
            )
        if self.welcome:
            body.append("WELCOME")
        if self.users_source.strip():
            body.append(
                "USERS\n{}\nEOUSERS".format(
                    self.users_source.strip("\n")
                )
            )
        body.extend(
            thread.to_source() for thread in self.threads
        )
        body.extend(self.extra_blocks)
        scene = "PHO Interlude\n{}\nEOPHO Interlude".format(
            "\n\n".join(value for value in body if value)
        )
        return self.prefix + scene + self.suffix
