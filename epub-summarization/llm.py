"""
LLM Integration Module

Provides LLM API integration for text summarization.
Supports Claude (Anthropic) and OpenAI GPT models.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional

import anthropic
import openai


class BaseSummarizer(ABC):
	"""Abstract base class for LLM summarizers."""

	def __init__(self, max_tokens: int = 4096):
		self.max_tokens = max_tokens

	@abstractmethod
	def _call_api(self, prompt: str) -> str:
		"""Make API call to LLM. Must be implemented by subclasses."""
		pass

	def _get_language_instruction(self, language: str) -> str:
		"""Get the language instruction for prompts. Can be overridden by subclasses."""
		return f'請務必使用{language}撰寫'

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

		content = self._truncate_content(content)

		lang_instruction = self._get_language_instruction(language)
		prompt = f"""請為以下章節內容撰寫摘要。

章節標題：{title}

要求：
- {lang_instruction}
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

		lang_instruction = self._get_language_instruction(language)
		prompt = f"""請根據以下各章節摘要，為整本書撰寫綜合摘要。

書名：{book_title}

要求：
- {lang_instruction}
- 摘要長度約 500-800 字
- 綜合全書的主旨、核心論點和結論
- 呈現書籍的整體架構和邏輯脈絡
- 保持客觀、學術的風格

各章節摘要：
{chapter_summaries}

請直接輸出全書摘要內容，不需要任何前綴或標題。"""

		return self._call_api(prompt)

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
		lang_instruction = self._get_language_instruction(language)

		if not existing_summary:
			prompt = f"""請為以下書籍的第一個章節撰寫初始摘要。

書名：{book_title}
章節 {chapter_index}/{total_chapters}：{new_title}

要求：
- {lang_instruction}
- 摘要長度約 200-400 字
- 抓取章節的核心概念和重點
- 這是全書摘要的起點，後續會逐章精煉

章節內容：
{new_content}

請直接輸出摘要內容，不需要任何前綴或標題。"""
		else:
			prompt = f"""請根據新的章節內容，精煉並擴充現有的書籍摘要。

書名：{book_title}
目前進度：章節 {chapter_index}/{total_chapters}
新章節標題：{new_title}

現有摘要：
{existing_summary}

新章節內容：
{new_content}

要求：
- {lang_instruction}
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
		lang_instruction = self._get_language_instruction(language)
		prompt = f"""請將以下逐章精煉的書籍摘要進行最終整理和潤飾。

書名：{book_title}

逐章精煉摘要：
{refined_summary}

要求：
- {lang_instruction}
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


class ClaudeSummarizer(BaseSummarizer):
	"""Claude API wrapper for text summarization."""

	DEFAULT_MODEL = 'claude-haiku-4-5-20251001'

	def __init__(
		self,
		api_key: Optional[str] = None,
		model: Optional[str] = None,
		max_tokens: int = 2048,
	):
		"""
		Initialize Claude summarizer.

		Args:
			api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
			model: Model to use. Defaults to claude-haiku-4-5-20251001.
			max_tokens: Maximum tokens for response.
		"""
		super().__init__(max_tokens)
		self.api_key = api_key or os.environ.get('ANTHROPIC_API_KEY')
		if not self.api_key:
			raise ValueError(
				"API key required. Set ANTHROPIC_API_KEY environment variable "
				"or pass api_key parameter."
			)

		self.client = anthropic.Anthropic(api_key=self.api_key)
		self.model = model or self.DEFAULT_MODEL

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
			print(f"Claude API Error: {e}")
			raise


class OpenAISummarizer(BaseSummarizer):
	"""OpenAI API wrapper for text summarization."""

	DEFAULT_MODEL = 'gpt-4o'

	def __init__(
		self,
		api_key: Optional[str] = None,
		model: Optional[str] = None,
		max_tokens: int = 8192,
	):
		"""
		Initialize OpenAI summarizer.

		Args:
			api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
			model: Model to use. Defaults to gpt-4o.
			max_tokens: Maximum tokens for response.
		"""
		super().__init__(max_tokens)
		self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
		if not self.api_key:
			raise ValueError(
				"API key required. Set OPENAI_API_KEY environment variable "
				"or pass api_key parameter."
			)

		self.client = openai.OpenAI(api_key=self.api_key)
		self.model = model or self.DEFAULT_MODEL

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


class OllamaSummarizer(BaseSummarizer):
	"""Ollama API wrapper for text summarization using local models."""

	DEFAULT_MODEL = 'gpt-oss:20b'
	DEFAULT_BASE_URL = 'http://localhost:11434/v1'

	def __init__(
		self,
		model: Optional[str] = None,
		base_url: Optional[str] = None,
		max_tokens: int = 4096,
	):
		"""
		Initialize Ollama summarizer.

		Args:
			model: Model to use. Defaults to gpt-oss:20b.
			base_url: Ollama API base URL. Defaults to http://localhost:11434/v1.
			max_tokens: Maximum tokens for response.
		"""
		super().__init__(max_tokens)
		self.base_url = base_url or os.environ.get('OLLAMA_BASE_URL', self.DEFAULT_BASE_URL)
		self.model = model or self.DEFAULT_MODEL
		self._language = 'zh-TW(繁體中文/正體中文)'  # Default language, updated by high-level methods

		# Ollama uses OpenAI-compatible API
		self.client = openai.OpenAI(
			base_url=self.base_url,
			api_key='ollama',  # Ollama doesn't require API key but openai lib needs one
		)

	def _get_language_instruction(self, language: str) -> str:
		"""Get stronger language instruction for Ollama models."""
		return f'不論原始文本使用哪種語言，請務必以{language}撰寫輸出，禁止以其他語言為主體'

	def _expand_language(self, language: str) -> str:
		"""Expand language code to more descriptive form for better LLM understanding."""
		if language == 'zh-TW':
			return 'zh-TW(繁體中文/正體中文)'
		return language

	def summarize_chapter(self, content: str, title: str, language: str = 'zh-TW') -> str:
		"""Override to track current language."""
		self._language = self._expand_language(language)
		return super().summarize_chapter(content, title, language)

	def summarize_book(
		self, chapter_summaries: str, book_title: str, language: str = 'zh-TW'
	) -> str:
		"""Override to track current language."""
		self._language = self._expand_language(language)
		return super().summarize_book(chapter_summaries, book_title, language)

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
		"""Override to track current language."""
		self._language = self._expand_language(language)
		return super().refine_summary(
			existing_summary=existing_summary,
			new_content=new_content,
			new_title=new_title,
			book_title=book_title,
			chapter_index=chapter_index,
			total_chapters=total_chapters,
			language=language,
		)

	def finalize_refined_summary(
		self,
		refined_summary: str,
		book_title: str,
		language: str = 'zh-TW',
	) -> str:
		"""Override to track current language."""
		self._language = self._expand_language(language)
		return super().finalize_refined_summary(refined_summary, book_title, language)

	def _call_api(self, prompt: str) -> str:
		"""Make API call to Ollama with language reinforcement and post-processing."""
		# Add language reminder at the end of the prompt
		prompt_with_reminder = prompt + f'\n\n【重要提醒】請確保輸出完全使用{self._language}，禁止使用其他語言。'

		try:
			response = self.client.chat.completions.create(
				model=self.model,
				max_completion_tokens=self.max_tokens,
				messages=[{'role': 'user', 'content': prompt_with_reminder}],
				extra_body={
					'options': {
						'num_ctx': 64000,
						'num_predict': 2048,
					}
				},
			)
			content = response.choices[0].message.content
			result = content if content else ''

			# Post-process: convert to target language
			return self._convert_to_target_language(result)
		except openai.APIError as e:
			print(f"Ollama API Error: {e}")
			raise

	def _convert_to_target_language(self, text: str) -> str:
		"""Convert text to target language using Ollama."""
		if not text or not text.strip():
			return text

		conversion_prompt = f"""這是一段書籍摘要文本，請執行以下轉換：
1. 將非{self._language}的文字轉換為{self._language}
2. 已經是{self._language}的部分保持不變

直接輸出轉換結果，不要加任何說明：

{text}"""

		try:
			response = self.client.chat.completions.create(
				model=self.model,
				max_completion_tokens=self.max_tokens,
				messages=[{'role': 'user', 'content': conversion_prompt}],
				extra_body={
					'options': {
						'num_ctx': 64000,
						'num_predict': 2048,
					}
				},
			)
			content = response.choices[0].message.content
			return content if content else text
		except openai.APIError as e:
			print(f"Ollama API Error during conversion: {e}")
			return text  # Return original text if conversion fails


def _create_summarizer(
	provider: str = 'claude',
	api_key: Optional[str] = None,
	model: Optional[str] = None,
) -> BaseSummarizer:
	"""
	Create a summarizer instance based on provider.

	Args:
		provider: LLM provider ('claude' or 'openai').
		api_key: API key for the provider.
		model: Model to use.

	Returns:
		BaseSummarizer instance.

	Raises:
		ValueError: If provider is not supported.
	"""
	provider = provider.lower()
	if provider == 'claude':
		return ClaudeSummarizer(api_key=api_key, model=model)
	elif provider == 'openai':
		return OpenAISummarizer(api_key=api_key, model=model)
	elif provider == 'ollama':
		return OllamaSummarizer(model=model)
	else:
		raise ValueError(
			f"Unsupported provider: {provider}. "
			"Supported providers: 'claude', 'openai', 'ollama'"
		)


def create_summarizer_functions(
	api_key: Optional[str] = None,
	model: Optional[str] = None,
	language: str = 'zh-TW',
	provider: str = 'claude',
):
	"""
	Factory function to create summarizer functions for EPUBSummarizer.

	Args:
		api_key: API key for the provider.
		model: Model to use.
		language: Output language.
		provider: LLM provider ('claude' or 'openai').

	Returns:
		Tuple of (chapter_summarizer_fn, book_summarizer_fn)
	"""
	summarizer = _create_summarizer(provider=provider, api_key=api_key, model=model)

	def chapter_fn(content: str, title: str) -> str:
		return summarizer.summarize_chapter(content, title, language)

	def book_fn(chapter_summaries: str, book_title: str) -> str:
		return summarizer.summarize_book(chapter_summaries, book_title, language)

	return chapter_fn, book_fn


def create_refine_functions(
	api_key: Optional[str] = None,
	model: Optional[str] = None,
	language: str = 'zh-TW',
	provider: str = 'claude',
):
	"""
	Factory function to create refine strategy functions for EPUBSummarizer.

	Args:
		api_key: API key for the provider.
		model: Model to use.
		language: Output language.
		provider: LLM provider ('claude' or 'openai').

	Returns:
		Tuple of (refine_fn, finalize_fn)
	"""
	summarizer = _create_summarizer(provider=provider, api_key=api_key, model=model)

	def refine_fn(
		existing_summary: str,
		new_content: str,
		new_title: str,
		book_title: str,
		chapter_index: int,
		total_chapters: int,
	) -> str:
		return summarizer.refine_summary(
			existing_summary=existing_summary,
			new_content=new_content,
			new_title=new_title,
			book_title=book_title,
			chapter_index=chapter_index,
			total_chapters=total_chapters,
			language=language,
		)

	def finalize_fn(refined_summary: str, book_title: str) -> str:
		return summarizer.finalize_refined_summary(refined_summary, book_title, language)

	return refine_fn, finalize_fn
