# MT940 fixtures, and where they come from

54 real statement files, copied verbatim from the test suite of
[wolph/mt940](https://github.com/wolph/mt940) (the `mt-940` package this project depends on).
They are inputs, not expected outputs: the assertions live in `tests/test_mt940_adapter.py`.

These files were edited in exactly one way, on 2026-08-06, and it matters enough to say
precisely how. An audit found real personal data in six of them: a named account holder with a
full January 2020 statement, another person's name beside a childcare debit, an unmasked
account number, and four days of card spending with merchant, town and timestamp, which is a
location history. Those tokens were replaced by placeholders of the SAME LENGTH, so not one
byte of structure moved and every dialect under test reads exactly as before.

Nothing else was touched. A fixture that is reformatted stops being evidence of what a bank
actually sends, which is the only reason to keep it here. `tests/fixtures/REVIEWED.json` records
the hash of every file as it was read and cleared, and `scripts/validate_corpus.py` fails if any
of them changes, so the next edit cannot pass unread.

## The banks

| directory | files | bank or origin |
|---|---|---|
| `ASNB/` | 2 | ASN Bank (NL). Puts a full IBAN in the `:61:` customer reference, which the standard `:61:` tag cannot read. |
| `betterplace/` | 10 | German SEPA exports collected by betterplace.org, including a file with a byte outside the SWIFT character set. |
| `citi/` | 1 | Citibank (US). |
| `cmxl/` | 11 | German and Polish files collected by the `cmxl` Ruby parser. |
| `jejik/` | 9 | ABN AMRO, ING, KNAB, PostFinance (CH), Rabobank, SNS, Triodos, plus a generic file. |
| `mBank/` | 3 | mBank (PL), MT940 and MT942. |
| `sberbank/` | 1 | Sberbank (HU), in HUF. |
| `self-provided/` | 17 | Sparkassen, Raiffeisen (HU, encoded in a DOS code page), and edge cases contributed to the parser. |

Files whose name says `broken`, `invalid` or `malformed` are kept on purpose: they are the
inputs for the tests that check we degrade instead of raising.

These counts are the tree's, not a memory of it. They were wrong in the first version of this
file, by one in one directory and two in another, which is exactly how a table stops being
checked and starts being decoration.

## Copyright

Most of this corpus is redistributed under the BSD 3-Clause licence of `wolph/mt940`, copyright
Rick van Hattem, reproduced in full below. Three directories reached that project from
elsewhere and are NOT his: each keeps its own terms and its own holder, in a `LICENSE` file
beside its data. Naming two of the three and leaving the third as a bare licence name, which is
what this section used to do, drops a copyright holder from the only notice a reader gets.

| directory | licence | copyright holder |
|---|---|---|
| `betterplace/` | Apache 2.0 | betterplace, 2010 |
| `cmxl/` | MIT | Michael Bumann, 2014 |
| `jejik/` | MIT | Frank Oxener, Agile Dovadi BV, 2012 |

These are MODIFIED copies, and saying so is not politeness: the Apache 2.0 licence covering
`betterplace/` requires a changed file to carry a notice that it was changed. That notice is
the paragraph above beginning "These files were edited in exactly one way", which gives the
date, what was replaced in the six files concerned, and why. It covers every directory here.

`{organization}` in the block below is upstream's own unfilled placeholder in the `wolph/mt940`
LICENSE. It is reproduced as it stands, like the rest of the text.

```
Copyright (c) 2014, Rick van Hattem
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the {organization} nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```
