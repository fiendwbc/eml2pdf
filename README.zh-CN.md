# eml2pdf

> [English](README.md) | **简体中文**

一个小巧、零三方依赖的命令行工具，把 `.eml` 邮件文件转换成清晰易读的 PDF。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)

每个生成的 PDF 包含：

- 📋 **邮件头信息** —— `发件人` / `收件人` / `抄送` / `日期` / `主题`
- 📝 **邮件正文** —— 优先渲染 HTML，没有 HTML 时回退为纯文本
- 🖼️ **内嵌图片** —— 通过 `cid:` 引用嵌入（转换为 data URI）
- 📎 底部的**附件清单** —— 列出文件名和大小（附件本身*不会*被嵌入 PDF）

Python 代码**仅使用标准库**，唯一的外部依赖是负责 HTML → PDF 渲染的 [`wkhtmltopdf`](https://wkhtmltopdf.org/) 程序。

---

## 环境要求

- **Python 3.12+**
- `PATH` 中可用的 **wkhtmltopdf**

### 安装 wkhtmltopdf

| 平台 | 命令 |
| --- | --- |
| Debian / Ubuntu | `sudo apt install wkhtmltopdf` |
| macOS (Homebrew) | `brew install wkhtmltopdf` |
| Windows | 从 <https://wkhtmltopdf.org/downloads.html> 下载安装包 |

验证是否安装成功：

```bash
wkhtmltopdf --version
```

---

## 安装

### 方式 A —— 安装为命令（推荐）

```bash
git clone https://github.com/fiendwbc/eml2pdf.git
cd eml2pdf
pip install .
```

安装后会在 `PATH` 中提供 `eml2pdf` 命令。

> 提示：想要隔离环境，可用 [`pipx`](https://pipx.pypa.io/)：`pipx install .`

### 方式 B —— 直接运行脚本

无需安装，直接运行单个文件即可：

```bash
python eml2pdf.py invoice.eml
```

---

## 使用方法

```text
eml2pdf [-h] [-o OUTPUT] inputs [inputs ...]
```

| 参数 | 说明 |
| --- | --- |
| `inputs` | 一个或多个 `.eml` 文件（`*.eml` 这类通配符由你的 shell 展开）。 |
| `-o`, `--output` | 输出 PDF 路径（单个输入时）**或**输出目录（多个输入时）。默认在每个输入文件旁边生成 `<名称>.pdf`。 |

### 示例

```bash
# 单个文件 → 在 invoice.eml 旁边生成 invoice.pdf
eml2pdf invoice.eml

# 多个文件 → 各生成一个 PDF，放在原文件旁边
eml2pdf *.eml

# 把所有输出 PDF 放到指定目录
eml2pdf *.eml -o ~/Documents/email-archive/

# 单个文件 → 指定明确的输出路径
eml2pdf invoice.eml -o /tmp/my-receipt.pdf
```

每次转换成功后会打印写入的路径，例如：

```text
Wrote: invoice.pdf
```

---

## 工作原理

1. 使用 Python 的 [`email`](https://docs.python.org/3/library/email.html) 库（`policy.default`）解析 `.eml` 文件。
2. 把邮件头、正文、内嵌图片和附件清单组装成一个自包含的 HTML 文档（内置了一小段样式表）。
3. 把正文中的 `cid:` 内嵌图片引用改写为 base64 的 `data:` URI，无需外部文件即可显示图片。
4. 移除指向 Google Fonts 的远程 `<link>` 标签，因为它们常常会拖慢甚至卡住渲染。
5. 由 `wkhtmltopdf` 将临时 HTML 文件转换成 PDF，转换结束后始终会清理临时文件。

---

## 说明与限制

- **附件只列出、不嵌入。** PDF 中会显示每个附件的文件名和大小，但不包含附件内容。
- **wkhtmltopdf 的渲染**基于较旧的 WebKit 引擎，非常新的 CSS 可能无法完美渲染；对于常见邮件一般不成问题。
- 每个文件的转换有 **120 秒超时**；包含大量远程资源的复杂邮件可能需要稍等片刻。
- 如果 `PATH` 中找不到 `wkhtmltopdf`，工具会提前退出并给出提示。

---

## 许可证

[MIT](LICENSE) © fiendwbc
