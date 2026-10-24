import re

COLLAPSE_CHARS = 480
COLLAPSE_LINES = 9
CODE_STYLE = "font-family:Consolas,monospace; background-color:#EEF0F3;"
WARNING_HINTS = ("⚠", "внимание", "осторожно", "предупрежд", "опасн", "небезопас", "не печатайте",
                 "warning", "caution", "danger", "unsafe", "do not print")

_FENCE = re.compile(r"^\s*(```|~~~)\s*([\w+#.-]*)\s*$")
_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_ITEM = re.compile(r"^(\s*)([-*•+]|\d{1,3}[.)])\s+(.*)$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")


def escape(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def inline(text):
    tokens = []

    def keep(rendered):
        tokens.append(rendered)
        return "\x00T%d\x00" % (len(tokens) - 1)

    def keep_code(match):
        return keep('<span style="%s">&nbsp;%s&nbsp;</span>' % (CODE_STYLE, escape(match.group(1))))

    def keep_link(match):
        return keep('<a href="%s">%s</a>' % (escape(match.group(2)), escape(match.group(1))))

    line = re.sub(r"`([^`\n]+)`", keep_code, str(text or ""))
    line = _LINK.sub(keep_link, line)
    line = escape(line)
    line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
    line = re.sub(r"(?<![\w*])__(.+?)__(?![\w*])", r"<b>\1</b>", line)
    line = re.sub(r"(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])", r"<i>\1</i>", line)
    line = re.sub(r"(?<![\w])_(?!\s)([^_\n]+?)_(?![\w])", r"<i>\1</i>", line)
    return re.sub("\x00T(\\d+)\x00", lambda m: tokens[int(m.group(1))], line)


def _block(kind, **fields):
    block = {"type": kind, "text": "", "level": 0, "ordered": False, "items": [], "header": [], "rows": [],
             "lang": ""}
    block.update(fields)
    return block


def _cells(line):
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|") and not line.endswith("\\|"):
        line = line[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line)]


def _is_table_start(lines, index):
    return "|" in lines[index] and index + 1 < len(lines) and bool(_TABLE_SEPARATOR.match(lines[index + 1]))


def parse_blocks(text):
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = []
    paragraph = []

    def flush():
        if paragraph:
            blocks.append(_block("paragraph", text="<br>".join(inline(p.strip()) for p in paragraph)))
            del paragraph[:]

    index = 0
    while index < len(lines):
        line = lines[index]
        fence = _FENCE.match(line)
        if fence:
            flush()
            body = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith(fence.group(1)):
                body.append(lines[index])
                index += 1
            blocks.append(_block("code", text="\n".join(body), lang=fence.group(2)))
            index += 1
            continue
        if not line.strip() or _RULE.match(line):
            flush()
            index += 1
            continue
        heading = _HEADING.match(line)
        if heading:
            flush()
            blocks.append(_block("heading", text=inline(heading.group(2)), level=len(heading.group(1))))
            index += 1
            continue
        if _is_table_start(lines, index):
            flush()
            header = _cells(line)
            rows = []
            index += 2
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                cells = _cells(lines[index])
                cells = (cells + [""] * len(header))[:len(header)]
                rows.append([inline(c) for c in cells])
                index += 1
            blocks.append(_block("table", header=[inline(h) for h in header], rows=rows))
            continue
        item = _ITEM.match(line)
        if item:
            flush()
            ordered = item.group(2)[0].isdigit()
            items = []
            while index < len(lines):
                item = _ITEM.match(lines[index])
                if item and not item.group(1) and item.group(2)[0].isdigit() != ordered:
                    break
                if item:
                    marker = item.group(2) if item.group(2)[0].isdigit() else "•"
                    items.append({"text": inline(item.group(3)), "level": min(3, len(item.group(1).expandtabs(4)) // 2),
                                  "marker": marker})
                elif lines[index].strip() and lines[index][:1] in (" ", "\t") and items:
                    items[-1]["text"] += "<br>" + inline(lines[index].strip())
                else:
                    break
                index += 1
            blocks.append(_block("list", items=items, ordered=ordered))
            continue
        paragraph.append(line[1:].lstrip() if line.lstrip().startswith(">") else line)
        index += 1
    flush()
    return blocks


def needs_attention(text):
    text = str(text or "")
    lowered = text.lower()
    if any(hint in lowered for hint in WARNING_HINTS):
        return True
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return bool(paragraphs) and "?" in paragraphs[-1]


def is_long(text):
    text = str(text or "").strip()
    return len(text) > COLLAPSE_CHARS or len([l for l in text.split("\n") if l.strip()]) > COLLAPSE_LINES


def should_collapse(text):
    return is_long(text) and not needs_attention(text)
