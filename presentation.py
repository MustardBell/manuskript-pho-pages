from __future__ import annotations

import copy
import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .model import PhoModelError, PhoPage


KNOWN_USERS = {
    "Bagrat": {"tag": ["Veteran Member", "The Guy in the Know"]},
    "XxVoid_CowboyxX": {},
    "xVCx": {"aliasFor": "XxVoid_CowboyxX"},
    "Reave": {"tag": ["Verified PRT Agent"]},
    "Alathea": {"tag": ["Moderator"]},
    "Huskie": {"aliasFor": "◄HuskieWakeupCall"},
    "◄HuskieWakeupCall": {},
    "Lung": {"aliasFor": "Divine_Carp"},
    "Divine_Carp": {},
    "Brocktonite03": {"tag": ["Veteran Member"]},
    "Crazy": {"aliasFor": "Master of Truth"},
    "Master of Truth": {"tag": ["Temp-banned"]},
    "Armsmaster_Protectorate_ENE_Official": {
        "tag": ["Verified Cape", "Protectorate ENE"],
    },
    "Armsmaster": {
        "aliasFor": "Armsmaster_Protectorate_ENE_Official",
    },
    "Mod": {"aliasFor": "Alathea"},
    "Meander": {"tag": ["Verified PRT Agent"]},
    "Xenology Geek": {
        "tag": ["Scientifically accurate UFOlogist"],
    },
}


class PhoPresentationError(PhoModelError):
    pass


@dataclass(frozen=True)
class PhoTimestamp:
    value: datetime
    label: str
    tooltip: str = ""


@dataclass(frozen=True)
class PhoAuthor:
    name: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhoPostPresentation:
    author: PhoAuthor
    timestamp: PhoTimestamp
    body_markdown: str
    original: bool = False


@dataclass(frozen=True)
class PhoThreadPagePresentation:
    number: int
    total: int
    posts: tuple[PhoPostPresentation, ...]
    navigation: tuple[int | None, ...]


@dataclass(frozen=True)
class PhoThreadPresentation:
    topic: str
    boards: tuple[str, ...]
    original_post: PhoPostPresentation | None
    pages: tuple[PhoThreadPagePresentation, ...]


@dataclass(frozen=True)
class PhoPresentation:
    reader: str
    show_welcome: bool
    threads: tuple[PhoThreadPresentation, ...]
    posts_per_page: int = 10
    private_messages: int = 10
    prefix_markdown: str = ""
    suffix_markdown: str = ""


@dataclass(frozen=True)
class _ReplyRecord:
    body: str
    user: str
    date: datetime
    page: int | None = None
    reply_id: str = "0"
    previous_id: str = "0"


class SinePseudoRandom:
    def __init__(self, seed):
        seed = float(seed if seed is not None else math.pi)
        self.value = math.sin(seed) * 10000

    def next(self):
        self.value = math.sin(self.value) * 10000
        return self.value - math.floor(self.value)


class PhoPresentationBuilder:
    """Resolve a parsed PHO source model into format-neutral semantics."""

    def __init__(self):
        self.settings = {}
        self.users = {}
        self.date = None
        self.date_op = None
        self._random = None

    def build(self, page):
        if not isinstance(page, PhoPage):
            raise TypeError("PHO presentation builders require PhoPage.")
        self.settings = dict(page.settings)
        self.users = copy.deepcopy(KNOWN_USERS)
        self._extract_users(page.users_source)
        self._initialize_time()
        threads = tuple(
            self._build_thread(thread) for thread in page.threads
        )
        return PhoPresentation(
            reader=self.settings.get("reader", ""),
            show_welcome=page.welcome,
            threads=threads,
            posts_per_page=self._integer_setting("posts", 10),
            private_messages=self._integer_setting("messages", 10),
            prefix_markdown=page.prefix,
            suffix_markdown=page.suffix,
        )

    def _initialize_time(self):
        date = self.settings.get("date")
        if not date:
            raise PhoPresentationError(
                "A PHO page requires SETTINGS with an ISO date."
            )
        self.date = self._parse_datetime(date)
        self.date_op = self.date
        self._random = SinePseudoRandom(self.date.timestamp() * 1000)

    def _extract_users(self, source):
        for line in source.splitlines():
            parts = line.split("\t")
            username = parts.pop(0).strip() if parts else ""
            if not username:
                continue
            self.users[username] = {}
            for parameter in parts:
                if ":" not in parameter:
                    continue
                name, value = parameter.split(":", 1)
                if name == "tag":
                    self.users[username].setdefault("tag", []).append(
                        value
                    )
                else:
                    self.users[username][name] = value

    def _build_thread(self, thread):
        replies = self._process_replies(thread.replies)
        original_post = None
        if not thread.no_original_post:
            author = self._author(thread.poster, self.date_op)
            original_post = PhoPostPresentation(
                author=author,
                timestamp=self._timestamp(self.date_op),
                body_markdown=self._resolve_mentions(
                    thread.original_post
                ),
                original=True,
            )
        return PhoThreadPresentation(
            topic=thread.topic,
            boards=tuple(
                value for value in thread.board.split("=>") if value
            ),
            original_post=original_post,
            pages=self._paginate(replies),
        )

    def _process_replies(self, replies):
        previous = {"0": self.date, None: self.date}
        latest = self.date
        processed = []
        for reply in replies:
            fields = list(reply.metadata)
            user = fields.pop(0).strip() if fields else ""
            if not user:
                raise PhoPresentationError(
                    "A PHO reply requires a username."
                )
            displacement = {}
            reply_id = "0"
            previous_id = "0"
            page = None
            stamp = None
            for field in fields:
                id_match = re.match(r"id:([0-9A-Za-z_-]+)", field)
                refer_match = re.match(
                    r"refer:([0-9A-Za-z_-]+)", field
                )
                page_match = re.match(r"page:(\d+)", field)
                stamp_match = re.match(r"=([^\s]+)", field)
                time_match = re.match(r"\+(\d+|rnd)([mhsd])", field)
                if id_match and reply_id == "0":
                    reply_id = id_match.group(1)
                if refer_match and previous_id == "0":
                    previous_id = refer_match.group(1)
                if page_match and page is None:
                    page = int(page_match.group(1))
                if stamp_match and stamp is None:
                    stamp = stamp_match.group(1)
                if time_match:
                    offset = time_match.group(1)
                    displacement[time_match.group(2)] = (
                        int(self._random.next() * 59) + 1
                        if offset == "rnd"
                        else int(offset)
                    )

            refer = bool(self.settings.get("refer"))
            if (
                refer
                and previous_id not in previous
                and previous_id != "latest"
            ):
                raise PhoPresentationError(
                    "PHO reply by {} refers to unknown message ID {!r}."
                    .format(user, previous_id)
                )
            reference = previous.get(previous_id, self.date)
            if previous_id == "latest" or not refer:
                reference = latest
                previous[None] = latest
            if stamp:
                exact = self._parse_datetime(stamp)
                reference = (
                    exact
                    if exact > self.date_op
                    else self._displace(reference, displacement)
                )
            else:
                reference = self._displace(reference, displacement)
            previous[reply_id] = reference
            if reference > latest:
                latest = reference
            self._apply_tag_metadata(user, fields, reference)
            processed.append(_ReplyRecord(
                body=self._resolve_mentions(reply.body.strip()),
                user=user,
                date=reference,
                page=page,
                reply_id=reply_id,
                previous_id=previous_id,
            ))
        return sorted(processed, key=lambda value: value.date)

    def _paginate(self, replies):
        if not replies:
            return ()
        posts = self._integer_setting("posts", 10)
        start_page = self._integer_setting("startpage", 1)
        count_op = start_page == 1
        count = len(replies) + (1 if count_op else 0)
        page_count = max(1, math.ceil(count / posts))
        first_capacity = max(1, posts - 1) if count_op else posts
        chunks = [replies[:first_capacity]]
        remaining = replies[first_capacity:]
        chunks.extend(
            remaining[index:index + posts]
            for index in range(0, len(remaining), posts)
        )
        chunks = [chunk for chunk in chunks if chunk]
        configured_end = self._integer_setting("endpage", 0)
        add_pages = self._integer_setting("addpages", 0)
        if chunks and len(chunks[-1]) < posts:
            configured_end = start_page + page_count - 1
            add_pages = 0
        end_page = max(
            1,
            configured_end,
            start_page + page_count - 1 + add_pages,
        )

        pages = []
        for offset, chunk in enumerate(chunks):
            if chunk and chunk[0].page is not None:
                start_page = chunk[0].page
                offset = 0
            current_page = start_page + offset
            if end_page < current_page:
                end_page = start_page + len(chunks)
            posts_for_page = tuple(
                PhoPostPresentation(
                    author=self._author(value.user, value.date),
                    timestamp=self._timestamp(value.date),
                    body_markdown=value.body,
                )
                for value in chunk
            )
            pages.append(PhoThreadPagePresentation(
                number=current_page,
                total=end_page,
                posts=posts_for_page,
                navigation=self._navigation(current_page, end_page),
            ))
        return tuple(pages)

    def _author(self, user, date):
        user = self._resolve_alias(user.strip())
        values = self.users.setdefault(user, {})
        visible = []
        for value in values.get("tag", []):
            tag, separator, timestamp = value.rpartition(":::")
            if separator:
                if float(timestamp) > date.timestamp() * 1000:
                    continue
                value = tag
            if value not in visible:
                visible.append(value)
        return PhoAuthor(user, tuple(visible))

    def _resolve_alias(self, user):
        visited = set()
        while self.users.get(user, {}).get("aliasFor"):
            if user in visited:
                raise PhoPresentationError(
                    "Cyclic PHO user alias: {}".format(user)
                )
            visited.add(user)
            source = self.users[user]
            target = source["aliasFor"]
            if source.get("tag"):
                self.users.setdefault(target, {}).setdefault(
                    "tag", []
                ).extend(source["tag"])
            user = target
        return user

    def _resolve_mentions(self, text):
        return re.sub(
            r"@([A-Za-z0-9_-]+)",
            lambda match: "@" + self._resolve_alias(match.group(1)),
            str(text),
        )

    def _apply_tag_metadata(self, user, fields, date):
        record = self.users.setdefault(user, {})
        tags = record.setdefault("tag", [])
        for field in fields:
            tag_match = re.match(r"tag:(.+)", field)
            untag_match = re.match(r"untag:(.+)", field)
            if tag_match:
                tag = tag_match.group(1)
                if not any(
                    value == tag or value.startswith(tag + ":::")
                    for value in tags
                ):
                    tags.append(
                        "{}:::{}".format(tag, date.timestamp() * 1000)
                    )
            if untag_match:
                tag = untag_match.group(1)
                record["tag"] = [
                    value for value in tags
                    if value != tag and not value.startswith(tag + ":::")
                ]
                tags = record["tag"]

    def _displace(self, reference, displacement):
        seconds = displacement.get("s")
        if seconds is None:
            seconds = int(self._random.next() * 14) + 15
        return reference + timedelta(
            seconds=seconds,
            minutes=displacement.get("m", 0),
            hours=displacement.get("h", 0),
            days=displacement.get("d", 0),
        )

    def _parse_datetime(self, value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise PhoPresentationError(
                "Invalid PHO date {!r}.".format(value)
            ) from error
        if parsed.tzinfo is None:
            try:
                parsed = parsed.replace(tzinfo=ZoneInfo(
                    self.settings.get("timeZone", "America/New_York")
                ))
            except ZoneInfoNotFoundError as error:
                raise PhoPresentationError(
                    "Unknown PHO timezone {!r}.".format(
                        self.settings.get("timeZone")
                    )
                ) from error
        return parsed

    def _timestamp(self, date):
        try:
            zone_name = self.settings.get(
                "timeZone", "America/New_York"
            )
            local = date.astimezone(ZoneInfo(zone_name))
        except ZoneInfoNotFoundError as error:
            raise PhoPresentationError(
                "Unknown PHO timezone {!r}.".format(zone_name)
            ) from error
        label = "{} {}{}, {}".format(
            local.strftime("%b"),
            local.day,
            self._number_suffix(local.day),
            local.year,
        )
        tooltip = ""
        if not self.settings.get("noabbr"):
            zone = (
                "Eastern Time"
                if zone_name == "America/New_York"
                else local.tzname()
            )
            tooltip = "{} {}".format(
                local.strftime("%m/%d/%Y, %I:%M:%S %p"),
                zone,
            )
        return PhoTimestamp(local, label, tooltip)

    def _integer_setting(self, name, default):
        try:
            return int(self.settings.get(name, default))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _number_suffix(day):
        if 11 <= day <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def _navigation(current_page, end_page):
        pages = list(range(1, min(5, end_page) + 1))
        if current_page - 1 > 6:
            pages.append(None)
        if 5 <= current_page <= end_page - 3:
            for page in (current_page - 1, current_page, current_page + 1):
                if page <= end_page and page not in pages:
                    pages.append(page)
        if current_page + 1 < end_page - 3:
            pages.append(None)
        for page in (end_page - 2, end_page - 1, end_page):
            if page > 0 and page not in pages:
                pages.append(page)
        return tuple(pages)


class PhoPresentationParser:
    """Plugin parser contract: raw PHO directives to semantic model."""

    def parse(self, source):
        try:
            page = PhoPage.parse(source)
        except PhoModelError:
            normalized = str(source or "").replace(
                "\r\n", "\n"
            ).replace("\r", "\n")
            if PhoPage.SCENE.search(normalized) is not None:
                raise
            page = PhoPage.initialize_from_markdown(normalized)
        return PhoPresentationBuilder().build(page)
