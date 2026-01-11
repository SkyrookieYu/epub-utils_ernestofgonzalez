# EPUB Summarization 開發對話記錄

## 2026-01-11 開發過程

### 1. 輸出檔名格式修改

**需求**: 將輸出檔名從 `[書名]-[mapreduce|refine].md` 改為使用 EPUB 檔名

**實作**: 修改 `summarize.py` 中的檔名生成邏輯
```python
epub_basename = os.path.splitext(os.path.basename(epub_path))[0]
strategy_suffix = 'mapreduce' if strategy == 'map_reduce' else 'refine'
output_file = os.path.join(epub_dir, f"{epub_basename}-{strategy_suffix}.md")
```

---

### 2. 測試 4 個 EPUB 檔案

**測試檔案**: 178998.epub, 318347.epub, 362484.epub, 424489.epub

**問題發現**: 背景任務無法讀取 conda 環境變數中的 ANTHROPIC_API_KEY

**解決方案**: 在每個命令中直接 export API key（背景任務執行在獨立 shell，不繼承 conda 環境變數）

---

### 3. 「世界盡頭的咖啡館」(424489.epub) 內容載入問題

**問題**: 大部分章節顯示 [無內容]

**調查結果**:
- EPUB 結構中，章節標題為 SVG 圖片檔（如 story-6.xhtml）
- 實際文字內容在後續檔案（如 story-7.xhtml）
- TOC 目標指向圖片檔，導致無法正確載入文字

**用戶確認**: 這是正常的 EPUB 結構，FBReader 可正常開啟

---

### 4. 實作 Spine-Based 內容提取

**新增方法**:
- `_build_spine_hrefs()`: 從 spine 建立有序的內容 href 列表
- `_get_spine_index_for_target()`: 將 TOC 目標對應到 spine 索引
- `_load_single_file_content()`: 載入單一檔案內容
- `_load_spine_range_content()`: 載入多個 spine 項目的內容
- `_flatten_chapters_with_targets()`: 將章節樹扁平化以利處理

**修改方法**:
- `load_chapter_content()`: 現在讀取 TOC 條目之間的所有 spine 項目
- `load_all_chapters()`: 傳遞下一章節目標以計算範圍

**結果**: 所有章節現在都能正確載入內容

---

### 5. 最終測試結果

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998.epub | 50KB | 2.8KB |
| 318347.epub | 54KB | 2.7KB |
| 362484.epub | 67KB | 2.5KB |
| 424489.epub | 34KB | 2.7KB |

---

### 6. 檢視 Prompt 參數

**Map Reduce 策略**:
- 章節摘要: 150-300 字 (`llm.py:62-75`)
- 全書摘要: 300-500 字 (`llm.py:96-110`)

**Refine 策略**:
- 初始摘要: 200-400 字 (`llm.py:161-175`)
- 精煉摘要: 動態 min(300 + chapter_index * 50, 800) 字 (`llm.py:177-198`)
- 最終整理: 500-800 字 (`llm.py:219-234`)

**用戶反饋**: 全書摘要可能太短，待調整

---

### 7. 建立開發日誌

建立 `CHANGELOG_CUSTOM.md` 記錄：
- 已完成功能
- 兩種摘要策略的完整 prompt 內容與長度要求
- 測試結果
- 待優化項目

---

### 8. Git 操作

**Commit**:
```
561d004 Add epub-summarization module with two summarization strategies
```

**推送問題**: HTTPS 認證失敗

**解決**: 切換到 SSH
```bash
git remote set-url origin git@github.com:SkyrookieYu/epub-utils_ernestofgonzalez.git
git push
```

---

## 技術筆記

### Spine vs TOC 的區別

- **Spine**: 定義閱讀順序，列出所有內容檔案的 idref
- **TOC**: 提供導航目標，但不一定涵蓋所有內容

### EPUB 內容跨檔案問題

某些 EPUB（如 424489.epub）的結構：
- 偶數檔案 (story-6, story-8...): SVG 章節標題圖片
- 奇數檔案 (story-7, story-9...): 實際文字內容
- TOC 指向圖片檔，需要讀取後續 spine 項目才能取得文字

### Conda 環境變數

- `conda env config vars set` 設定的變數需要重新啟動環境才生效
- 背景任務（如 `&` 或獨立 shell）不會繼承這些變數
- 解決方案：在命令中直接 export 或使用 `.env` 檔案

---

## 檔案結構

```
epub-summarization/
├── __init__.py             # 模組初始化
├── llm.py                  # Claude API 整合
├── summarize.py            # 主要摘要邏輯
├── requirements.txt        # 依賴套件
├── CHANGELOG_CUSTOM.md     # 開發日誌與 Prompt 參數
└── CLAUDE_CONVERSATION.md  # 對話記錄 (本檔案)
```

---

## 2026-01-11 對話續篇

### 9. 調整 Map Reduce 全書摘要長度

**問題**: Map Reduce 策略產生的全書摘要比 Refine 策略短

**解決方案**:
- 修改 `llm.py:102`
- 將摘要長度要求從 `300-500 字` 改為 `500-800 字`（與 Refine 策略一致）

---

### 10. 重新測試 4 本書

**Conda 環境變數問題**:
- 在 Bash 中無法直接讀取 `ANTHROPIC_API_KEY`
- 發現：Conda 環境變數與 Bash 環境變數是分開的
- Conda 環境變數設定在 `$CONDA_PREFIX/etc/conda/activate.d/` 目錄下
- 解決方案：使用 `conda run -n epub-utils` 執行命令

```bash
conda run -n epub-utils python main.py --epub epubs/178998.epub --strategy mapreduce
```

**測試結果（更新後）**:

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998 (原子習慣) | 2,652 字元 | 2,734 字元 |
| 318347 (我可能錯了) | 2,620 字元 | 2,628 字元 |
| 362484 (納瓦爾寶典) | 2,667 字元 | 2,339 字元 |
| 424489 (世界盡頭的咖啡館) | 2,728 字元 | 2,630 字元 |

**結論**: 兩種策略現在產生相近長度的全書摘要

---

### 11. 專案結構與安裝方式討論

**根專案 (epub-utils) 的兩套安裝系統**:

| 系統 | 檔案 | 用途 |
|------|------|------|
| setuptools | `setup.py` | PyPI 發布用，版本規格較彈性 |
| requirements | `requirements/*.txt` | 開發用，版本固定 |

**快速安裝**:
```bash
pip install -e .                    # 安裝套件本身（讀取 setup.py）
pip install -r requirements.txt     # 安裝開發依賴
```

**entry_points 機制**:
- `setup.py` 中的 `entry_points` 註冊 CLI 命令
- `pip install -e .` 會在 `$CONDA_PREFIX/bin/` 建立執行檔
- 執行檔內容為 Python script，呼叫 `epub_utils.cli:main`

**重要澄清**:
- `pip install -e .` 和 `pip install -r requirements.txt` 是獨立的
- 執行一個不會自動執行另一個
- 現代專案傾向使用 `pyproject.toml` 統一兩套系統

---

### 12. pytest 相關知識

**pytest.ini 配置**:
```ini
[pytest]
testpaths = tests
addopts = -v --tb=short
```
- `testpaths`: 指定測試目錄
- `addopts`: 預設命令列參數（-v 詳細輸出，--tb=short 簡短追蹤）

**conftest.py 功能**:
- 定義 fixtures（如 `doc_path` 提供測試用 EPUB 路徑）
- Fixtures 可被多個測試檔案共享
- 支援 scope 設定（function, class, module, session）

**test_cli.py 特點**:
- 使用 Click 的 `CliRunner` 測試 CLI 命令
- 使用 `@pytest.mark.parametrize` 參數化測試

---

### 13. 文檔化兩種策略比較

在 `CHANGELOG_CUSTOM.md` 新增「兩種策略的比較」章節：

**Map Reduce 流程**:
```
章節1 ──→ LLM ──→ 摘要1 ─┐
章節2 ──→ LLM ──→ 摘要2 ─┼──→ LLM ──→ 全書摘要
章節N ──→ LLM ──→ 摘要N ─┘
```

**Refine 流程**:
```
章節1 ───────────────→ LLM ──→ 摘要v1
章節2 + 摘要v1 ──────→ LLM ──→ 摘要v2
章節N + 摘要v(N-1) ──→ LLM ──→ 摘要vN ──→ 全書摘要
```

**技術差異**:
- Map Reduce: 章節獨立處理，可平行，截斷 300,000 字元/章
- Refine: 逐章迭代，帶入現有摘要，截斷 200,000 字元/章

---

### 14. Claude Code 對話合併問題

**問題**: 能否合併不同的 conversation？

**答案**: Claude Code 不支援直接合併對話。每個對話是獨立 session。

**替代方案**:
1. `claude --resume` 繼續之前的對話
2. Context 用盡時系統自動摘要延續
3. 在 CLAUDE.md 或專案文件中記錄重要資訊供後續對話參考
4. 建立 CLAUDE_CONVERSATION.md 記錄對話歷史（本檔案）

---

### 15. Git 提交記錄（續）

```
73e94cf Add comparison of Map Reduce vs Refine summarization strategies
3b4978d Add CLAUDE.md documentation for development setup
4533f97 Update Map Reduce book summary length to match Refine strategy
```

---

### 已更新檔案（續）

- `llm.py` - 修改 Map Reduce 全書摘要長度（300-500 → 500-800）
- `CHANGELOG_CUSTOM.md` - 新增測試結果、策略比較、變更記錄
- `/CLAUDE.md` (根專案) - 新增安裝說明
- `/CLAUDE_zh.md` (根專案) - 新增安裝說明（中文版）
- `CLAUDE_CONVERSATION.md` - 新增對話續篇（本次更新）

---

### 16. Click 的 CliRunner 說明

`CliRunner` 是 Click 框架提供的測試工具，用來在測試環境中模擬執行 CLI 命令。

**主要功能**:
- 不需要真正啟動子程序，直接在 Python 中執行 CLI 命令
- 捕獲輸出（stdout/stderr）和 exit code
- 模擬使用者輸入

**簡單範例**:
```python
from click.testing import CliRunner
from epub_utils.cli import main

def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ['--help'])

    assert result.exit_code == 0
    assert 'Usage:' in result.output
```

**result 物件包含**:
- `result.exit_code` - 退出碼（0 表示成功）
- `result.output` - 標準輸出內容
- `result.exception` - 若發生例外，會存在這裡

**優點**:
- 測試速度快（不需 fork 子程序）
- 可直接 assert 輸出內容
- 環境隔離，不影響真實系統

這是測試 Click 應用程式的標準做法，比用 `subprocess` 呼叫 CLI 更簡潔有效。
