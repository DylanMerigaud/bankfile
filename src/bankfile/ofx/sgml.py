"""The OFX tag reader: one algorithm for the SGML bodies of 1.x and the XML bodies of 2.x.

OFX 1.x is SGML with omitted end tags, so syntax alone never tells you whether `<X>` opens a
leaf or an aggregate. The reader applies the standard minimisation rule instead of guessing from
a list of known tags: an end tag closes everything still open above it, and a start tag closes
the element on top when that element already has a value. A fully closed XML body is the same
algorithm with nothing left to infer, which is why 1.x and 2.x produce the same tree here and
`tests/test_ofx_sgml.py` asserts exactly that on two spellings of the same statement.

There is no tag list in this module, on purpose. A reader that walks a known structure shifts
its fields the day a bank inserts `VALUEDATE` between two standard ones, and both parsers
measured for this corpus drop those vendor values without a word. Knowing which tags matter is
the caller's job; keeping every one of them is this module's.

Character references are resolved, because `&amp;` is how both OFX 1.x (specification section
"Special Characters", which names `&amp;`, `&lt;`, `&gt;` and `&nbsp;`) and OFX 2.x (XML) write
a literal `&`. Handing `SMITH &amp; SONS` back as-is would be a wrong value with no warning
attached to it, which section 0 of the reading rules calls the worst failure this project can
produce. An entity we do not know stays verbatim: we never invent a character.

One case the minimisation rule cannot decide, and no reader can: an element left empty AND left
unclosed (`<CURDEF>` on its own line, with no `</CURDEF>`) is indistinguishable from an
aggregate, so the elements that follow become its children. Nothing is lost, and `find` is
depth first for that reason: a caller looking for `BANKACCTFROM` still finds it wherever the
ambiguity put it.

Known limit, left alone deliberately: an attribute value containing `>` (`<TAG a="x>y">`) ends
the tag early. OFX carries its data in elements, not in attributes, and no fixture in the corpus
has one, so the regex stays readable instead of covering a case the format does not use.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field

from bankfile.model import ReadWarning

# The synthetic root. It starts with a character no tag name can start with, so it can never
# collide with an element read from a file.
ROOT_TAG = "#DOCUMENT"

_TOKEN = re.compile(
    r"""
      <!\[CDATA\[(?P<cdata>.*?)\]\]>                    # a CDATA section, its text is data
    | <!--.*?-->                                        # a comment
    | <[?!][^>]*>                                       # <?xml ...?>, <?OFX ...?>, <!DOCTYPE ...>
    | </(?P<close>[A-Za-z_][\w.:-]*)\s*>                # an end tag
    | <(?P<open>[A-Za-z_][\w.:-]*)[^<>]*?(?P<empty>/?)\s*>   # a start or empty element tag
    """,
    re.DOTALL | re.VERBOSE,
)

# No whitespace is allowed between `<` and the tag name, as in XML and SGML both. Accepting
# `< B >` as a start tag would turn the memo `PAID < B > NOW` into a phantom element and cut the
# value in two, and a bank file is far more likely to contain an unescaped comparison sign than
# a tag written with a space in front of its name.

_ENTITY = re.compile(
    r"&(?:#(?P<dec>\d+)|#[xX](?P<hex>[0-9A-Fa-f]+)|(?P<name>[A-Za-z][A-Za-z0-9]*));"
)
# The four the OFX 1.x specification names, plus the two extra ones XML predefines for 2.x.
_NAMED_ENTITIES = {
    "amp": "&",
    "lt": "<",
    "gt": ">",
    "quot": '"',
    "apos": "'",
    # Written as an escape: a literal U+00A0 in the source is invisible in a diff.
    "nbsp": "\u00a0",
}


@dataclass(frozen=True, slots=True)
class Node:
    """One element. A leaf carries a value, an aggregate carries children, never both.

    Immutable: a tree that can be edited after the fact is a tree whose provenance nobody can
    reconstruct when a figure turns out wrong.
    """

    tag: str
    # None means the element was absent, present and empty, or self-closed. Reading rules,
    # section 4: an empty tag means ABSENT, and never the empty string, because "" and "the
    # bank sent nothing" are two different facts and only one of them is worth investigating.
    value: str | None = None
    children: tuple[Node, ...] = ()

    def find(self, tag: str) -> Node | None:
        """The first descendant carrying this tag, depth first, or None."""
        wanted = tag.upper()
        return next((node for node in self._descendants() if node.tag == wanted), None)

    def find_all(self, tag: str, *, stop_at: frozenset[str] = frozenset()) -> list[Node]:
        """Every descendant carrying this tag, in document order.

        `stop_at` names tags the walk must not enter. It exists because of a real defect: OFX
        1.x lets an aggregate omit its end tag, so a file with two statements and no
        `</STMTRS>` nests the second inside the first. Searching descendants then hands the
        second account's entries to the first, stamped with the first account's currency, which
        is a wrong amount under a wrong account, the exact failure this library exists to
        prevent.
        """
        wanted = tag.upper()
        return [node for node in self._descendants(stop_at=stop_at) if node.tag == wanted]

    def child(self, tag: str) -> Node | None:
        """The first DIRECT child carrying this tag.

        Used wherever a field belongs to one element and must not be borrowed from a nested
        one: a transaction inside a transaction would otherwise lend its amount to its parent.
        """
        wanted = tag.upper()
        return next((node for node in self.children if node.tag == wanted), None)

    def child_text(self, tag: str) -> str | None:
        found = self.child(tag)
        return found.value if found is not None else None

    def text(self, tag: str) -> str | None:
        """The value of the first descendant carrying this tag, or None if there is none."""
        found = self.find(tag)
        return found.value if found is not None else None

    def _descendants(self, *, stop_at: frozenset[str] = frozenset()) -> Iterator[Node]:
        # Iterative, like _freeze and for the same reason: a corrupt file nests as deep as it
        # likes, and a lookup that answers RecursionError is a lookup that failed.
        stack = list(reversed(self.children))
        while stack:
            node = stack.pop()
            yield node
            if node.tag not in stop_at:
                stack.extend(reversed(node.children))


@dataclass(slots=True)
class _Open:
    """An element while it is being built. `Node` is frozen, so the tree is assembled here and
    frozen once at the end."""

    tag: str
    # The text runs of this element, in document order, joined and stripped only once the
    # element is frozen. Stripping each run on its own would glue `PRICE ` and ` DROP` into
    # `PRICEDROP` when a comment or a stray end tag falls between them.
    texts: list[str] = field(default_factory=list)
    children: list[_Open] = field(default_factory=list)


def parse_tags(body: str) -> tuple[Node, list[ReadWarning]]:
    """Read `body`, the decoded document from its first `<` onward, into a tree.

    Never raises. Everything it cannot place comes back as a warning carrying the raw text.
    """
    warnings: list[ReadWarning] = []
    stack = [_Open(ROOT_TAG)]
    position = 0
    element_seen = False

    for match in _TOKEN.finditer(body):
        _absorb_text(stack, body[position : match.start()], warnings)
        position = match.end()
        cdata = match.group("cdata")
        end_tag = match.group("close")
        start_tag = match.group("open")
        if cdata is not None:
            # Its whole point is to hold characters that would otherwise be markup, so it is
            # data, taken literally, with no entity to resolve inside it.
            _absorb_text(stack, cdata, warnings, literal=True)
        elif end_tag is not None:
            _close(stack, end_tag.upper(), warnings)
        elif start_tag is not None:
            element_seen = True
            _open(stack, start_tag.upper())
            if match.group("empty"):
                # `<X/>` is an empty leaf, exactly as if it were `<X></X>`. Normalising it here,
                # in the tokenising pass, is what keeps it away from the value rules downstream.
                stack.pop()
        # Anything else matched is a comment or a processing instruction: not part of the tree.

    _absorb_text(stack, body[position:], warnings)

    if len(stack) > 1:
        chain = " > ".join(node.tag for node in stack[1:])
        warnings.append(
            ReadWarning(
                rule="tag",
                field=stack[1].tag,
                value=None,
                message=f"document ends with tags still open, closed implicitly: {chain}",
            )
        )
    if not element_seen:
        warnings.append(
            ReadWarning(rule="tag", field=None, value=None, message="no tag found in the document")
        )

    return _freeze(stack[0]), warnings


def _unescape(raw: str) -> str:
    """Resolve the character references a bank actually writes, and only those.

    An entity we do not know (`&foo;`) is left exactly as it came: reading rules section 0,
    never an invented value. A single pass, so `&amp;lt;` yields the text `&lt;` and not `<`.
    """
    if "&" not in raw:
        return raw

    def resolve(match: re.Match[str]) -> str:
        decimal = match.group("dec")
        hexadecimal = match.group("hex")
        try:
            if decimal is not None:
                return chr(int(decimal))
            if hexadecimal is not None:
                return chr(int(hexadecimal, 16))
        except (ValueError, OverflowError):
            # A code point outside Unicode. `chr` answers ValueError past U+10FFFF and
            # OverflowError once the integer no longer fits a C int, and both are the same
            # event here. Keeping the reference verbatim beats raising, and beats substituting
            # a replacement character nobody asked for.
            return match.group(0)
        # Case insensitive because OFX 1.x files are written in upper case throughout, and
        # `&AMP;` from such a file means the same character as `&amp;`.
        return _NAMED_ENTITIES.get(match.group("name").lower(), match.group(0))

    return _ENTITY.sub(resolve, raw)


def _absorb_text(
    stack: list[_Open], raw: str, warnings: list[ReadWarning], *, literal: bool = False
) -> None:
    """Attach a run of text to the element it belongs to.

    Whitespace between two tags is layout, not a value: counting it would give every aggregate
    of an SGML file a value and close it at its first child.
    """
    text = raw if literal else _unescape(raw)
    if not text.strip():
        return
    holder = stack[-1]
    if len(stack) == 1 or holder.children:
        where = (
            "outside any tag"
            if len(stack) == 1
            else f"between the children of {holder.tag}, which is an aggregate"
        )
        warnings.append(
            ReadWarning(
                rule="tag",
                field=None if len(stack) == 1 else holder.tag,
                value=text.strip(),
                message=f"text {where}, kept here and left out of the tree",
            )
        )
        return
    holder.texts.append(text)


def _open(stack: list[_Open], tag: str) -> None:
    if stack[-1].texts:
        # The element on top already had its text, so it was a leaf whose end tag was omitted.
        stack.pop()
    node = _Open(tag)
    stack[-1].children.append(node)
    stack.append(node)


def _close(stack: list[_Open], tag: str, warnings: list[ReadWarning]) -> None:
    for depth in range(len(stack) - 1, 0, -1):
        if stack[depth].tag == tag:
            # Everything above it is a leaf whose end tag the file omitted, which is the normal
            # SGML case and not worth a warning: it would fire on every line of every 1.x file.
            del stack[depth:]
            return
    warnings.append(
        ReadWarning(
            rule="tag",
            field=tag,
            value=None,
            message=f"end tag </{tag}> has no start tag still open, ignored",
        )
    )


def _freeze(root: _Open) -> Node:
    """Turn the mutable tree into the immutable one, without recursion.

    A corrupt file nests as deep as it likes (under the minimisation rule every empty unclosed
    leaf costs one level), and a recursive walk answers RecursionError somewhere past a thousand
    of them. Section 0 leaves no room for that: malformed input never raises.
    """
    order: list[_Open] = []
    pending = [root]
    while pending:
        node = pending.pop()
        order.append(node)
        pending.extend(node.children)

    # Keyed by identity, which is safe here because `order` holds a reference to every node for
    # the whole loop, so no id can be reused by a new object.
    frozen: dict[int, Node] = {}
    for node in reversed(order):
        frozen[id(node)] = Node(
            tag=node.tag,
            value="".join(node.texts).strip() or None,
            children=tuple(frozen[id(child)] for child in node.children),
        )
    return frozen[id(root)]
