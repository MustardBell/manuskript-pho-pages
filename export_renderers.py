import re

from manuskript.converters.markdownToBBCode import markdown_to_bbcode
from manuskript.plugins import PageExportDocument

from .presentation import PhoPresentation


DEFAULT_STYLE = {
    "separator": "■",
    "topic_label": "♦ Topic:",
    "board_label": "In: Boards",
    "board_separator": "►",
    "reply_marker": "►",
    "welcome_title": "Welcome to the Parahumans Online message boards.",
    "showing_template": "Showing page {current} of {total}",
    "end_template": "End of Page. {navigation}",
}


class PhoExportRenderer:
    output_format = ""

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
        style = dict(DEFAULT_STYLE)
        style.update(options or {})
        return PageExportDocument(
            self.render_presentation(model, style),
            self.output_format,
        )

    def render_presentation(self, model, style):
        raise NotImplementedError

    @staticmethod
    def template(value, **fields):
        try:
            return str(value).format(**fields)
        except (KeyError, ValueError) as error:
            raise ValueError(
                "Invalid PHO renderer template {!r}: {}".format(
                    value,
                    error,
                )
            ) from error


class PhoMarkdownRenderer(PhoExportRenderer):
    """Portable PHO projection used by ordinary export pipelines."""

    output_format = "markdown"

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
        return "\n\n".join(value for value in blocks if value)

    def render_welcome(self, model, style):
        return "\n".join([
            style["separator"],
            "",
            "**{}**".format(style["welcome_title"]),
            "You are currently logged in, *{}*".format(model.reader),
            "You are viewing:",
            "- Threads you have replied to",
            "- AND Threads that have new replies",
            "- OR private message conversations with new replies",
            "- Thread OP is displayed.",
            "- Ten posts per page",
            "- Last ten messages in private message history.",
            "- Threads and private messages are ordered chronologically.",
            "",
            style["separator"],
        ])

    def render_thread(self, thread, style):
        board = " {} ".format(style["board_separator"]).join(
            [style["board_label"]] + list(thread.boards)
        )
        blocks = [
            "**{} {}**".format(style["topic_label"], thread.topic),
            "**{}**".format(board),
        ]
        if thread.original_post is not None:
            blocks.append(self.render_post(
                thread.original_post,
                style,
                quoted=False,
            ))
        for page in thread.pages:
            showing = self.template(
                style["showing_template"],
                current=page.number,
                total=page.total,
            )
            blocks.append("**({})**".format(showing))
            blocks.extend(
                self.render_post(post, style, quoted=True)
                for post in page.posts
            )
            navigation = self.navigation(page)
            blocks.append("**{}**".format(self.template(
                style["end_template"],
                current=page.number,
                total=page.total,
                navigation=navigation,
            )))
        blocks.append(style["separator"])
        return "\n\n".join(value for value in blocks if value)

    def render_post(self, post, style, quoted):
        marker = style["reply_marker"] if not post.original else ""
        tags = "".join(" ({})".format(tag) for tag in post.author.tags)
        verb = "Posted" if post.original else "Replied"
        values = [
            "**{}{}**{}".format(marker, post.author.name, tags),
            "{} on {}:".format(verb, post.timestamp.label),
            self.markdown_body(post.body_markdown),
        ]
        content = "\n\n".join(value for value in values if value)
        if not quoted:
            return content
        return "\n".join(
            ">" if not line else "> " + line
            for line in content.splitlines()
        )

    @staticmethod
    def markdown_body(value):
        return re.sub(
            r"(?m)^@([^\n>]+)>(.+)$",
            lambda match: "> **{} said:** {}".format(
                match.group(1).strip(),
                match.group(2),
            ),
            value.strip(),
        )

    @staticmethod
    def navigation(page):
        return ", ".join(
            "..." if value is None else str(value)
            for value in page.navigation
        )


class PhoBBCodeRenderer(PhoExportRenderer):
    """Direct PHO→BBCode renderer with forum-specific safety rules."""

    output_format = "bbcode"

    def render_presentation(self, model, style):
        blocks = []
        if model.prefix_markdown.strip():
            blocks.append(markdown_to_bbcode(
                model.prefix_markdown.strip("\n")
            ))
        if model.show_welcome:
            blocks.append(self.render_welcome(model, style))
        blocks.extend(
            self.render_thread(thread, style) for thread in model.threads
        )
        if model.suffix_markdown.strip():
            blocks.append(markdown_to_bbcode(
                model.suffix_markdown.strip("\n")
            ))
        return "\n\n".join(value for value in blocks if value)

    def render_welcome(self, model, style):
        return "\n".join([
            self.separator(style),
            "",
            "[b]{}[/b]".format(style["welcome_title"]),
            "You are currently logged in, [u]{}[/u]".format(
                model.reader
            ),
            "You are viewing:",
            "• Threads you have replied to",
            "• AND Threads that have new replies",
            "• OR private message conversations with new replies",
            "• Thread OP is displayed.",
            "• Ten posts per page",
            "• Last ten messages in private message history.",
            "• Threads and private messages are ordered chronologically.",
            self.separator(style),
        ])

    def render_thread(self, thread, style):
        board = " {} ".format(style["board_separator"]).join(
            [style["board_label"]] + list(thread.boards)
        )
        blocks = [
            "[b]{} {}[/b]".format(style["topic_label"], thread.topic),
            "[b]{}[/b]".format(board),
        ]
        if thread.original_post is not None:
            blocks.append(self.render_post(thread.original_post, style))
        for page in thread.pages:
            showing = self.template(
                style["showing_template"],
                current=page.number,
                total=page.total,
            )
            posts = "\n\n".join(
                self.render_post(post, style) for post in page.posts
            )
            blocks.append(
                "[b]({})[/b][indent]\n{}\n[/indent]".format(
                    showing,
                    posts,
                )
            )
            navigation = self.navigation(page)
            blocks.append("[b]{}[/b]".format(self.template(
                style["end_template"],
                current=page.number,
                total=page.total,
                navigation=navigation,
            )))
        blocks.append(self.separator(style))
        return "\n".join(value for value in blocks if value)

    def render_post(self, post, style):
        marker = style["reply_marker"] if not post.original else ""
        tags = "".join(" ({}) ".format(tag) for tag in post.author.tags)
        verb = "Posted" if post.original else "Replied"
        return "\n".join([
            "[b]{}{} [/b]{}".format(marker, post.author.name, tags),
            "{} {}:".format(verb, self.timestamp(post.timestamp)),
            self.bbcode_body(post.body_markdown),
        ])

    @staticmethod
    def timestamp(value):
        if not value.tooltip:
            return "on {}".format(value.label)
        tooltip = value.tooltip.replace('"', "&quot;")
        return 'on [abbr="{}"]{}[/abbr]'.format(
            tooltip,
            value.label,
        )

    @staticmethod
    def bbcode_body(value):
        value = re.sub(
            r"(?m)^@([^\n>]+)>(.+)$",
            lambda match: (
                '\n[fieldset title="{} said:"]{}[/fieldset]'.format(
                    match.group(1).strip().replace('"', "&quot;"),
                    match.group(2),
                )
            ),
            value.strip(),
        )
        return markdown_to_bbcode(value).replace(
            "@", "[plain]@[/plain]"
        )

    @staticmethod
    def separator(style):
        return "[CENTER]{}[/CENTER]".format(style["separator"])

    @staticmethod
    def navigation(page):
        values = []
        for value in page.navigation:
            if value is None:
                values.append("...")
            elif value == page.number:
                values.append(str(value))
            else:
                values.append("[u]{}[/u]".format(value))
        return ", ".join(values)
