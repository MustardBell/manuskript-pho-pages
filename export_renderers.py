import re

from manuskript.plugins import BBCODE, MARKDOWN, PageExportDocument

from .presentation import PhoPresentation


COMMON_STYLE = {
    "separator": "■",
    "default_reader": "Reader",
    "default_topic": "A question",
    "welcome_title": (
        "Welcome to the Parahumans Online message boards."
    ),
    "logged_in_template": "You are currently logged in, {reader}",
    "viewing_title": "You are viewing:",
    "viewing_replied_threads": "Threads you have replied to",
    "viewing_new_replies": "AND Threads that have new replies",
    "viewing_private_replies": (
        "OR private message conversations with new replies"
    ),
    "viewing_original_post": "Thread OP is displayed.",
    "viewing_posts_per_page": "{posts} posts per page",
    "viewing_private_messages": (
        "Last {messages} messages in private message history."
    ),
    "viewing_chronological": (
        "Threads and private messages are ordered chronologically."
    ),
    "topic_label": "♦ Topic:",
    "topic_template": "{label} {topic}",
    "board_label": "In: Boards",
    "board_separator": "►",
    "board_template": "{boards}",
    "reply_marker": "►",
    "original_poster_label": "Original Poster",
    "posted_label": "Posted",
    "replied_label": "Replied",
    "on_label": "on",
    "said_template": "{author} said",
    "date_template": "{source_label}",
    "tooltip_template": "{source_tooltip}",
    "showing_template": "Showing page {current} of {total}",
    "end_template": "End of Page. {navigation}",
    "navigation_separator": ", ",
    "navigation_ellipsis": "...",
}


MARKDOWN_STYLE = {
    **COMMON_STYLE,
    "document_separator": r"\n\n",
    "block_separator": r"\n\n",
    "post_separator": r"\n\n",
    "separator_template": "{separator}",
    "welcome_container_template": (
        r"{separator}\n\n{title}\n{logged_in}\n{viewing_title}"
        r"\n{items}\n\n{separator}"
    ),
    "welcome_title_template": "**{content}**",
    "reader_template": "*{content}*",
    "welcome_item_template": "- {content}",
    "thread_heading_template": "**{content}**",
    "thread_container_template": (
        r"{headings}\n\n{posts}\n\n{separator}"
    ),
    "author_template": "**{marker}{author}**{tags}",
    "tag_template": " ({tag})",
    "post_meta_template": "{verb} {on} {timestamp}:",
    "timestamp_template": "{label}",
    "timestamp_without_tooltip_template": "{label}",
    "quote_template": "> **{attribution}:** {body}",
    "mention_template": "@",
    "reply_quote_marker": ">",
    "reply_line_template": "{marker}{space}{content}",
    "page_heading_template": "**({content})**",
    "page_container_template": r"{heading}\n\n{posts}",
    "page_end_template": "**{content}**",
    "navigation_current_template": "{page}",
    "navigation_link_template": "{page}",
}


BBCODE_STYLE = {
    **COMMON_STYLE,
    "document_separator": r"\n\n",
    "block_separator": r"\n",
    "post_separator": r"\n",
    "separator_template": "[CENTER]{separator}[/CENTER]",
    "welcome_container_template": (
        r"{separator}\n\n{title}\n{logged_in}\n{viewing_title}"
        r"\n{items}\n{separator}"
    ),
    "welcome_title_template": "[b]{content}[/b]",
    "reader_template": "[u]{content}[/u]",
    "welcome_item_template": "• {content}",
    "thread_heading_template": "[b]{content}[/b]",
    "thread_container_template": (
        r"{headings}\n{posts}\n{separator}"
    ),
    "author_template": "[b]{marker}{author} [/b]{tags}",
    "tag_template": " ({tag}) ",
    "post_meta_template": "{verb} {on} {timestamp}:",
    "timestamp_template": (
        '[abbr="{tooltip_attribute}"]{label}[/abbr]'
    ),
    "timestamp_without_tooltip_template": "{label}",
    "quote_template": (
        r'\n[fieldset title="{attribution_attribute}:"]'
        r"{body}[/fieldset]"
    ),
    "mention_template": "[plain]@[/plain]",
    "reply_quote_marker": "",
    "reply_line_template": "{content}",
    "page_heading_template": "[b]({content})[/b]",
    "page_container_template": (
        r"{heading}[indent]\n{posts}\n[/indent]"
    ),
    "page_end_template": "[b]{content}[/b]",
    "navigation_current_template": "{page}",
    "navigation_link_template": "[u]{page}[/u]",
}


class PhoExportRenderer:
    output_format = ""
    default_style = COMMON_STYLE

    def render(self, model, target_format, options):
        if not isinstance(model, PhoPresentation):
            raise TypeError(
                "PHO export renderers require PhoPresentation models."
            )
        if target_format not in (self.output_format, ""):
            raise ValueError(
                "{} cannot render PHO as {}.".format(
                    type(self).__name__,
                    target_format,
                )
            )
        style = dict(self.default_style)
        style.update(options or {})
        return PageExportDocument(
            self.render_presentation(model, style),
            self.output_format,
        )

    def render_presentation(self, model, style):
        raise NotImplementedError

    @classmethod
    def template(cls, value, **fields):
        value = cls.control_text(value)
        try:
            return value.format(**fields)
        except (KeyError, ValueError) as error:
            raise ValueError(
                "Invalid PHO renderer template {!r}: {}".format(
                    value,
                    error,
                )
            ) from error

    @staticmethod
    def control_text(value):
        return str(value).replace(r"\n", "\n").replace(r"\t", "\t")

    def separator(self, style):
        return self.template(
            style["separator_template"],
            separator=style["separator"],
        )

    def render_welcome(self, model, style):
        reader_name = model.reader or style["default_reader"]
        reader = self.template(
            style["reader_template"],
            content=reader_name,
            reader=reader_name,
        )
        logged_in = self.template(
            style["logged_in_template"],
            reader=reader,
            reader_name=reader_name,
        )
        title = self.template(
            style["welcome_title_template"],
            content=style["welcome_title"],
        )
        item_values = (
            self.template(style["viewing_replied_threads"]),
            self.template(style["viewing_new_replies"]),
            self.template(style["viewing_private_replies"]),
            self.template(style["viewing_original_post"]),
            self.template(
                style["viewing_posts_per_page"],
                posts=model.posts_per_page,
            ),
            self.template(
                style["viewing_private_messages"],
                messages=model.private_messages,
            ),
            self.template(style["viewing_chronological"]),
        )
        items = "\n".join(
            self.template(
                style["welcome_item_template"],
                content=value,
            )
            for value in item_values
            if value
        )
        separator = self.separator(style)
        return self.template(
            style["welcome_container_template"],
            separator=separator,
            title=title,
            logged_in=logged_in,
            viewing_title=style["viewing_title"],
            items=items,
        )

    def thread_headings(self, thread, style):
        topic = thread.topic or style["default_topic"]
        topic = self.template(
            style["topic_template"],
            label=style["topic_label"],
            topic=topic,
        )
        board_path = " {} ".format(style["board_separator"]).join(
            [style["board_label"]] + list(thread.boards)
        )
        board = self.template(
            style["board_template"],
            label=style["board_label"],
            boards=board_path,
        ).rstrip()
        return "\n".join(
            self.template(
                style["thread_heading_template"],
                content=value,
            )
            for value in (topic, board)
            if value
        )

    def author_tags(self, post, style):
        tags = list(post.author.tags)
        original_label = str(style["original_poster_label"]).strip()
        if post.original and original_label:
            tags.insert(0, original_label)
        visible = []
        for tag in tags:
            if tag and tag not in visible:
                visible.append(tag)
        return "".join(
            self.template(style["tag_template"], tag=tag)
            for tag in visible
        )

    def render_post_fields(self, post, style):
        marker = style["reply_marker"] if not post.original else ""
        author = self.template(
            style["author_template"],
            marker=marker,
            author=post.author.name,
            tags=self.author_tags(post, style),
            original=post.original,
        )
        verb = (
            style["posted_label"]
            if post.original
            else style["replied_label"]
        )
        timestamp = self.render_timestamp(post.timestamp, style)
        metadata = self.template(
            style["post_meta_template"],
            verb=verb,
            on=style["on_label"],
            timestamp=timestamp,
            author=post.author.name,
            original=post.original,
        )
        return author, metadata

    def render_timestamp(self, timestamp, style):
        fields = self.timestamp_fields(timestamp)
        label = self.template(style["date_template"], **fields)
        fields["label"] = label
        tooltip = ""
        if timestamp.tooltip:
            tooltip = self.template(style["tooltip_template"], **fields)
        fields["tooltip"] = tooltip
        fields["tooltip_attribute"] = self.attribute_text(tooltip)
        template = (
            style["timestamp_template"]
            if tooltip
            else style["timestamp_without_tooltip_template"]
        )
        return self.template(template, **fields)

    @staticmethod
    def timestamp_fields(timestamp):
        value = timestamp.value
        day = value.day
        return {
            "source_label": timestamp.label,
            "source_tooltip": timestamp.tooltip,
            "iso": value.isoformat(),
            "year": value.year,
            "month": value.month,
            "month_padded": value.strftime("%m"),
            "month_short": value.strftime("%b"),
            "month_long": value.strftime("%B"),
            "day": day,
            "day_padded": value.strftime("%d"),
            "ordinal": PhoExportRenderer.number_suffix(day),
            "hour_12": value.strftime("%I"),
            "hour_24": value.strftime("%H"),
            "minute": value.strftime("%M"),
            "second": value.strftime("%S"),
            "am_pm": value.strftime("%p"),
            "zone": value.tzname() or "",
        }

    @staticmethod
    def number_suffix(day):
        if 11 <= day <= 13:
            return "th"
        return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    @staticmethod
    def attribute_text(value):
        return str(value).replace('"', "&quot;")

    def navigation(self, page, style):
        values = []
        for value in page.navigation:
            if value is None:
                values.append(style["navigation_ellipsis"])
                continue
            template = (
                style["navigation_current_template"]
                if value == page.number
                else style["navigation_link_template"]
            )
            values.append(self.template(template, page=value))
        return self.control_text(style["navigation_separator"]).join(
            values
        )


class PhoMarkdownRenderer(PhoExportRenderer):
    """Portable PHO projection used by ordinary export pipelines."""

    output_format = MARKDOWN
    default_style = MARKDOWN_STYLE

    def render_presentation(self, model, style):
        blocks = []
        if model.prefix_markdown.strip():
            blocks.append(model.prefix_markdown.strip("\n"))
        if model.show_welcome:
            blocks.append(self.render_welcome(model, style))
        blocks.extend(
            self.render_thread(thread, style) for thread in model.threads
        )
        if model.suffix_markdown.strip():
            blocks.append(model.suffix_markdown.strip("\n"))
        separator = self.control_text(style["document_separator"])
        return separator.join(value for value in blocks if value)

    def render_thread(self, thread, style):
        posts = []
        if thread.original_post is not None:
            posts.append(self.render_post(
                thread.original_post,
                style,
                quoted=False,
            ))
        posts.extend(self.render_page(page, style) for page in thread.pages)
        return self.template(
            style["thread_container_template"],
            headings=self.thread_headings(thread, style),
            posts=self.control_text(style["block_separator"]).join(
                value for value in posts if value
            ),
            separator=self.separator(style),
        )

    def render_page(self, page, style):
        showing = self.template(
            style["showing_template"],
            current=page.number,
            total=page.total,
        )
        heading = self.template(
            style["page_heading_template"],
            content=showing,
            current=page.number,
            total=page.total,
        )
        posts = self.control_text(style["block_separator"]).join(
            self.render_post(post, style, quoted=True)
            for post in page.posts
        )
        container = self.template(
            style["page_container_template"],
            heading=heading,
            posts=posts,
            current=page.number,
            total=page.total,
        )
        navigation = self.navigation(page, style)
        ending = self.template(
            style["end_template"],
            current=page.number,
            total=page.total,
            navigation=navigation,
        )
        ending = self.template(
            style["page_end_template"],
            content=ending,
            current=page.number,
            total=page.total,
            navigation=navigation,
        )
        return self.control_text(style["block_separator"]).join(
            (container, ending)
        )

    def render_post(self, post, style, quoted):
        author, metadata = self.render_post_fields(post, style)
        body = self.markdown_body(post.body_markdown, style)
        content = self.control_text(style["post_separator"]).join(
            value for value in (author, metadata, body) if value
        )
        if not quoted:
            return content
        marker = style["reply_quote_marker"]
        return "\n".join(
            self.template(
                style["reply_line_template"],
                marker=marker,
                space=" " if line and marker else "",
                content=line,
            )
            for line in content.splitlines()
        )

    def markdown_body(self, value, style):
        value = re.sub(
            r"(?m)^@([^\n>]+)>(.+)$",
            lambda match: self.template(
                style["quote_template"],
                author=match.group(1).strip(),
                attribution=self.template(
                    style["said_template"],
                    author=match.group(1).strip(),
                ),
                attribution_attribute=self.attribute_text(
                    self.template(
                        style["said_template"],
                        author=match.group(1).strip(),
                    )
                ),
                body=match.group(2),
            ),
            value.strip(),
        )
        mention = style["mention_template"]
        return value if mention == "@" else value.replace("@", mention)


class PhoBBCodeRenderer(PhoExportRenderer):
    """Direct PHO→BBCode renderer with forum-specific safety rules."""

    output_format = BBCODE
    default_style = BBCODE_STYLE

    def __init__(self, markup):
        """``markup`` converts Markdown to BBCode.

        Supplied by the host through the markup.bbcode capability rather
        than imported, so this plugin depends on the published surface only.
        """
        self.markup = markup

    def render_presentation(self, model, style):
        blocks = []
        if model.prefix_markdown.strip():
            blocks.append(self.markup.convert(
                model.prefix_markdown.strip("\n")
            ))
        if model.show_welcome:
            blocks.append(self.render_welcome(model, style))
        blocks.extend(
            self.render_thread(thread, style) for thread in model.threads
        )
        if model.suffix_markdown.strip():
            blocks.append(self.markup.convert(
                model.suffix_markdown.strip("\n")
            ))
        separator = self.control_text(style["document_separator"])
        return separator.join(value for value in blocks if value)

    def render_thread(self, thread, style):
        posts = []
        if thread.original_post is not None:
            posts.append(self.render_post(thread.original_post, style))
        posts.extend(self.render_page(page, style) for page in thread.pages)
        return self.template(
            style["thread_container_template"],
            headings=self.thread_headings(thread, style),
            posts=self.control_text(style["block_separator"]).join(
                value for value in posts if value
            ),
            separator=self.separator(style),
        )

    def render_page(self, page, style):
        showing = self.template(
            style["showing_template"],
            current=page.number,
            total=page.total,
        )
        heading = self.template(
            style["page_heading_template"],
            content=showing,
            current=page.number,
            total=page.total,
        )
        posts = self.control_text(style["block_separator"]).join(
            self.render_post(post, style) for post in page.posts
        )
        container = self.template(
            style["page_container_template"],
            heading=heading,
            posts=posts,
            current=page.number,
            total=page.total,
        )
        navigation = self.navigation(page, style)
        ending = self.template(
            style["end_template"],
            current=page.number,
            total=page.total,
            navigation=navigation,
        )
        ending = self.template(
            style["page_end_template"],
            content=ending,
            current=page.number,
            total=page.total,
            navigation=navigation,
        )
        return self.control_text(style["block_separator"]).join(
            (container, ending)
        )

    def render_post(self, post, style):
        author, metadata = self.render_post_fields(post, style)
        body = self.bbcode_body(post.body_markdown, style)
        return self.control_text(style["post_separator"]).join(
            value for value in (author, metadata, body) if value
        )

    def bbcode_body(self, value, style):
        value = re.sub(
            r"(?m)^@([^\n>]+)>(.+)$",
            lambda match: self.template(
                style["quote_template"],
                author=match.group(1).strip(),
                attribution=self.template(
                    style["said_template"],
                    author=match.group(1).strip(),
                ),
                attribution_attribute=self.attribute_text(
                    self.template(
                        style["said_template"],
                        author=match.group(1).strip(),
                    )
                ),
                body=match.group(2),
            ),
            value.strip(),
        )
        # The mention template is a per-render style value, so this stays a
        # post-pass rather than a converter rule.
        return self.markup.convert(value).replace(
            "@", style["mention_template"]
        )
