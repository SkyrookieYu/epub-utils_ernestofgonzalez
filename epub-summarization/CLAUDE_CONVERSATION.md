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

---

## 2026-01-12 OpenAI 支援開發與測試

### 17. 新增 OpenAI GPT 支援

**需求**: 在現有的 Claude API 支援之外，新增 OpenAI GPT 模型支援

**實作**:

1. **重構 llm.py - 抽象基底類別**:
```python
class BaseSummarizer(ABC):
    """Abstract base class for LLM summarizers."""

    def __init__(self, max_tokens: int = 4096):
        self.max_tokens = max_tokens

    @abstractmethod
    def _call_api(self, prompt: str) -> str:
        """Make API call to LLM. Must be implemented by subclasses."""
        pass

    # 共用方法: summarize_chapter, summarize_book, refine_summary, etc.
```

2. **新增 OpenAISummarizer 類別**:
```python
class OpenAISummarizer(BaseSummarizer):
    """OpenAI API wrapper for text summarization."""

    DEFAULT_MODEL = 'gpt-5-mini-2025-08-07'

    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[{'role': 'user', 'content': prompt}],
        )
        content = response.choices[0].message.content
        return content if content else ''
```

3. **更新工廠函數**:
```python
def _create_summarizer(provider: str = 'claude', ...) -> BaseSummarizer:
    if provider == 'claude':
        return ClaudeSummarizer(...)
    elif provider == 'openai':
        return OpenAISummarizer(...)
```

4. **更新 requirements.txt**:
```
anthropic>=0.40.0
openai>=1.0.0
```

5. **更新 __init__.py 匯出**:
```python
from .llm import (
    BaseSummarizer,
    ClaudeSummarizer,
    OpenAISummarizer,
    create_summarizer_functions,
    create_refine_functions,
)
```

---

### 18. 修改輸出檔名格式

**需求**: 將輸出檔名從 `[檔名]-[策略].md` 改為 `[檔名]-[策略]-[provider].md`

**新格式範例**:
- `178998-mapreduce-claude.md`
- `178998-mapreduce-openai.md`

**修改 summarize.py**:
```python
provider_suffix = provider.lower()
output_file = os.path.join(
    epub_dir,
    f"{epub_basename}-{strategy_suffix}-{provider_suffix}.md"
)
```

---

### 19. OpenAI API 問題排查

#### 問題 1: `max_tokens` 不支援

**錯誤訊息**:
```
'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead.
```

**解決**: 將 OpenAI API 呼叫從 `max_tokens` 改為 `max_completion_tokens`

---

#### 問題 2: max_tokens 預設值太小

**錯誤訊息**:
```
Could not finish the message because max_tokens or model output limit was reached
```

**解決**: 將 `BaseSummarizer` 的 `max_tokens` 預設值從 1024 增加到 4096

---

#### 問題 3: GPT-5-mini 模型回傳空內容

**現象**:
- 章節摘要部分生成正常
- 全書摘要經常為空

**調查過程**:

1. 最初使用 `gpt-5-mini` → 空內容
2. 改用 `gpt-4o-mini` → 正常運作
3. 用戶指出正確名稱為 `gpt-5-mini-2025-08-07` → 仍有空內容
4. 嘗試 `gpt-5-nano-2025-08-07` → 仍為空

**Debug 輸出**:
```python
Content: ''
Finish reason: length
Usage: CompletionUsage(
    completion_tokens=100,
    prompt_tokens=8,
    total_tokens=108,
    completion_tokens_details=CompletionTokensDetails(
        reasoning_tokens=100,  # ← 問題所在
        ...
    )
)
```

**根本原因**:
GPT-5 系列是 reasoning model，會使用 `reasoning_tokens` 進行內部推理。當 `max_completion_tokens` 設定不夠大時，所有 token 都被用於推理，導致輸出內容為空。

---

### 20. OpenAI 測試結果

使用 `gpt-5-mini-2025-08-07` 模型測試 4 本 EPUB:

| 檔案 | 全書摘要 | 章節摘要 | 備註 |
|------|----------|----------|------|
| 178998.epub (原子習慣) | ✓ | ✓ | 第二次執行才成功 |
| 318347.epub (我可能錯了) | ✓ | ✓ | |
| 362484.epub (納瓦爾寶典) | ✓ | ✓ | |
| 424489.epub (世界盡頭的咖啡館) | ✗ | ✓ | 重複測試仍為空 |

**輸出檔案位置**: `epubs/` 目錄
- `178998-mapreduce-openai.md`
- `318347-mapreduce-openai.md`
- `362484-mapreduce-openai.md`
- `424489-mapreduce-openai.md`

---

### 21. GPT-5 Reasoning Model 的限制

**發現**:
- GPT-5 系列（如 gpt-5-mini, gpt-5-nano）是 reasoning model
- 與 GPT-4 系列不同，會額外使用 reasoning tokens
- `finish_reason: length` 表示達到 token 上限
- 當 prompt 較複雜或輸入較長時，可能所有 token 都用於推理，無輸出內容

**可能的解決方案**:
1. 大幅增加 `max_completion_tokens`（如 8192 或更高）
2. 改用 `gpt-4o-mini` 等非 reasoning model
3. 簡化 prompt 以減少推理需求

**結論**:
GPT-5-mini 模型在 epub-summarization 場景下不穩定，3/4 的書籍能正常產生全書摘要，但 424489.epub 持續失敗。建議使用 Claude 或 GPT-4 系列以獲得更穩定的結果。

---

### 技術筆記補充

#### Conda 環境變數與 Bash 環境變數

再次遇到環境變數問題：

```bash
# 這不會讀取 conda 環境變數
python summarize.py ...

# 需要用 conda run 執行
conda run -n epub-utils python summarize.py ...
```

**查看 conda 環境變數**:
```bash
conda run -n epub-utils env | grep OPENAI
```

#### OpenAI 模型列表查詢

```python
import openai
client = openai.OpenAI()
models = client.models.list()
for m in models.data:
    if 'gpt-5' in m.id:
        print(m.id)
```

---

### 22. 修正 GPT-5 Reasoning Tokens 問題

**發現**: GPT-5 系列有 `reasoning_effort` 參數可控制 reasoning tokens 的使用量

**OpenAI 官方文件說明**:
- 早期 reasoning model（如 o3）支援 `low`, `medium`, `high` 三種設定
- GPT-5.2 新增 `none` 選項，為預設值，提供較低延遲
- 設定為 `none` 時，若需要推理，應在 prompt 中鼓勵模型「思考」或列出步驟

**修改 llm.py**:
```python
def _call_api(self, prompt: str) -> str:
    """Make API call to OpenAI."""
    try:
        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            reasoning_effort='none',  # Disable reasoning tokens for GPT-5 models
            messages=[
                {'role': 'user', 'content': prompt}
            ],
        )
        content = response.choices[0].message.content
        return content if content else ''
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise
```

**預期效果**: 減少 reasoning tokens 後，更多 completion tokens 會用於實際輸出，解決全書摘要為空的問題。

---

### 23. 測試結果 - reasoning_effort 修正

**問題**: `gpt-5-mini-2025-08-07` 不支援 `reasoning_effort='none'`

**錯誤訊息**:
```
Unsupported value: 'reasoning_effort' does not support 'none' with this model.
Supported values are: 'minimal', 'low', 'medium', and 'high'.
```

**修正**: 將 `reasoning_effort` 從 `'none'` 改為 `'minimal'`

```python
reasoning_effort='minimal',  # Minimize reasoning tokens for GPT-5 models
```

**測試結果**: 424489.epub（之前持續失敗的檔案）現在成功產生完整的全書摘要！

**結論**:
- GPT-5.2 支援 `'none'` 選項
- GPT-5-mini 系列只支援 `'minimal', 'low', 'medium', 'high'`
- 使用 `'minimal'` 可有效減少 reasoning tokens，讓更多 token 用於輸出內容

---

### 24. 進一步測試 - GPT-5-mini 仍不穩定

使用 `reasoning_effort='minimal'` 測試其他檔案：

| 檔案 | gpt-5-mini 全書摘要 |
|------|---------------------|
| 424489.epub (世界盡頭的咖啡館) | ✓ 成功 |
| 318347.epub (我可能錯了) | ✓ 成功（非常詳細）|
| 362484.epub (納瓦爾寶典) | ✗ 空白 |

**結論**: GPT-5-mini 即使加了 `reasoning_effort='minimal'`，仍有不穩定的情況。

---

### 25. 改用 gpt-4o 模型

嘗試使用 `gpt-4o` 時發現錯誤：

```
Unrecognized request argument supplied: reasoning_effort
```

**原因**: `gpt-4o` 不是 reasoning model，不支援 `reasoning_effort` 參數。

**修正 llm.py**: 根據模型名稱動態決定是否加入 `reasoning_effort`

```python
def _call_api(self, prompt: str) -> str:
    """Make API call to OpenAI."""
    try:
        # Build request parameters
        params = {
            'model': self.model,
            'max_completion_tokens': self.max_tokens,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        # Only add reasoning_effort for GPT-5 models (reasoning models)
        if 'gpt-5' in self.model or 'o1' in self.model or 'o3' in self.model:
            params['reasoning_effort'] = 'minimal'

        response = self.client.chat.completions.create(**params)
        content = response.choices[0].message.content
        return content if content else ''
    except openai.APIError as e:
        print(f"OpenAI API Error: {e}")
        raise
```

---

### 26. gpt-4o 測試結果

使用 `gpt-4o` 模型重新測試：

```bash
conda run -n epub-utils python summarize.py ../epubs/362484.epub --provider openai --model gpt-4o
conda run -n epub-utils python summarize.py ../epubs/178998.epub --provider openai --model gpt-4o
```

| 檔案 | gpt-4o 全書摘要 |
|------|-----------------|
| 362484.epub (納瓦爾寶典) | ✓ 完整 |
| 178998.epub (原子習慣) | ✓ 完整 |

**結論**:
- `gpt-4o` 非常穩定，100% 成功率
- `gpt-5-mini` 有 reasoning tokens 問題，即使設定 `reasoning_effort='minimal'` 仍不穩定
- 建議使用 `gpt-4o` 或 Claude 以獲得穩定結果

---

### 27. OpenAI 模型選擇建議

| 模型 | 穩定性 | reasoning_effort | 建議用途 |
|------|--------|------------------|----------|
| gpt-4o | ✓ 穩定 | 不支援 | 推薦使用 |
| gpt-4o-mini | ✓ 穩定 | 不支援 | 成本較低的選擇 |
| gpt-5-mini | ✗ 不穩定 | 需設為 minimal | 不建議用於摘要任務 |
| gpt-5-nano | ✗ 不穩定 | 需設為 minimal | 不建議用於摘要任務 |

---

## 2026-01-12 完整模型測試與 max_tokens 修復

### 28. GPT-4o 完整測試（Map Reduce + Refine）

**測試命令**:
```bash
conda run -n epub-utils python summarize.py ../epubs/[檔案].epub --provider openai --model gpt-4o --strategy [策略]
```

**Map Reduce 測試結果**:

| 檔案 | 狀態 |
|------|------|
| 178998.epub (原子習慣) | ✓ |
| 318347.epub (我可能錯了) | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ |

**Refine 測試結果**:

| 檔案 | 狀態 |
|------|------|
| 178998.epub (原子習慣) | ✓ |
| 318347.epub (我可能錯了) | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ |

**結論**: GPT-4o 模型在兩種策略下都 100% 穩定。

---

### 29. Claude Sonnet 4 Map Reduce 測試

**測試命令**:
```bash
conda run -n epub-utils python summarize.py ../epubs/[檔案].epub --provider claude --model claude-sonnet-4-20250514 --strategy map_reduce
```

**測試結果**:

| 檔案 | 狀態 |
|------|------|
| 178998.epub (原子習慣) | ✓ |
| 318347.epub (我可能錯了) | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ |

---

### 30. 變更預設 Claude 模型

**修改**: 將預設 Claude 模型從 `claude-sonnet-4-20250514` 改為 `claude-haiku-4-5-20251001`

**修改位置**:
- `llm.py:213` - `ClaudeSummarizer.DEFAULT_MODEL`
- `summarize.py` - Help text 更新

**原因**: Haiku 4.5 成本較低，適合大量摘要任務。

---

### 31. Claude Sonnet 4 + Haiku 4.5 Refine 測試

**測試 Sonnet 4**:
```bash
conda run -n epub-utils python summarize.py ../epubs/[檔案].epub --provider claude --model claude-sonnet-4-20250514 --strategy refine
```

**測試 Haiku 4.5**:
```bash
conda run -n epub-utils python summarize.py ../epubs/[檔案].epub --provider claude --model claude-haiku-4-5-20251001 --strategy refine
```

**初始測試結果**:

| 檔案 | Sonnet 4 | Haiku 4.5 |
|------|----------|-----------|
| 178998.epub | ✓ | ✓ |
| 318347.epub | ✓ | ✓ |
| 362484.epub | ✓ | ✓ |
| 424489.epub | ✓ | ✓ |

---

### 32. 發現問題：Claude Refine 摘要結尾被截斷

**問題描述**: 用戶發現 Claude refine 產生的 8 個摘要檔案，大多數結尾不完整，句子在中間被切斷。

**問題範例**:
```
# 被截斷的結尾
- 362484-refine-claude-claude-sonnet-4.md: "...長期成功"
- 178998-refine-claude-claude-sonnet-4.md: "...心得分"
- 318347-refine-claude-claude-sonnet-4.md: "...體"
```

**調查過程**:
1. 讀取多個 Claude refine 輸出檔案
2. 檢查結尾發現句子在中間被截斷
3. 檢查 `llm.py` 中的 `max_tokens` 設定

**根本原因**:
`ClaudeSummarizer` 和 `OpenAISummarizer` 的 `max_tokens` 預設值為 1024，對於 `finalize_refined_summary` 函數（要求 500-800 字）來說太小。

```python
# 原本的設定
def __init__(self, ..., max_tokens: int = 1024):
```

---

### 33. 修復 max_tokens 問題

**修改**: 將 `max_tokens` 預設值從 1024 增加到 2048

**修改位置**:
- `llm.py:219` - `ClaudeSummarizer.__init__`
- `llm.py:265` - `OpenAISummarizer.__init__`

```python
# 修改後
def __init__(
    self,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_tokens: int = 2048,  # 從 1024 改為 2048
):
```

---

### 34. 驗證修復並重新執行測試

**驗證測試**: 先執行 424489.epub Haiku refine 確認修復有效

```bash
conda run -n epub-utils python summarize.py ../epubs/424489.epub --provider claude --model claude-haiku-4-5-20251001 --strategy refine
```

**結果**: 結尾完整，修復成功。

**重新執行其他 7 個測試**:

| 模型 | 檔案 | 狀態 |
|------|------|------|
| Sonnet 4 | 178998.epub | ✓ 結尾完整 |
| Sonnet 4 | 318347.epub | ✓ 結尾完整 |
| Sonnet 4 | 362484.epub | ✓ 結尾完整 |
| Sonnet 4 | 424489.epub | ✓ 結尾完整 |
| Haiku 4.5 | 178998.epub | ✓ 結尾完整 |
| Haiku 4.5 | 318347.epub | ✓ 結尾完整 |
| Haiku 4.5 | 362484.epub | ✓ 結尾完整 |

**最終驗證**:
```bash
for f in epubs/*-refine-claude-*.md; do echo "=== $(basename $f) ==="; tail -3 "$f"; done
```

所有 8 個 Claude refine 檔案現在都有完整的結尾。

---

### 35. 測試輸出檔案位置

**Sonnet 4 refine 檔案** (在 `epubs/` 目錄):
- `178998-refine-claude-claude-sonnet-4.md`
- `318347-refine-claude-claude-sonnet-4.md`
- `362484-refine-claude-claude-sonnet-4.md`
- `424489-refine-claude-claude-sonnet-4.md`

**Haiku 4.5 refine 檔案** (在 `epubs/Claude/` 目錄):
- `178998-refine-claude-claude-haiku-4-5.md`
- `318347-refine-claude-claude-haiku-4-5.md`
- `362484-refine-claude-claude-haiku-4-5.md`
- `424489-refine-claude-claude-haiku-4-5.md`

---

### 技術筆記補充

#### max_tokens vs max_completion_tokens

| Provider | 參數名稱 | 用途 |
|----------|----------|------|
| Claude | max_tokens | 控制輸出長度上限 |
| OpenAI (GPT-4) | max_completion_tokens | 控制輸出長度上限 |
| OpenAI (GPT-5) | max_completion_tokens | 控制輸出 + reasoning tokens 上限 |

#### 摘要長度與 token 需求估算

| 語言 | 字元/token 比例 |
|------|----------------|
| 英文 | ~4 字元/token |
| 中文 | ~1.5-2 字元/token |

對於 500-800 中文字的摘要，約需要 400-550 tokens。原本的 1024 tokens 理論上足夠，但實際上 LLM 可能產生更長的輸出，加上格式化（標題、分段），容易超出限制。

將 max_tokens 增加到 2048 提供足夠的緩衝空間。
