# Security

## Reporting

Open a private security advisory through the Security tab of this repository. No public issue.

## What matters especially here

This project reads bank files. Two categories come first:

**A data leak in the repository.** A corpus file that is not anonymised enough is a
vulnerability, even if there is no bug. Report it as one.

**A parser that returns a wrong amount without an error.** In finance, a wrong but plausible
result is worse than a crash: it enters a reconciliation and nobody sees it. A silent gap
between the file and the output is treated as a vulnerability, not as a bug.
