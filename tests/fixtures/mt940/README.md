# MT940 fixtures, and where they come from

54 real statement files from 16 named banks, copied verbatim from the test suite of
[wolph/mt940](https://github.com/wolph/mt940) (the `mt-940` package this project depends on).
They are inputs, not expected outputs: the assertions live in `tests/test_mt940_adapter.py`.

Nothing here was edited. A fixture that is reformatted stops being evidence of what a bank
actually sends, which is the only reason to keep it in the repository.

## The banks

| directory | files | bank or origin |
|---|---|---|
| `ASNB/` | 2 | ASN Bank (NL). Puts a full IBAN in the `:61:` customer reference, which the standard `:61:` tag cannot read. |
| `betterplace/` | 9 | German SEPA exports collected by betterplace.org, including a file with a byte outside the SWIFT character set. |
| `citi/` | 1 | Citibank (US). |
| `cmxl/` | 11 | German and Polish files collected by the `cmxl` Ruby parser. |
| `jejik/` | 9 | ABN AMRO, ING, KNAB, PostFinance (CH), Rabobank, SNS, Triodos, plus a generic file. |
| `mBank/` | 3 | mBank (PL), MT940 and MT942. |
| `sberbank/` | 1 | Sberbank (HU), in HUF. |
| `self-provided/` | 15 | Sparkassen, Raiffeisen (HU, encoded in a DOS code page), and edge cases contributed to the parser. |

Files whose name says `broken`, `invalid` or `malformed` are kept on purpose: they are the
inputs for the tests that check we degrade instead of raising.

## Copyright

The corpus is redistributed under the BSD 3-Clause licence of `wolph/mt940`. Three of the
directories were themselves imported by that project from other parsers, and carry their own
notice in a `LICENSE` file next to the data: `betterplace/` (Apache 2.0),
`cmxl/` (MIT, Michael Bumann), `jejik/` (MIT, Frank Oxener, Agile Dovadi BV).

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
