# Phase 0: triaging the 43 open entries of `ofxparse`

> Done 2026-08-05. This is the full trace of the triage, entry by entry. It exists for two
> reasons: so nobody has to redo the sweep, and so every fixture in the corpus traces back to
> a source a reader can open.

The first deliverable of this repository is the corpus, not the parser. A model writes a
spec-compliant parser in thirty seconds; it cannot know that Wells Fargo writes its entire QFX
header on a single line. Those are facts about the world, they are observed, not derived.

## What the number 43 counts

As of 2026-08-05, `jseutter/ofxparse` has **33 open issues and 10 open pull requests**. The PRs
count, and they count double: an unmerged PR often carries the exact BYTES of the file that
broke, in its test fixture. Three of the examples in the brief are unmerged PRs: #172 (Wells
Fargo), #160 (Chase), #163 (`cpNONE`).

The age of those entries matters more than their count. One issue was opened in 2023, one in
2024, one in 2025, one in 2026; the bulk dates from 2010 to 2019. The inbound flow is about one
request a year. **This tracker is not a backlog of frustrated users waiting for a replacement**,
and the corpus below is worth more as a test asset than as a way back into that audience.

## The result

| | |
|---|---|
| entries triaged | 43 |
| entries carrying an attested file deviation | 15 |
| fixtures produced | 18 |
| banks named in the sources | 6 |
| entries with no file property | 28 |

Fifteen entries for eighteen fixtures: several entries describe the same deviation (the three
sources for `CHARSET:NONE` collapse into one fixture), and three entries carry several at once.
Issue #81 alone yields four, PR #179 three, PR #173 two.

**Only six of the eighteen cases name a bank.** That is what the sources allow: the other
reporters write "my bank" and nothing more. Inventing the other twelve would have looked better
and destroyed the asset.

## All 43, one by one

A verdict of `fixture` means the entry produced at least one corpus case. The others
carry the reason for rejection. The criterion is single and written once for all:
**the source must attest a property of the CONTENT of a file**. A feature request,
however legitimate, is not one.

| # | type | title | verdict |
|---|---|---|---|
| [182](https://github.com/jseutter/ofxparse/issues/182) | issue | Maintenance status of ofxparse | question or empty entry |
| [181](https://github.com/jseutter/ofxparse/pull/181) | PR | Remove bs4 deprecation warnings | repository documentation or maintenance |
| [180](https://github.com/jseutter/ofxparse/issues/180) | issue | There is a bug in ofxparse, owned by jseutter | question or empty entry |
| [179](https://github.com/jseutter/ofxparse/pull/179) | PR | Fix import OFX file with linebreak before headers and not A... | **fixture** `unnamed-bank/blank-line-before-header, amount-comma-decimal, zero-date, chase/non-ascii-byte-declared-usascii` |
| [177](https://github.com/jseutter/ofxparse/pull/177) | PR | trim usage of six | repository documentation or maintenance |
| [176](https://github.com/jseutter/ofxparse/issues/176) | issue | Feature Request - Add Transaction Parsing for "DTAVAIL" Fie... | spec coverage gap, not a deviation |
| [175](https://github.com/jseutter/ofxparse/pull/175) | PR | Add writer of Credit Card Statement | library feature request |
| [173](https://github.com/jseutter/ofxparse/pull/173) | PR | Handle `chknum` in transaction field | **fixture** `unnamed-bank/chknum-instead-of-checknum, amount-plus-sign-and-space` |
| [172](https://github.com/jseutter/ofxparse/pull/172) | PR | The header in a Wells Fargo  .qfx file contains no newlines | **fixture** `wells-fargo/header-on-one-line` |
| [171](https://github.com/jseutter/ofxparse/issues/171) | issue | Bug with encoding for ETrade | **fixture** `etrade/charset-none-with-encoding-usascii` |
| [170](https://github.com/jseutter/ofxparse/issues/170) | issue | XMLParsedAsHTMLWarning | file property already covered by #133 (OFX 2.x XML declaration), the rest is a BeautifulSoup warning |
| [169](https://github.com/jseutter/ofxparse/issues/169) | issue | Cannot process UTF-8 files with characters outside the 256 ... | **fixture** `unnamed-bank/character-outside-latin1` |
| [167](https://github.com/jseutter/ofxparse/issues/167) | issue | OfxPreprocessedFile() crashes on an empty close tag like th... | **fixture** `onpoint-community-credit-union/self-closing-memo-tag` |
| [166](https://github.com/jseutter/ofxparse/issues/166) | issue | Does this parse ofx 1.0 format? | named bank (Citi Australia), bytes never provided, see the open leads below |
| [164](https://github.com/jseutter/ofxparse/issues/164) | issue | Missing BANKACCTTO on statement transaction | spec coverage gap, not a deviation |
| [163](https://github.com/jseutter/ofxparse/pull/163) | PR | Fixing parse error "unknown encoding: cpNONE" | **fixture** `etrade/charset-none-with-encoding-usascii` |
| [162](https://github.com/jseutter/ofxparse/issues/162) | issue | Transaction that is not a DEBIT nor a CREDIT | **fixture** `lcl/check-without-payee` |
| [161](https://github.com/jseutter/ofxparse/pull/161) | PR | Allow parsing OFX files starting with empty lines | **fixture** `unnamed-bank/blank-line-before-header` |
| [160](https://github.com/jseutter/ofxparse/pull/160) | PR | Support parsing quirky Chase QFX headers | **fixture** `chase/blank-line-before-header-none-after, chase/non-ascii-byte-declared-usascii` |
| [159](https://github.com/jseutter/ofxparse/issues/159) | issue | Read an OFX String instead of a OFX file | library feature request |
| [158](https://github.com/jseutter/ofxparse/issues/158) | issue | transaction.security and position.security should be Securi... | spec coverage gap, not a deviation |
| [154](https://github.com/jseutter/ofxparse/issues/154) | issue | OfxParser.parse fails: unknown encoding: cpNONE | **fixture** `etrade/charset-none-with-encoding-usascii` |
| [149](https://github.com/jseutter/ofxparse/issues/149) | issue | Changing <FITID> is not persisting at all | library feature request |
| [148](https://github.com/jseutter/ofxparse/issues/148) | issue | Not able to read file with iso-8859-1 encoding | **fixture** `unnamed-bank/charset-8859-1-without-iso-prefix` |
| [145](https://github.com/jseutter/ofxparse/issues/145) | issue | 'str' object has no attribute 'strftime' in ofxprinter | internal Python bug, no file property |
| [144](https://github.com/jseutter/ofxparse/pull/144) | PR | Generic ofx2dataframe converter capable of handling multipl... | library feature request |
| [142](https://github.com/jseutter/ofxparse/issues/142) | issue | Python3 "TypeError: must be str, not bytes" | internal Python bug, no file property |
| [136](https://github.com/jseutter/ofxparse/issues/136) | issue | Transaction Date, Value, Memo | question or empty entry |
| [133](https://github.com/jseutter/ofxparse/issues/133) | issue | UTF-8 Encoding | **fixture** `unnamed-bank/xml-declaration-ofx-2` |
| [128](https://github.com/jseutter/ofxparse/issues/128) | issue | Can not add own field in Transaction Object | library feature request |
| [125](https://github.com/jseutter/ofxparse/issues/125) | issue | travis.yml should not specify BeautifulSoup for Python 2.7 | repository documentation or maintenance |
| [124](https://github.com/jseutter/ofxparse/issues/124) | issue | Currency on transactions | spec coverage gap, not a deviation |
| [81](https://github.com/jseutter/ofxparse/issues/81) | issue | Empty tags | **fixture** `unnamed-bank/empty-tags-curdef-fitid-name, mixed-case-trntype, tags-outside-spec, onpoint-community-credit-union/self-closing-memo-tag` |
| [70](https://github.com/jseutter/ofxparse/issues/70) | issue | [easy] PEP8 code style cleanup | repository documentation or maintenance |
| [58](https://github.com/jseutter/ofxparse/issues/58) | issue | [medium] Parse dates in %d%m%y format | **fixture** `hsbc-brasil/dtstart-ddmmyy` |
| [57](https://github.com/jseutter/ofxparse/issues/57) | issue | [medium] Use coveralls.io to generate test coverage stats | repository documentation or maintenance |
| [50](https://github.com/jseutter/ofxparse/issues/50) | issue | [easy] README file does not show attributes of transactions | repository documentation or maintenance |
| [29](https://github.com/jseutter/ofxparse/issues/29) | issue | [easy] FTIDs in test fixtures should be unique | repository documentation or maintenance |
| [17](https://github.com/jseutter/ofxparse/issues/17) | issue | [medium] Application script: Convert an OFX file to a set o... | library feature request |
| [16](https://github.com/jseutter/ofxparse/issues/16) | issue | [medium] Application script: Convert an OFX file to a .json... | library feature request |
| [15](https://github.com/jseutter/ofxparse/issues/15) | issue | [medium] Application script: Convert an OFX file to a CSV file | library feature request |
| [14](https://github.com/jseutter/ofxparse/issues/14) | issue | [hard] Document how to make a release | repository documentation or maintenance |
| [5](https://github.com/jseutter/ofxparse/issues/5) | issue | [medium] ofxparse wiki pages | repository documentation or maintenance |

## Four entries, one single cause

`#160` (Chase), `#161`, `#169` and `#179` describe four different files and one bug:
`read_headers` cuts the header at the first `<` and then stops at the first blank line. One
blank line at the top of the file and ALL the headers are lost in silence. The file still reads
as long as it is pure ASCII, and breaks on the first accented byte, which is why the reports
look like they contradict each other.

That is the kind of fact you only see by triaging all 43 at once, and it is a direct argument
for the unification layer: one rule, written once, covers four banks.

## What this triage does NOT prove

- **The corpus contains no MT940, CAMT.053 or BAI2 deviation.** The source triaged here is an
  OFX parser, it could not produce anything else. Phase 1 covers MT940 AND OFX/QFX: the MT940
  half of the corpus is still entirely to be built, and it will not come out of this tracker.
- **No fixture is a real bank file in our possession.** All of them are rebuilt from public
  text on a shared template, so that the diff against the template is exactly the deviation.
  Every note states what comes from quoted bytes and what comes from the template.
- **Some deviations rest on a single report, sometimes an old one.** HSBC Brasil dates from
  2013 and has never been reconfirmed. The note says so.
- **A fixture that breaks neither parser is not proof of uselessness.** Three fixtures pass
  everywhere today: they document a real shape and act as a guard rail for our own parser.

## Open leads this triage leaves behind

- **#166 names Citi Australia** and describes an "odd" OFX 1.0 that fails, without ever giving
  the bytes. It is the only named bank in the tracker whose file is missing: one question in
  the issue would recover it.
- **Four entries ask for spec fields `ofxparse` does not expose** (`DTAVAIL` #176, `BANKACCTTO`
  and `CCACCTTO` #164, `CURRENCY` and `CURRATE` #124, the `Security` object #158). These are
  not deviations, a model derives them from the specification. They are, however, a list of
  fields real files actually carry, so they feed the normalised schema of phase 1 directly.
- **#29 is a warning addressed to us.** The `ofxparse` maintainers anonymised their own
  fixtures until the `FITID` values were no longer unique, which broke the property the fixture
  was testing. Our anonymisation has to stop before the property under test. The first pass of
  this corpus made that exact mistake on the LCL fixture, giving `CHECKNUM` the same value as
  `FITID`; an audit caught it.
