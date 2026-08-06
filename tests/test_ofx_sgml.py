"""The tag reader, tested on the real fixtures of the corpus.

Every test here names the file it reads and asserts on values taken from that file. The two
constructs the corpus proves are dangerous, a vendor tag sitting between two standard ones and
an empty element written `<MEMO/>`, are checked by what comes AFTER them: that is where a
reader that mishandles them does its damage, and where a measured parser already loses a whole
statement today.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bankfile.ofx.sgml import ROOT_TAG, Node, parse_tags

CORPUS = Path(__file__).resolve().parent.parent / "corpus"

# EVERY OFX and QFX file of the corpus, not a hand-picked few: the reader has no tag list, so
# any of them can expose a construct the others do not, and a sweep that skips a bank is a
# sweep that will not notice the day that bank's file stops reading.
EVERY_OFX_FILE = sorted(
    path.relative_to(CORPUS).as_posix()
    for path in CORPUS.rglob("*")
    if path.suffix.lower() in {".ofx", ".qfx"}
)


def body_of(relative: str) -> str:
    """Hand `parse_tags` what the reader will hand it: the text from the first `<` onward.

    Picking the codec is `bankfile.ofx.header`'s job, not this module's, so the fallback here is
    deliberately crude. cp1252 cannot fail on a byte, so it always yields something to parse,
    and it keeps the tag reader testable without the header reader.
    """
    raw = (CORPUS / relative).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")
    return text[text.index("<") :]


def child(node: Node, tag: str) -> Node:
    """`find` returns None when a tag is absent, which every test below would then have to
    re-check by hand. Failing here instead keeps the assertion that matters readable."""
    found = node.find(tag)
    assert found is not None, f"{tag} is missing from the tree"
    return found


def every_node(node: Node) -> list[Node]:
    out = [node]
    for kid in node.children:
        out.extend(every_node(kid))
    return out


def paths(node: Node, prefix: str = "") -> list[tuple[str, str | None]]:
    """The whole tree flattened to (path, value) pairs, in document order."""
    out: list[tuple[str, str | None]] = []
    for kid in node.children:
        path = f"{prefix}/{kid.tag}"
        out.append((path, kid.value))
        out.extend(paths(kid, path))
    return out


def test_the_standard_fields_after_a_vendor_tag_are_not_shifted() -> None:
    """`unnamed-bank/tags-outside-spec.ofx`: four tags the OFX 1.0.2 specification does not
    define for STMTTRN sit between FITID and MEMO. The point of the fixture is what follows
    them, and that ACCTBAL never reaches an amount field."""
    root, warnings = parse_tags(body_of("banks/unnamed-bank/tags-outside-spec.ofx"))
    txn = child(root, "STMTTRN")

    assert [kid.tag for kid in txn.children] == [
        "TRNTYPE",
        "DTPOSTED",
        "TRNAMT",
        "FITID",
        "VALUEDATE",
        "NAME",
        "TRANSACTIONSPLIT",
        "CATEGORY",
        "ACCTBAL",
        "MEMO",
    ]
    assert txn.text("TRNAMT") == "-10.00"
    assert txn.text("NAME") == "ANON MERCHANT"
    assert txn.text("MEMO") == "ANON MEMO"
    # The four vendor values come back out under their own names instead of being dropped,
    # which is what both measured parsers do with them.
    assert txn.text("VALUEDATE") == "20260115"
    assert txn.text("TRANSACTIONSPLIT") == "No"
    assert txn.text("CATEGORY") == "Uncategorised"
    assert txn.text("ACCTBAL") == "-400.52"
    assert warnings == []


def test_a_self_closing_tag_does_not_cost_the_balance_that_follows_it() -> None:
    """`onpoint-community-credit-union/self-closing-memo-tag.ofx`: ofxtools 1.1.1 answers
    `Can't set STMTRS.ledgerbal to None` on this file, so one empty memo costs it the whole
    statement. The balance is in the file, it must be in the tree."""
    root, warnings = parse_tags(
        body_of("banks/onpoint-community-credit-union/self-closing-memo-tag.ofx")
    )

    memo = child(root, "MEMO")
    assert memo.value is None
    assert memo.children == ()

    stmtrs = child(root, "STMTRS")
    assert [kid.tag for kid in stmtrs.children] == [
        "CURDEF",
        "BANKACCTFROM",
        "BANKTRANLIST",
        "LEDGERBAL",
        "AVAILBAL",
    ]
    ledgerbal = child(root, "LEDGERBAL")
    assert ledgerbal.text("BALAMT") == "90.00"
    assert ledgerbal.text("DTASOF") == "20260131"
    assert warnings == []


def test_a_tag_that_is_present_but_empty_reads_as_absent() -> None:
    """`unnamed-bank/empty-tags-curdef-fitid-name.ofx`: an empty element is None, never the
    empty string, and never a crash. ofxparse 0.21 raises IndexError on this file."""
    root, warnings = parse_tags(body_of("banks/unnamed-bank/empty-tags-curdef-fitid-name.ofx"))

    assert child(root, "CURDEF").value is None
    txn = child(root, "STMTTRN")
    assert child(txn, "FITID").value is None
    assert child(txn, "NAME").value is None
    # The field after the two empty ones, read at its own name.
    assert txn.text("MEMO") == "ANON MEMO"
    assert [kid.tag for kid in txn.children] == [
        "TRNTYPE",
        "DTPOSTED",
        "TRNAMT",
        "FITID",
        "NAME",
        "MEMO",
    ]
    assert warnings == []


def test_an_explicit_end_tag_in_an_sgml_body_stays_out_of_the_value() -> None:
    """`unnamed-bank/mixed-case-trntype.ofx`: one element is closed explicitly in a body whose
    other elements are not. The value keeps its case, since folding it belongs to whoever looks
    the enumeration up, not to the reader."""
    root, warnings = parse_tags(body_of("banks/unnamed-bank/mixed-case-trntype.ofx"))
    txn = child(root, "STMTTRN")

    assert txn.text("TRNTYPE") == "Credit"
    assert txn.text("DTPOSTED") == "20260115"
    assert txn.text("TRNAMT") == "-10.00"
    assert txn.text("MEMO") == "ANON MEMO"
    assert warnings == []


def test_a_fully_closed_xml_body_yields_the_same_tree_as_the_sgml_one() -> None:
    """`unnamed-bank/xml-declaration-ofx-2.ofx` is the shared template written in OFX 2.x XML,
    with one changed payee. One algorithm covers both styles, or that claim is untested."""
    xml, xml_warnings = parse_tags(body_of("banks/unnamed-bank/xml-declaration-ofx-2.ofx"))
    sgml, sgml_warnings = parse_tags(body_of("template/ofx-1.0.2.ofx"))

    assert [path for path, _ in paths(xml)] == [path for path, _ in paths(sgml)]
    differences = [
        (path, left, right)
        for (path, left), (_, right) in zip(paths(xml), paths(sgml), strict=True)
        if left != right
    ]
    assert differences == [
        (
            "/OFX/BANKMSGSRSV1/STMTTRNRS/STMTRS/BANKTRANLIST/STMTTRN/NAME",
            "ANON ÉNERGIE",
            "ANON MERCHANT",
        )
    ]
    assert xml_warnings == []
    assert sgml_warnings == []


def test_the_processing_instructions_of_an_ofx_2_file_are_not_tags() -> None:
    """The body starts at the first `<`, which in an OFX 2.x file is `<?xml ...?>`."""
    root, warnings = parse_tags(body_of("banks/unnamed-bank/xml-declaration-ofx-2.ofx"))
    assert [kid.tag for kid in root.children] == ["OFX"]
    assert warnings == []


def test_tag_names_are_read_and_matched_uppercased() -> None:
    root, warnings = parse_tags("<Ofx><stmtTrn><TrnAmt>-10.00</trnamt></STMTTRN></ofx>")
    assert [kid.tag for kid in root.children] == ["OFX"]
    assert child(root, "stmttrn").text("trnamt") == "-10.00"
    assert warnings == []


def test_the_corpus_sweep_actually_has_files_to_sweep() -> None:
    """A glob that quietly matches nothing turns the two tests below into assertions about an
    empty list, which pass forever and prove nothing."""
    assert len(EVERY_OFX_FILE) >= 18
    assert "template/ofx-1.0.2.ofx" in EVERY_OFX_FILE


@pytest.mark.parametrize("relative", EVERY_OFX_FILE)
def test_a_node_never_carries_both_a_value_and_children(relative: str) -> None:
    """A value on an aggregate would mean the reader mixed a leaf and its parent, which is
    exactly how a field gets attributed to the wrong tag."""
    root, _ = parse_tags(body_of(relative))
    for node in every_node(root):
        assert node.value is None or node.children == (), node.tag


@pytest.mark.parametrize("relative", EVERY_OFX_FILE)
def test_every_corpus_file_reads_without_a_single_tag_warning(relative: str) -> None:
    """None of these files is malformed at tag level: the eighteen deviations they carry are in
    the header, the amounts and the dates. A warning appearing here means the reader started
    misreading a construct it used to read, on a real bank file."""
    root, warnings = parse_tags(body_of(relative))
    assert warnings == []
    assert [kid.tag for kid in root.children] == ["OFX"]


def test_find_all_returns_every_descendant_in_document_order() -> None:
    root, _ = parse_tags(body_of("banks/unnamed-bank/tags-outside-spec.ofx"))
    assert [node.value for node in root.find_all("BALAMT")] == ["90.00", "90.00"]
    assert [node.text("CODE") for node in root.find_all("STATUS")] == ["0", "0"]
    assert root.find_all("NOSUCHTAG") == []
    assert root.find("NOSUCHTAG") is None
    assert root.text("NOSUCHTAG") is None


def test_a_value_keeps_its_inner_characters_verbatim() -> None:
    """A `<` inside a memo is not a tag, and the surrounding newlines of an SGML file are not
    part of the value."""
    root, warnings = parse_tags("<STMTTRN>\n<MEMO>PRICE < 5, PAID  IN  FULL\n</STMTTRN>")
    assert child(root, "MEMO").value == "PRICE < 5, PAID  IN  FULL"
    assert warnings == []


def test_an_escaped_character_comes_out_as_the_character_the_file_meant() -> None:
    """`&amp;` is how both OFX 1.x SGML and OFX 2.x XML write a literal `&`. Returning it
    unresolved would be a wrong value, silently, in a payee name."""
    root, warnings = parse_tags(
        "<STMTTRN><NAME>SMITH &amp; SONS</NAME><MEMO>A &lt;B&gt; C</MEMO></STMTTRN>"
    )
    txn = child(root, "STMTTRN")
    assert txn.text("NAME") == "SMITH & SONS"
    assert txn.text("MEMO") == "A <B> C"
    assert warnings == []


def test_a_numeric_character_reference_is_resolved_and_an_unknown_one_is_left_alone() -> None:
    """We never invent a character: `&frob;` is not a reference we know, so it stays verbatim
    rather than turning into a replacement character nobody can trace back."""
    root, _ = parse_tags(
        "<A><NAME>CAF&#201; &#xe9;</NAME><MEMO>&frob; &amp;lt; &#1114113;</MEMO></A>"
    )
    assert child(root, "NAME").value == "CAFÉ é"
    # `&amp;lt;` is resolved once, into the TEXT `&lt;`, not twice into `<`. The last one is a
    # code point outside Unicode.
    assert child(root, "MEMO").value == "&frob; &lt; &#1114113;"


def test_a_cdata_section_keeps_its_text_instead_of_vanishing() -> None:
    """CDATA is skipped as markup by a naive tokeniser, which drops the value without a word."""
    root, warnings = parse_tags("<MEMO><![CDATA[PRICE < 5 & RISING]]></MEMO>")
    assert child(root, "MEMO").value == "PRICE < 5 & RISING"
    assert warnings == []


def test_a_value_interrupted_by_markup_does_not_glue_its_words_together() -> None:
    """Two runs of text separated by something the tree drops must not become one word. A memo
    reading PRICEDROP where the file said `PRICE DROP` is a value nobody can match back."""
    root, _ = parse_tags("<MEMO>PRICE <!--vendor note--> DROP</MEMO>")
    assert child(root, "MEMO").value == "PRICE  DROP"


def test_a_comparison_sign_in_a_memo_is_not_read_as_a_tag() -> None:
    """`< B >` is not a start tag in XML or in SGML: no whitespace is allowed after the `<`.
    Reading one there would cut the memo in two and invent an element."""
    root, warnings = parse_tags("<STMTTRN><MEMO>PAID < B > NOW</MEMO></STMTTRN>")
    txn = child(root, "STMTTRN")
    assert [kid.tag for kid in txn.children] == ["MEMO"]
    assert txn.text("MEMO") == "PAID < B > NOW"
    assert warnings == []


def test_a_document_nested_far_deeper_than_the_recursion_limit_still_reads() -> None:
    """Under the minimisation rule an empty unclosed leaf costs one level of nesting, so a
    corrupt file reaches any depth it likes. A reader that answers RecursionError has failed the
    whole file over its structure, which section 0 only allows when nothing usable comes out."""
    depth = 5000
    body = "".join(f"<T{index}>" for index in range(depth)) + "-10.00"
    root, warnings = parse_tags(body)
    assert child(root, "T0").tag == "T0"
    deepest = root.find(f"T{depth - 1}")
    assert deepest is not None
    assert deepest.value == "-10.00"
    assert [(w.rule, w.field) for w in warnings] == [("tag", "T0")]


def test_a_document_left_open_is_closed_implicitly_and_says_so() -> None:
    root, warnings = parse_tags("<OFX><BANKMSGSRSV1><STMTTRNRS><TRNUID>1")
    assert child(root, "STMTTRNRS").text("TRNUID") == "1"
    assert [(w.rule, w.field, w.value) for w in warnings] == [("tag", "OFX", None)]
    assert "STMTTRNRS" in warnings[0].message


def test_an_end_tag_with_no_start_tag_is_reported_and_closes_nothing() -> None:
    root, warnings = parse_tags("<OFX><SONRS></FI></SONRS><MEMO>kept</MEMO></OFX>")
    assert child(root, "OFX").text("MEMO") == "kept"
    assert child(root, "SONRS").children == ()
    assert [(w.rule, w.field, w.value) for w in warnings] == [("tag", "FI", None)]


def test_text_between_two_children_is_reported_instead_of_becoming_a_value() -> None:
    root, warnings = parse_tags("<OFX><SONRS><CODE>0</CODE>stray text</SONRS></OFX>")
    sonrs = child(root, "SONRS")
    assert sonrs.value is None
    assert sonrs.text("CODE") == "0"
    assert [(w.rule, w.field, w.value) for w in warnings] == [("tag", "SONRS", "stray text")]


def test_text_outside_any_tag_is_reported_rather_than_attached_to_the_root() -> None:
    root, warnings = parse_tags("<OFX></OFX>trailing junk")
    assert root.value is None
    assert [(w.rule, w.field, w.value) for w in warnings] == [("tag", None, "trailing junk")]


def test_a_body_with_no_tag_at_all_is_reported() -> None:
    root, warnings = parse_tags("")
    assert root.tag == ROOT_TAG
    assert root.children == ()
    assert [(w.rule, w.field, w.value) for w in warnings] == [("tag", None, None)]


@pytest.mark.parametrize(
    "body",
    [
        "",
        "   \n  ",
        "<",
        "<>",
        "</>",
        "<<OFX>>",
        "a < b",
        "<OFX",
        "<!-- unterminated",
        "<!DOCTYPE OFX SYSTEM 'ofx.dtd'>",
        "<?xml version='1.0'?>",
        "</OFX>",
        "<A><B>x</C></A>",
        "<A/>",
        "<A></A></A>",
        "<A>1<B>2</A>",
        "<A>&",
        "<A>&amp",
        "<A>&#;&#x;&;",
        "<A>&#99999999999999;",
        "<A><![CDATA[unterminated",
        "<![CDATA[]]>",
        "< A >",
        "<A/",
    ],
)
def test_malformed_input_never_raises(body: str) -> None:
    """Section 0: we only fail when no usable statement block comes out at all, and that
    verdict belongs to the caller. The reader itself always returns a tree."""
    root, warnings = parse_tags(body)
    assert root.tag == ROOT_TAG
    assert root.value is None
    assert all(w.rule == "tag" for w in warnings)
