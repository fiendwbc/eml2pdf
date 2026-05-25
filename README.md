# eml2pdf

> **English** | [简体中文](README.zh-CN.md)

A tiny, dependency-free command-line tool that converts `.eml` email files into clean, readable PDFs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

Each generated PDF contains:

- 📋 A **header block** — `From` / `To` / `Cc` / `Date` / `Subject`
- 📝 The **email body** — rendered HTML when available, otherwise plain text
- 🖼️ **Inline images** embedded via `cid:` references (converted to data URIs)
- 📎 A list of **attachments** at the bottom (names and sizes; the files themselves are *not* embedded)

The Python code uses **only the standard library** — the single external dependency is the [`wkhtmltopdf`](https://wkhtmltopdf.org/) binary that does the HTML → PDF rendering.

---

## Requirements

- **Python 3.12+**
- **wkhtmltopdf** available on your `PATH`

### Installing wkhtmltopdf

| Platform | Command |
| --- | --- |
| Debian / Ubuntu | `sudo apt install wkhtmltopdf` |
| macOS (Homebrew) | `brew install wkhtmltopdf` |
| Windows | Download the installer from <https://wkhtmltopdf.org/downloads.html> |

Verify it is reachable:

```bash
wkhtmltopdf --version
```

---

## Installation

### Option A — install as a command (recommended)

```bash
git clone https://github.com/fiendwbc/eml2pdf.git
cd eml2pdf
pip install .
```

This exposes an `eml2pdf` command on your `PATH`.

> Tip: to keep it isolated, use [`pipx`](https://pipx.pypa.io/): `pipx install .`

### Option B — run the script directly

No installation needed — just run the single file:

```bash
python eml2pdf.py invoice.eml
```

---

## Usage

```text
eml2pdf [-h] [-o OUTPUT] inputs [inputs ...]
```

| Argument | Description |
| --- | --- |
| `inputs` | One or more `.eml` files (globs like `*.eml` are expanded by your shell). |
| `-o`, `--output` | Output PDF path (single input) **or** an output directory (multiple inputs). Defaults to writing `<name>.pdf` next to each input. |

### Examples

```bash
# Single file → writes invoice.pdf next to invoice.eml
eml2pdf invoice.eml

# Multiple files → one PDF each, alongside the originals
eml2pdf *.eml

# Send all output PDFs to a specific directory
eml2pdf *.eml -o ~/Documents/email-archive/

# Single file → an explicit output path
eml2pdf invoice.eml -o /tmp/my-receipt.pdf
```

Each successful conversion prints the path it wrote, e.g.:

```text
Wrote: invoice.pdf
```

---

## How it works

1. The `.eml` file is parsed with Python's [`email`](https://docs.python.org/3/library/email.html) package using `policy.default`.
2. The header fields, body, inline images, and attachment list are assembled into a single self-contained HTML document (styled with a small embedded stylesheet).
3. Inline `cid:` image references are rewritten to base64 `data:` URIs so the images render without external files.
4. Remote Google Fonts `<link>` tags are stripped, since they commonly stall the renderer.
5. `wkhtmltopdf` converts the temporary HTML file to PDF; the temp file is always cleaned up afterwards.

---

## Notes & limitations

- **Attachments are listed, not embedded.** The PDF shows each attachment's filename and size, but does not include the file contents.
- **wkhtmltopdf rendering** is based on an older WebKit engine, so very modern CSS may not render perfectly. For typical emails this is rarely an issue.
- Conversion has a **120-second timeout** per file; complex emails with many remote resources may take a moment.
- If `wkhtmltopdf` is missing from `PATH`, the tool exits early with a helpful message.

---

## License

[MIT](LICENSE) © fiendwbc
