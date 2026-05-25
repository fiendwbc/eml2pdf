#!/usr/bin/env python3
"""
eml2pdf — Convert .eml email files to PDF.

Examples:
    # Single file → writes invoice.pdf next to invoice.eml
    eml2pdf invoice.eml

    # Multiple files → one PDF each
    eml2pdf *.eml

    # Custom output directory
    eml2pdf *.eml -o ~/Documents/email-archive/

    # Single file → custom output path
    eml2pdf invoice.eml -o /tmp/my-receipt.pdf

Each PDF contains:
  - A header block (From / To / Cc / Date / Subject)
  - The email body (HTML when available, otherwise plain text)
  - Inline images embedded via cid: references (as data URIs)
  - A list of attachments at the bottom (not embedded in the PDF)

Requirements:
  - Python 3.8+
  - wkhtmltopdf  (Debian/Ubuntu: `apt install wkhtmltopdf`;
                  macOS: `brew install wkhtmltopdf`;
                  Windows: https://wkhtmltopdf.org/downloads.html)
"""

from __future__ import annotations

import argparse
import base64
import email
import re
import shutil
import subprocess
import sys
from email import policy
from html import escape
from pathlib import Path

# ---------- HTML wrapper ----------------------------------------------------

WRAPPER = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { font-family: Arial, Helvetica, sans-serif; font-size: 13px;
         color: #222; margin: 24px; }
  .email-header { border: 1px solid #ccc; border-radius: 4px;
                  padding: 12px 16px; margin-bottom: 20px;
                  background: #f7f7f7; }
  .email-header table { border-collapse: collapse; }
  .email-header td { padding: 3px 8px 3px 0; vertical-align: top; }
  .email-header td.label { font-weight: bold; color: #555;
                           white-space: nowrap; width: 70px; }
  .email-body { border-top: 2px solid #1976d2; padding-top: 16px; }
  .attachments { margin-top: 20px; padding: 10px; background: #fffbea;
                 border-left: 3px solid #f6c700; font-size: 12px; }
  pre.plain-body { white-space: pre-wrap; word-wrap: break-word;
                   font-family: inherit; }
</style></head>
<body>
  <div class="email-header"><table>##HEADER_ROWS##</table></div>
  <div class="email-body">##BODY##</div>
  ##ATTACHMENTS##
</body></html>
"""

# ---------- Email parsing helpers -------------------------------------------


def build_header_rows(msg) -> str:
    rows = []
    fields = [("From", "From"), ("To", "To"), ("Cc", "Cc"),
              ("Date", "Date"), ("Subject", "Subject")]
    for label, field in fields:
        val = msg.get(field)
        if val is None:
            continue
        val_html = escape(str(val))
        if field == "Subject":
            val_html = f"<b>{val_html}</b>"
        rows.append(
            f'<tr><td class="label">{label}:</td><td>{val_html}</td></tr>'
        )
    return "".join(rows)


def collect_inline_images(msg) -> dict:
    """Map Content-ID → (mime_type, base64_data) for cid: replacement."""
    images = {}
    for part in msg.walk():
        if part.get_content_maintype() != "image":
            continue
        cid = part.get("Content-ID", "")
        if not cid:
            continue
        cid = cid.strip("<>")
        try:
            data = part.get_payload(decode=True)
        except Exception:
            continue
        if data:
            images[cid] = (part.get_content_type(),
                           base64.b64encode(data).decode("ascii"))
    return images


_CID_PATTERN = re.compile(r'src=["\']cid:([^"\']+)["\']', re.I)


def replace_cid_images(html: str, images: dict) -> str:
    def repl(m):
        cid = m.group(1)
        if cid in images:
            mime, b64 = images[cid]
            return f'src="data:{mime};base64,{b64}"'
        return m.group(0)
    return _CID_PATTERN.sub(repl, html)


def collect_attachments(msg):
    """List (filename, size_bytes) for non-inline attachments."""
    out = []
    for part in msg.walk():
        if part.is_multipart():
            continue
        if part.get_content_disposition() != "attachment":
            continue
        fn = part.get_filename() or "(unnamed)"
        try:
            data = part.get_payload(decode=True)
            size = len(data) if data else 0
        except Exception:
            size = 0
        out.append((fn, size))
    return out


def clean_html(html: str) -> str:
    """Strip remote font links that often hang the renderer."""
    return re.sub(
        r'<link[^>]*fonts\.googleapis\.com[^>]*>', '', html, flags=re.I
    )


def get_body_html(msg) -> str:
    html_part = msg.get_body(preferencelist=("html",))
    if html_part:
        return clean_html(html_part.get_content())
    text_part = msg.get_body(preferencelist=("plain",))
    if text_part:
        return f'<pre class="plain-body">{escape(text_part.get_content())}</pre>'
    return "<i>(empty body)</i>"


def build_attachments_block(atts) -> str:
    if not atts:
        return ""
    rows = "".join(
        f'<div>📎 {escape(fn)} ({size:,} bytes)</div>'
        for fn, size in atts
    )
    return (f'<div class="attachments">'
            f'<b>Attachments ({len(atts)}):</b>{rows}</div>')


def eml_to_html(msg) -> str:
    body = replace_cid_images(get_body_html(msg), collect_inline_images(msg))
    return (WRAPPER
            .replace("##HEADER_ROWS##", build_header_rows(msg))
            .replace("##BODY##", body)
            .replace("##ATTACHMENTS##", build_attachments_block(
                collect_attachments(msg))))


# ---------- Conversion -------------------------------------------------------


def convert_one(eml_path: Path, out_path: Path) -> None:
    with open(eml_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    html = eml_to_html(msg)
    tmp_html = out_path.with_name(out_path.stem + ".__eml2pdf__.html")
    tmp_html.write_text(html, encoding="utf-8")
    try:
        result = subprocess.run([
            "wkhtmltopdf",
            "--quiet",
            "--encoding", "utf-8",
            "--margin-top", "12mm", "--margin-bottom", "12mm",
            "--margin-left", "12mm", "--margin-right", "12mm",
            "--load-error-handling", "ignore",
            "--load-media-error-handling", "ignore",
            "--enable-local-file-access",
            str(tmp_html), str(out_path),
        ], capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            sys.stderr.write(f"wkhtmltopdf error on {eml_path}:\n"
                             f"{result.stderr}\n")
            raise SystemExit(1)
    finally:
        tmp_html.unlink(missing_ok=True)


# ---------- CLI --------------------------------------------------------------


def main() -> None:
    p = argparse.ArgumentParser(
        prog="eml2pdf",
        description="Convert .eml email files to PDF.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Requires wkhtmltopdf in PATH.",
    )
    p.add_argument("inputs", nargs="+", help="One or more .eml files")
    p.add_argument(
        "-o", "--output",
        help=("Output PDF path (single input) OR output directory "
              "(multiple inputs). Default: write <name>.pdf next to "
              "each input."),
    )
    args = p.parse_args()

    if shutil.which("wkhtmltopdf") is None:
        sys.exit("Error: wkhtmltopdf not found in PATH. "
                 "Install it first (see --help).")

    inputs = [Path(s) for s in args.inputs]
    missing = [str(i) for i in inputs if not i.is_file()]
    if missing:
        sys.exit("Not found: " + ", ".join(missing))

    if args.output and len(inputs) == 1 and not Path(args.output).is_dir() \
            and not args.output.endswith(("/", "\\")):
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        convert_one(inputs[0], out)
        print(f"Wrote: {out}")
        return

    if args.output:
        out_dir = Path(args.output)
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = None

    for eml in inputs:
        target = (out_dir / (eml.stem + ".pdf")) if out_dir \
            else eml.with_suffix(".pdf")
        convert_one(eml, target)
        print(f"Wrote: {target}")


if __name__ == "__main__":
    main()
