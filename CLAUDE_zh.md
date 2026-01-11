# CLAUDE.md

本文件為 Claude Code (claude.ai/code) 在此程式碼庫中工作時提供指引。

## 專案概述

epub-utils 是一個 Python 函式庫和 CLI 工具，用於從終端機檢視 EPUB 檔案。支援 EPUB 2.0.1 和 EPUB 3.0+ 規範。

## 虛擬環境

虛擬環境名稱為 `epub-utils`。

## 常用指令

```bash
# 執行所有測試
pytest

# 執行單一測試檔案
pytest tests/test_doc.py

# 執行特定測試
pytest tests/test_doc.py::test_function_name

# 程式碼檢查
ruff check

# 格式化程式碼
ruff check --select I --fix && ruff format

# Makefile 快捷指令
make test      # 執行測試
make lint      # 程式碼檢查
make format    # 格式化程式碼
make coverage  # 產生覆蓋率報告
```

## 程式碼風格

- 使用 ruff 進行程式碼檢查和格式化
- Tab 縮排、單引號、100 字元行寬限制
- 設定檔位於 `ruff.toml`

## 架構

### 進入點
- **CLI**: `epub_utils/cli.py` - 基於 Click 的 CLI，包含指令：`container`、`package`、`toc`、`metadata`、`manifest`、`spine`、`content`、`files`
- **函式庫**: `epub_utils.Document` - 主要 API 進入點

### 核心類別 (epub_utils/)
- `Document` (`doc.py`)：主類別，封裝 EPUB 檔案。所有解析元件皆採用延遲載入。
- `Container` (`container.py`)：解析 `META-INF/container.xml`，定位 OPF 套件檔案。
- `Package` (`package/__init__.py`)：解析 OPF 檔案，包含 `Metadata`、`Manifest` 和 `Spine`。
- `Metadata` (`package/metadata.py`)：Dublin Core 元資料（標題、創作者、識別碼等）
- `Manifest` (`package/manifest.py`)：EPUB 中所有資源的清單
- `Spine` (`package/spine.py`)：內容文件的閱讀順序

### 導覽 (epub_utils/navigation/)
- `Navigation`（基礎類別）：抽象導覽介面
- `NCXNavigation` (`ncx/`)：EPUB 2.0 導覽控制檔案 (toc.ncx)
- `EPUBNavDocNavigation` (`nav/`)：EPUB 3.0 導覽文件 (nav.xhtml)

### 內容 (epub_utils/content/)
- `XHTMLContent`：表示 XHTML 內容文件，具有輸出方法（`to_xml()`、`to_str()`、`to_plain()`）

### 輸出格式化
- 所有文件類別都有 `to_str()`（原始 XML）、`to_xml()`（語法高亮），部分具有 `to_kv()`（鍵值對）
- `XMLPrinter` (`printers.py`)：透過 Pygments 處理 XML 格式化和語法高亮

### 例外處理 (epub_utils/exceptions.py)
- `EPUBError`：基礎例外，具有結構化錯誤訊息和建議
- `ParseError`、`InvalidEPUBError`、`UnsupportedFormatError`、`FileNotFoundError`、`ValidationError`

## 測試

- 測試位於 `tests/` 目錄
- 測試 fixture 使用 `tests/assets/` 中的 EPUB 檔案
- `conftest.py` 提供 `doc_path` fixture，指向測試用 EPUB

## 依賴套件

- `click`：CLI 框架
- `lxml`：XML 解析（若無法使用則回退至標準函式庫 xml.etree）
- `pygments`：語法高亮
- `packaging`：版本解析

## 開發環境安裝

本專案使用**兩套並行的依賴管理系統**（這是較舊 Python 專案的常見模式）：

### 兩套系統說明

| 系統 | 檔案 | 用途 |
|------|------|------|
| setuptools | `setup.py` | 給 pip/PyPI 的套件元資料，版本規格較彈性 |
| requirements | `requirements/*.txt` | 開發依賴，鎖定精確版本 |

### 快速設定（建議）

```bash
# 步驟 1：以可編輯模式安裝套件（讀取 setup.py）
pip install -e .

# 步驟 2：安裝所有開發依賴（讀取 requirements.txt）
pip install -r requirements.txt
```

### 各指令安裝內容

**`pip install -e .`**（來自 `setup.py`）：
- 核心依賴：click, lxml, packaging, pygments, PyYAML
- 註冊 `epub-utils` CLI 指令

**`pip install -r requirements.txt`**（聚合所有 requirements 檔案）：
- `requirements/requirements.txt` - 核心依賴（鎖定版本）
- `requirements/requirements-testing.txt` - pytest, coverage
- `requirements/requirements-linting.txt` - ruff
- `requirements/requirements-docs.txt` - sphinx, furo

### 替代方式：使用 extras

```bash
# 使用 setup.py 中定義的 extras 安裝
pip install -e ".[test]"       # 核心 + pytest
pip install -e ".[docs]"       # 核心 + sphinx
pip install -e ".[test,docs]"  # 核心 + pytest + sphinx
```

### 為什麼有兩套系統？

- `setup.py` 使用彈性版本（`click`）以相容不同使用者環境
- `requirements.txt` 使用鎖定版本（`click==8.1.8`）確保開發環境可重現
- 現代專案通常使用 `pyproject.toml` 統一兩種方式
