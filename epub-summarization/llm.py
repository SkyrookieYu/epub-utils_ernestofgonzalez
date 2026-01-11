"""
LLM Integration Module

Provides Claude API integration for text summarization.
"""

import os
from typing import Optional

import anthropic


class ClaudeSummarizer:
	"""Claude API wrapper for text summarization."""

	DEFAULT_MODEL = 'claude-sonnet-4-20250514'
	MAX_CONTENT_TOKENS = 100000  # Leave room for prompt and response

	def __init__(
		self,
		api_key: Optional[str] = None,
		model: Optional[str] = None,
		max_tokens: int = 1024,
	):
		"""
		Initialize Claude summarizer.

		Args:
			api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
			model: Model to use. Defaults to claude-sonnet-4-20250514.
			max_tokens: Maximum tokens for response.
		"""
		self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
		if not self.api_key:
			raise ValueError(
				"API key required. Set ANTHROPIC_API_KEY environment variable "
				"or pass api_key parameter."
			)

		self.client = anthropic.Anthropic(api_key=self.api_key)
		self.model = model or self.DEFAULT_MODEL
		self.max_tokens = max_tokens

	def summarize_chapter(self, content: str, title: str, language: str = 'zh-TW') -> str:
		"""
		Generate a summary for a single chapter.

		Args:
			content: Plain text content of the chapter.
			title: Chapter title.
			language: Output language (default: Traditional Chinese).

		Returns:
			Summary text.
		"""
		if not content or not content.strip():
			return ''

		# Truncate content if too long
		content = self._truncate_content(content)

		prompt = f"""請為以下章節內容撰寫摘要。

章節標題：{title}

要求：
- 使用{language}撰寫
- 摘要長度約 150-300 字
- 抓取章節的核心概念和重點
- 保持客觀、簡潔的風格

章節內容：
{content}

請直接輸出摘要內容，不需要任何前綴或標題。"""

		return self._call_api(prompt)

	def summarize_book(
		self, chapter_summaries: str, book_title: str, language: str = 'zh-TW'
	) -> str:
		"""
		Generate a book summary from chapter summaries.

		Args:
			chapter_summaries: Combined chapter summaries.
			book_title: Book title.
			language: Output language (default: Traditional Chinese).

		Returns:
			Book summary text.
		"""
		if not chapter_summaries or not chapter_summaries.strip():
			return ''

		prompt = f"""請根據以下各章節摘要，為整本書撰寫綜合摘要。

書名：{book_title}

要求：
- 使用{language}撰寫
- 摘要長度約 500-800 字
- 綜合全書的主旨、核心論點和結論
- 呈現書籍的整體架構和邏輯脈絡
- 保持客觀、學術的風格

各章節摘要：
{chapter_summaries}

請直接輸出全書摘要內容，不需要任何前綴或標題。"""

		return self._call_api(prompt)

	def _call_api(self, prompt: str) -> str:
		"""Make API call to Claude."""
		try:
			message = self.client.messages.create(
				model=self.model,
				max_tokens=self.max_tokens,
				messages=[
					{'role': 'user', 'content': prompt}
				],
			)
			return message.content[0].text
		except anthropic.APIError as e:
			print(f"API Error: {e}")
			raise

	def refine_summary(
		self,
		existing_summary: str,
		new_content: str,
		new_title: str,
		book_title: str,
		chapter_index: int,
		total_chapters: int,
		language: str = 'zh-TW',
	) -> str:
		"""
		Refine existing summary by incorporating new chapter content.

		Args:
			existing_summary: Current accumulated summary.
			new_content: Plain text content of the new chapter.
			new_title: Title of the new chapter.
			book_title: Title of the book.
			chapter_index: Current chapter index (1-based).
			total_chapters: Total number of chapters.
			language: Output language.

		Returns:
			Refined summary text.
		"""
		if not new_content or not new_content.strip():
			return existing_summary

		new_content = self._truncate_content(new_content, max_chars=200000)

		if not existing_summary:
			# First chapter - create initial summary
			prompt = f"""請為以下書籍的第一個章節撰寫初始摘要。

書名：{book_title}
章節 {chapter_index}/{total_chapters}：{new_title}

要求：
- 使用{language}撰寫
- 摘要長度約 200-400 字
- 抓取章節的核心概念和重點
- 這是全書摘要的起點，後續會逐章精煉

章節內容：
{new_content}

請直接輸出摘要內容，不需要任何前綴或標題。"""
		else:
			# Subsequent chapters - refine existing summary
			prompt = f"""請根據新的章節內容，精煉並擴充現有的書籍摘要。

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
- 摘要長度可隨內容增加適度擴展（目前建議 {min(300 + chapter_index * 50, 800)} 字左右）
- 避免重複，突出新增的核心概念
- 保持客觀、學術的風格

請直接輸出精煉後的完整摘要，不需要任何前綴或標題。"""

		return self._call_api(prompt)

	def finalize_refined_summary(
		self,
		refined_summary: str,
		book_title: str,
		language: str = 'zh-TW',
	) -> str:
		"""
		Finalize the refined summary with proper structure.

		Args:
			refined_summary: The accumulated refined summary.
			book_title: Title of the book.
			language: Output language.

		Returns:
			Final polished summary.
		"""
		prompt = f"""請將以下逐章精煉的書籍摘要進行最終整理和潤飾。

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

請直接輸出最終摘要，不需要任何前綴或標題。"""

		return self._call_api(prompt)

	def _truncate_content(self, content: str, max_chars: int = 300000) -> str:
		"""Truncate content if too long."""
		if len(content) > max_chars:
			return content[:max_chars] + "\n\n[內容已截斷...]"
		return content


def create_summarizer_functions(
	api_key: Optional[str] = None,
	model: Optional[str] = None,
	language: str = 'zh-TW',
):
	"""
	Factory function to create summarizer functions for EPUBSummarizer.

	Args:
		api_key: Anthropic API key.
		model: Model to use.
		language: Output language.

	Returns:
		Tuple of (chapter_summarizer_fn, book_summarizer_fn)
	"""
	claude = ClaudeSummarizer(api_key=api_key, model=model)

	def chapter_fn(content: str, title: str) -> str:
		return claude.summarize_chapter(content, title, language)

	def book_fn(chapter_summaries: str, book_title: str) -> str:
		return claude.summarize_book(chapter_summaries, book_title, language)

	return chapter_fn, book_fn


def create_refine_functions(
	api_key: Optional[str] = None,
	model: Optional[str] = None,
	language: str = 'zh-TW',
):
	"""
	Factory function to create refine strategy functions for EPUBSummarizer.

	Args:
		api_key: Anthropic API key.
		model: Model to use.
		language: Output language.

	Returns:
		Tuple of (refine_fn, finalize_fn)
	"""
	claude = ClaudeSummarizer(api_key=api_key, model=model)

	def refine_fn(
		existing_summary: str,
		new_content: str,
		new_title: str,
		book_title: str,
		chapter_index: int,
		total_chapters: int,
	) -> str:
		return claude.refine_summary(
			existing_summary=existing_summary,
			new_content=new_content,
			new_title=new_title,
			book_title=book_title,
			chapter_index=chapter_index,
			total_chapters=total_chapters,
			language=language,
		)

	def finalize_fn(refined_summary: str, book_title: str) -> str:
		return claude.finalize_refined_summary(refined_summary, book_title, language)

	return refine_fn, finalize_fn
