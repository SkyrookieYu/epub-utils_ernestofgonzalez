# EPUB Summarization 開發日誌

## 2026-01-11 進度記錄

### 已完成功能

1. **EPUB 解析與內容提取**
   - 支援 EPUB 3 (nav) 和 EPUB 2 (NCX) 目錄結構
   - 實作 spine-based 內容提取，處理章節內容跨多個檔案的情況
   - 支援 TOC 指向圖片檔而實際文字在後續檔案的 EPUB 結構

2. **兩種摘要策略**
   - Map Reduce: 先為每章生成摘要，再合併成全書摘要
   - Refine: 逐章精煉摘要，最終產生全書摘要

3. **輸出格式**
   - 輸出檔名: `[epub檔名]-[策略]-[provider]-[模型名稱].md`
   - 範例: `178998-mapreduce-openai-gpt-4o.md`
   - 輸出位置: 與 EPUB 檔案相同目錄

---

## Prompts 參數（Claude & OpenAI 共用）

> **說明**: Claude 和 OpenAI 使用相同的 prompts，定義在 `BaseSummarizer` 基底類別中。
> 兩者的差異僅在於 API 呼叫方式（`_call_api` 方法）。

---

### Map Reduce 策略 Prompts

#### 1. 章節摘要 (summarize_chapter)

| 項目 | 值 |
|------|-----|
| 位置 | `llm.py:44-57` |
| 長度要求 | 150-300 字 |
| 內容截斷 | 300,000 字元 |

```
請為以下章節內容撰寫摘要。

章節標題：{title}

要求：
- 使用{language}撰寫
- 摘要長度約 150-300 字
- 抓取章節的核心概念和重點
- 保持客觀、簡潔的風格

章節內容：
{content}

請直接輸出摘要內容，不需要任何前綴或標題。
```

#### 2. 全書摘要 (summarize_book)

| 項目 | 值 |
|------|-----|
| 位置 | `llm.py:78-92` |
| 長度要求 | 500-800 字（2026-01-11 更新，原為 300-500 字）|

```
請根據以下各章節摘要，為整本書撰寫綜合摘要。

書名：{book_title}

要求：
- 使用{language}撰寫
- 摘要長度約 500-800 字
- 綜合全書的主旨、核心論點和結論
- 呈現書籍的整體架構和邏輯脈絡
- 保持客觀、學術的風格

各章節摘要：
{chapter_summaries}

請直接輸出全書摘要內容，不需要任何前綴或標題。
```

---

### Refine 策略 Prompts

#### 1. 初始摘要 (refine_summary - 第一章)

| 項目 | 值 |
|------|-----|
| 位置 | `llm.py:127-141` |
| 長度要求 | 200-400 字 |
| 內容截斷 | 200,000 字元 |

```
請為以下書籍的第一個章節撰寫初始摘要。

書名：{book_title}
章節 {chapter_index}/{total_chapters}：{new_title}

要求：
- 使用{language}撰寫
- 摘要長度約 200-400 字
- 抓取章節的核心概念和重點
- 這是全書摘要的起點，後續會逐章精煉

章節內容：
{new_content}

請直接輸出摘要內容，不需要任何前綴或標題。
```

#### 2. 精煉摘要 (refine_summary - 後續章節)

| 項目 | 值 |
|------|-----|
| 位置 | `llm.py:143-163` |
| 長度要求 | 動態：`min(300 + chapter_index * 50, 800)` 字 |
| 內容截斷 | 200,000 字元 |

```
請根據新的章節內容，精煉並擴充現有的書籍摘要。

書名：{book_title}
目前進度：章節 {chapter_index}/{total_chapters}
新章節標題：{new_title}

現有摘要：
{existing_summary}

新章節內容：
{new_content}

要求：
- 使用{language}撰寫
- 將新章節的重點整合到現有摘要中
- 保持摘要的連貫性和邏輯流暢
- 摘要長度可隨內容增加適度擴展（目前建議 {suggested_length} 字左右）
- 避免重複，突出新增的核心概念
- 保持客觀、學術的風格

請直接輸出精煉後的完整摘要，不需要任何前綴或標題。
```

#### 3. 最終整理 (finalize_refined_summary)

| 項目 | 值 |
|------|-----|
| 位置 | `llm.py:184-199` |
| 長度要求 | 500-800 字 |

```
請將以下逐章精煉的書籍摘要進行最終整理和潤飾。

書名：{book_title}

逐章精煉摘要：
{refined_summary}

要求：
- 使用{language}撰寫
- 確保結構完整、邏輯清晰
- 摘要長度約 500-800 字
- 涵蓋全書的主旨、核心論點、主要方法和結論
- 保持客觀、學術的風格
- 適當分段以提高可讀性

請直接輸出最終摘要，不需要任何前綴或標題。
```

---

### API 呼叫差異

| Provider | API 呼叫方式 | 特殊參數 |
|----------|-------------|----------|
| Claude | `client.messages.create()` | 無 |
| OpenAI (gpt-4o) | `client.chat.completions.create()` | 無 |
| OpenAI (gpt-5) | `client.chat.completions.create()` | `reasoning_effort='minimal'` |

---

## 測試結果 (2026-01-11)

測試 EPUB 檔案: 178998.epub, 318347.epub, 362484.epub, 424489.epub

### 輸出檔案大小

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998 | 50KB | 2.8KB |
| 318347 | 54KB | 2.7KB |
| 362484 | 67KB | 2.5KB |
| 424489 | 34KB | 2.7KB |

**說明:**
- Map Reduce 檔案較大是因為包含所有章節摘要
- Refine 檔案僅包含全書摘要

### 全書摘要長度比較 (2026-01-11 更新後)

將 Map Reduce 全書摘要長度要求從 300-500 字調整為 500-800 字後的測試結果：

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998 (原子習慣) | 2,652 字元 | 2,734 字元 |
| 318347 (我可能錯了) | 2,620 字元 | 2,628 字元 |
| 362484 (納瓦爾寶典) | 2,667 字元 | 2,339 字元 |
| 424489 (世界盡頭的咖啡館) | 2,728 字元 | 2,630 字元 |

**說明:**
- 兩種策略現在產生相近長度的全書摘要
- 實際輸出長度（約 2,300-2,700 字元）超過 prompt 要求的 500-800 字
- LLM 傾向產生比指定長度更多的內容

---

## 兩種策略的比較

### 流程差異

**Map Reduce 策略流程：**
```
章節1 ──→ LLM ──→ 摘要1 ─┐
章節2 ──→ LLM ──→ 摘要2 ─┼──→ LLM ──→ 全書摘要
章節3 ──→ LLM ──→ 摘要3 ─┤
  ...                    │
章節N ──→ LLM ──→ 摘要N ─┘
```
- 每個章節獨立處理，可平行執行
- 最後合併所有章節摘要，產生全書摘要

**Refine 策略流程：**
```
章節1 ──────────────────────→ LLM ──→ 摘要v1
                                        ↓
章節2 + 摘要v1 ─────────────→ LLM ──→ 摘要v2
                                        ↓
章節3 + 摘要v2 ─────────────→ LLM ──→ 摘要v3
                                        ↓
  ...                                   ↓
                                        ↓
章節N + 摘要v(N-1) ─────────→ LLM ──→ 摘要vN
                                        ↓
                             LLM ──→ 全書摘要（最終整理）
```
- 逐章迭代處理，每次都帶入現有摘要
- 摘要隨章節推進而逐步精煉

---

### 技術比較

| 項目 | Map Reduce | Refine |
|------|------------|--------|
| **每次 LLM 呼叫輸入** | 單一章節內容 | 現有摘要 + 新章節內容 |
| **章節摘要長度** | 固定 150-300 字 | 動態：min(300 + index*50, 800) 字 |
| **內容截斷限制** | 300,000 字元/章節 | 200,000 字元/章節 |
| **章節間關聯** | 無（獨立處理） | 有（摘要累積脈絡） |
| **LLM 呼叫次數** | N+1 次（N章節 + 1全書） | N+1 次（N章節 + 1整理） |
| **可否平行處理** | 章節摘要可平行 | 必須循序處理 |
| **最終輸出** | 各章摘要 + 全書摘要 | 僅全書摘要 |

---

### 優缺點比較

#### Map Reduce

**優點：**
- 章節處理可平行化，速度較快
- 保留各章節獨立摘要，方便查閱特定章節
- 章節間不會互相干擾，適合內容獨立性高的書籍

**缺點：**
- 各章節摘要獨立產生，可能遺失章節間的邏輯連貫性
- 全書摘要是基於摘要的摘要，可能損失細節
- 輸出檔案較大（包含所有章節摘要）

#### Refine

**優點：**
- 摘要隨閱讀推進而精煉，保持整體連貫性
- 後面章節可參考前面的脈絡，產生更一致的敘事
- 輸出檔案精簡（僅全書摘要）

**缺點：**
- 必須循序處理，無法平行化，速度較慢
- 不保留各章節獨立摘要
- 後期章節的摘要可能被壓縮，早期內容佔比較高

---

### 使用建議

| 情境 | 建議策略 |
|------|----------|
| 想快速瀏覽各章節重點 | Map Reduce |
| 追求整體敘事連貫性 | Refine |
| 書籍各章獨立性高（如工具書、食譜） | Map Reduce |
| 書籍前後章節關聯緊密（如小說、論述） | Refine |
| 需要平行處理以加速 | Map Reduce |
| 只需要全書摘要，不需各章細節 | Refine |

---

## 變更記錄

### 2026-01-12 (續)
- [x] 修復 Claude refine 摘要結尾被截斷問題
  - 將 `max_tokens` 預設值從 1024 增加到 2048
  - 修改位置: `llm.py:219` (ClaudeSummarizer), `llm.py:265` (OpenAISummarizer)
- [x] 變更預設 Claude 模型
  - 從 `claude-sonnet-4-20250514` 改為 `claude-haiku-4-5-20251001`
  - 修改位置: `llm.py:213`
- [x] 完成完整模型測試
  - GPT-4o: Map Reduce ✓ (4/4), Refine ✓ (4/4)
  - Claude Sonnet 4: Map Reduce ✓ (4/4), Refine ✓ (4/4)
  - Claude Haiku 4.5: Refine ✓ (4/4)

### 2026-01-12
- [x] 新增 OpenAI GPT 模型支援
  - 重構 `llm.py`：新增 `BaseSummarizer` 抽象基底類別
  - 新增 `OpenAISummarizer` 類別
  - 更新工廠函數支援 `provider` 參數
  - 更新 `requirements.txt` 加入 `openai>=1.0.0`
- [x] 輸出檔名格式變更
  - 從 `[檔名]-[策略].md` 改為 `[檔名]-[策略]-[provider]-[模型名稱].md`
  - 例如: `178998-mapreduce-openai-gpt-4o.md`
  - 模型名稱會自動簡化（移除日期後綴如 `-20250514`）
- [x] 新增 `--provider` CLI 參數
- [x] 修正 GPT-5 reasoning model 問題
  - 加入 `reasoning_effort='minimal'` 參數（僅限 GPT-5/o1/o3 模型）

### 2026-01-11
- [x] 將 Map Reduce 全書摘要長度要求從 300-500 字調整為 500-800 字（與 Refine 策略一致）
  - 修改位置: `llm.py:102`

---

## OpenAI 模型支援 (2026-01-12)

### 支援的 Provider

| Provider | 預設模型 | 環境變數 |
|----------|----------|----------|
| claude | claude-haiku-4-5-20251001 | ANTHROPIC_API_KEY |
| openai | gpt-5-mini-2025-08-07 | OPENAI_API_KEY |

### 使用方式

```bash
# 使用 Claude（預設）
python summarize.py book.epub

# 使用 OpenAI
python summarize.py book.epub --provider openai

# 指定 OpenAI 模型
python summarize.py book.epub --provider openai --model gpt-4o
```

---

### GPT-5 Reasoning Model 問題

#### 問題描述

GPT-5 系列（gpt-5-mini, gpt-5-nano）是 reasoning model，會使用 `reasoning_tokens` 進行內部推理。當 token 預算不足時，所有 token 都被用於推理，導致輸出內容為空。

#### 錯誤現象

```python
Content: ''
Finish reason: length
Usage: CompletionUsage(
    completion_tokens=100,
    reasoning_tokens=100,  # 全部用於推理
)
```

#### 解決方案

加入 `reasoning_effort='minimal'` 參數以減少推理 token 消耗：

```python
# llm.py - OpenAISummarizer._call_api()
params = {
    'model': self.model,
    'max_completion_tokens': self.max_tokens,
    'messages': [{'role': 'user', 'content': prompt}],
}
# 只對 reasoning model 加入此參數
if 'gpt-5' in self.model or 'o1' in self.model or 'o3' in self.model:
    params['reasoning_effort'] = 'minimal'
```

---

### OpenAI 模型穩定性測試

| 模型 | 穩定性 | reasoning_effort | 備註 |
|------|--------|------------------|------|
| gpt-4o | ✓ 穩定 | 不支援 | **推薦使用** |
| gpt-4o-mini | ✓ 穩定 | 不支援 | 成本較低 |
| gpt-5-mini | ✗ 不穩定 | 需設為 minimal | 偶爾產生空白摘要 |
| gpt-5-nano | ✗ 不穩定 | 需設為 minimal | 偶爾產生空白摘要 |

#### 測試結果

**gpt-5-mini-2025-08-07 (reasoning_effort='minimal')**:

| 檔案 | 全書摘要 |
|------|----------|
| 178998.epub (原子習慣) | ✓ |
| 318347.epub (我可能錯了) | ✓ |
| 362484.epub (納瓦爾寶典) | ✗ 空白 |
| 424489.epub (世界盡頭的咖啡館) | ✓ |

**gpt-4o**:

| 檔案 | 全書摘要 |
|------|----------|
| 178998.epub (原子習慣) | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ |

**結論**: 建議使用 `gpt-4o` 或 `claude` 以獲得穩定結果。

---

## 完整測試結果 (2026-01-12)

### GPT-4o 測試

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998.epub (原子習慣) | ✓ | ✓ |
| 318347.epub (我可能錯了) | ✓ | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ | ✓ |

### Claude Sonnet 4 測試

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998.epub (原子習慣) | ✓ | ✓ |
| 318347.epub (我可能錯了) | ✓ | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ | ✓ |

### Claude Haiku 4.5 測試

| 檔案 | Map Reduce | Refine |
|------|------------|--------|
| 178998.epub (原子習慣) | ✓ | ✓ |
| 318347.epub (我可能錯了) | ✓ | ✓ |
| 362484.epub (納瓦爾寶典) | ✓ | ✓ |
| 424489.epub (世界盡頭的咖啡館) | ✓ | ✓ |

### max_tokens 修復記錄

**問題**: Claude refine 策略產生的摘要結尾被截斷

**原因**: `max_tokens` 預設值 1024 對於 500-800 字的中文摘要不足

**解決方案**: 將 `max_tokens` 從 1024 增加到 2048

**修改檔案**: `llm.py`
- 行 219: `ClaudeSummarizer.__init__` max_tokens 預設值
- 行 265: `OpenAISummarizer.__init__` max_tokens 預設值

---

## 待優化項目

- [x] ~~全書摘要長度可能過短，考慮調整 prompt 參數~~ (已完成)
- [x] ~~新增 OpenAI 模型支援~~ (已完成)
- [x] ~~修復 max_tokens 不足導致輸出被截斷問題~~ (已完成，1024 → 2048)
- [ ] 考慮調整 prompt 以控制實際輸出長度更接近指定範圍
- [ ] 考慮將預設 OpenAI 模型改為 gpt-4o（更穩定）
