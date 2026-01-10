"""
EPUB Summarization Module

This module provides functionality to:
1. Parse EPUB table of contents
2. Extract chapter content
3. Generate chapter and book summaries
"""

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

from epub_utils import Document
from epub_utils.navigation.base import NavigationItem


@dataclass
class ChapterInfo:
	"""Represents a chapter with its content and summary."""

	title: str
	target: str  # relative path to content file
	level: int
	content: str = ''
	summary: str = ''
	children: List['ChapterInfo'] = field(default_factory=list)


@dataclass
class BookSummary:
	"""Represents the complete book summary."""

	title: str
	chapters: List[ChapterInfo]
	full_summary: str = ''


class EPUBSummarizer:
	"""Extract and summarize EPUB book content."""

	def __init__(self, epub_path: str):
		"""
		Initialize the summarizer with an EPUB file.

		Args:
			epub_path: Path to the EPUB file.
		"""
		self.doc = Document(epub_path)
		self.package_href = self.doc.package_href
		self._nav_base_path = self._get_nav_base_path()
		self._spine_hrefs = self._build_spine_hrefs()
		self._href_to_spine_index = {href: i for i, href in enumerate(self._spine_hrefs)}

	def _get_nav_base_path(self) -> str:
		"""Get the base path for resolving navigation file relative paths."""
		# Try EPUB 3 nav first, then NCX
		nav_href = self.doc.package.nav_href or self.doc.package.toc_href
		if nav_href:
			# Nav file is relative to package, get its directory
			full_nav_path = os.path.join(self.package_href, nav_href)
			return os.path.dirname(full_nav_path)
		return self.package_href

	def _build_spine_hrefs(self) -> List[str]:
		"""Build ordered list of content hrefs from spine."""
		spine_hrefs = []
		manifest = self.doc.package.manifest
		for itemref in self.doc.package.spine.itemrefs:
			idref = itemref['idref']
			item = manifest.find_by_id(idref)
			if item:
				# Build full path relative to package
				href = os.path.normpath(os.path.join(self.package_href, item['href']))
				spine_hrefs.append(href)
		return spine_hrefs

	def _get_spine_index_for_target(self, target: str) -> int:
		"""Get spine index for a TOC target path."""
		if not target:
			return -1
		# Remove fragment identifier
		target_path = target.split('#')[0]
		full_path = os.path.normpath(os.path.join(self._nav_base_path, target_path))
		return self._href_to_spine_index.get(full_path, -1)

	def get_chapters(self) -> List[ChapterInfo]:
		"""
		Extract chapter information from the EPUB table of contents.

		Returns:
			List of ChapterInfo objects representing the book structure.
		"""
		toc = self.doc.toc
		if toc is None:
			return []

		toc_items = toc.get_toc_items()
		return self._convert_nav_items(toc_items)

	def _convert_nav_items(self, nav_items: List[NavigationItem]) -> List[ChapterInfo]:
		"""Convert NavigationItems to ChapterInfo objects recursively."""
		chapters = []

		for item in nav_items:
			chapter = ChapterInfo(
				title=item.label,
				target=item.target,
				level=item.level,
			)

			# Recursively convert children
			if item.children:
				chapter.children = self._convert_nav_items(item.children)

			chapters.append(chapter)

		return chapters

	def _load_single_file_content(self, full_path: str) -> str:
		"""Load plain text content from a single file."""
		try:
			content = self.doc.get_file_by_path(full_path)
			if hasattr(content, 'to_plain'):
				return content.to_plain()
			return str(content)
		except Exception:
			return ''

	def _load_spine_range_content(self, start_index: int, end_index: int) -> str:
		"""
		Load content from a range of spine items.

		Args:
			start_index: Starting spine index (inclusive).
			end_index: Ending spine index (exclusive). Use -1 for end of spine.

		Returns:
			Combined plain text content.
		"""
		if start_index < 0:
			return ''

		if end_index < 0:
			end_index = len(self._spine_hrefs)

		content_parts = []
		for i in range(start_index, min(end_index, len(self._spine_hrefs))):
			href = self._spine_hrefs[i]
			text = self._load_single_file_content(href)
			if text.strip():
				content_parts.append(text)

		return '\n\n'.join(content_parts)

	def load_chapter_content(self, chapter: ChapterInfo, next_target: Optional[str] = None) -> str:
		"""
		Load the plain text content of a chapter.

		This method reads all spine items from the chapter's target up to
		(but not including) the next chapter's target. This handles EPUBs
		where chapter content spans multiple files.

		Args:
			chapter: ChapterInfo object with target path.
			next_target: Target path of the next chapter (to know where to stop).

		Returns:
			Plain text content of the chapter.
		"""
		if not chapter.target:
			return ''

		start_index = self._get_spine_index_for_target(chapter.target)
		if start_index < 0:
			# Fallback: try loading single file directly
			target_path = chapter.target.split('#')[0]
			full_path = os.path.normpath(os.path.join(self._nav_base_path, target_path))
			return self._load_single_file_content(full_path)

		# Determine end index
		if next_target:
			end_index = self._get_spine_index_for_target(next_target)
			if end_index < 0:
				end_index = start_index + 1
		else:
			end_index = start_index + 1

		# Load content from spine range
		content = self._load_spine_range_content(start_index, end_index)

		# If content is empty, try just the next spine item (for image-only targets)
		if not content.strip() and start_index + 1 < len(self._spine_hrefs):
			if end_index <= start_index + 1:
				end_index = start_index + 2
			content = self._load_spine_range_content(start_index, end_index)

		return content

	def _flatten_chapters_with_targets(self, chapters: List[ChapterInfo]) -> List[tuple]:
		"""Flatten chapters into a list of (chapter, target) tuples in order."""
		result = []
		for chapter in chapters:
			result.append((chapter, chapter.target))
			if chapter.children:
				result.extend(self._flatten_chapters_with_targets(chapter.children))
		return result

	def load_all_chapters(self, chapters: List[ChapterInfo]) -> None:
		"""
		Load content for all chapters using spine-based extraction.

		This method reads content between TOC entries, handling EPUBs where
		chapter content spans multiple spine items.

		Args:
			chapters: List of ChapterInfo objects to populate with content.
		"""
		# Flatten all chapters to get ordered list of targets
		flat_chapters = self._flatten_chapters_with_targets(chapters)

		# Load content for each chapter
		for i, (chapter, target) in enumerate(flat_chapters):
			# Get next chapter's target to know where to stop
			next_target = flat_chapters[i + 1][1] if i + 1 < len(flat_chapters) else None
			chapter.content = self.load_chapter_content(chapter, next_target)

	def summarize_chapter(self, chapter: ChapterInfo, summarizer_fn) -> str:
		"""
		Generate summary for a single chapter.

		Args:
			chapter: ChapterInfo with content loaded.
			summarizer_fn: Function that takes text and returns summary.

		Returns:
			Summary text.
		"""
		if not chapter.content:
			return ''

		chapter.summary = summarizer_fn(chapter.content, chapter.title)
		return chapter.summary

	def summarize_all_chapters(self, chapters: List[ChapterInfo], summarizer_fn) -> None:
		"""
		Generate summaries for all chapters recursively.

		Args:
			chapters: List of ChapterInfo objects with content loaded.
			summarizer_fn: Function that takes (content, title) and returns summary.
		"""
		for chapter in chapters:
			self.summarize_chapter(chapter, summarizer_fn)

			# Recursively summarize children
			if chapter.children:
				self.summarize_all_chapters(chapter.children, summarizer_fn)

	def generate_book_summary(
		self, chapters: List[ChapterInfo], summarizer_fn, book_title: Optional[str] = None
	) -> BookSummary:
		"""
		Generate a complete book summary from chapter summaries.

		Args:
			chapters: List of ChapterInfo with summaries.
			summarizer_fn: Function that takes combined summaries and returns book summary.
			book_title: Optional book title, defaults to metadata title.

		Returns:
			BookSummary object with full summary.
		"""
		# Get book title from metadata if not provided
		if book_title is None:
			book_title = self.doc.package.metadata.title or 'Unknown Title'

		# Collect all chapter summaries
		all_summaries = self._collect_summaries(chapters)
		combined_summaries = '\n\n'.join(all_summaries)

		# Generate book summary
		full_summary = summarizer_fn(combined_summaries, book_title)

		return BookSummary(
			title=book_title,
			chapters=chapters,
			full_summary=full_summary,
		)

	def _collect_summaries(self, chapters: List[ChapterInfo]) -> List[str]:
		"""Collect all chapter summaries recursively."""
		summaries = []

		for chapter in chapters:
			if chapter.summary:
				summaries.append(f"## {chapter.title}\n{chapter.summary}")

			if chapter.children:
				summaries.extend(self._collect_summaries(chapter.children))

		return summaries

	def _flatten_chapters(self, chapters: List[ChapterInfo]) -> List[ChapterInfo]:
		"""Flatten nested chapters into a single list."""
		result = []
		for chapter in chapters:
			result.append(chapter)
			if chapter.children:
				result.extend(self._flatten_chapters(chapter.children))
		return result

	def generate_refined_summary(
		self,
		chapters: List[ChapterInfo],
		refine_fn,
		finalize_fn,
		book_title: Optional[str] = None,
	) -> BookSummary:
		"""
		Generate a book summary using the refine strategy.

		This approach processes chapters sequentially, refining the summary
		with each new chapter's content.

		Args:
			chapters: List of ChapterInfo with content loaded.
			refine_fn: Function that refines summary with new chapter.
			finalize_fn: Function that finalizes the refined summary.
			book_title: Optional book title, defaults to metadata title.

		Returns:
			BookSummary object with full summary.
		"""
		# Get book title from metadata if not provided
		if book_title is None:
			book_title = self.doc.package.metadata.title or 'Unknown Title'

		# Flatten chapters for sequential processing
		flat_chapters = self._flatten_chapters(chapters)
		total_chapters = len(flat_chapters)

		if total_chapters == 0:
			return BookSummary(
				title=book_title,
				chapters=chapters,
				full_summary='',
			)

		# Process chapters sequentially with refine strategy
		current_summary = ''
		for i, chapter in enumerate(flat_chapters, 1):
			if not chapter.content:
				continue

			print(f"  精煉章節 {i}/{total_chapters}: {chapter.title}")
			current_summary = refine_fn(
				existing_summary=current_summary,
				new_content=chapter.content,
				new_title=chapter.title,
				book_title=book_title,
				chapter_index=i,
				total_chapters=total_chapters,
			)

		# Finalize the summary
		print("  最終整理摘要...")
		full_summary = finalize_fn(current_summary, book_title)

		return BookSummary(
			title=book_title,
			chapters=chapters,
			full_summary=full_summary,
		)


# === Example Usage ===

def example_summarizer(content: str, title: str) -> str:
	"""
	Placeholder summarizer function.
	Replace with actual LLM call (e.g., OpenAI, Anthropic, etc.)
	"""
	word_count = len(content.split())
	return f"[Summary of '{title}' - {word_count} words]"


def print_chapters_tree(chapters: List[ChapterInfo], indent: int = 0) -> None:
	"""Print chapter structure as a tree."""
	for chapter in chapters:
		prefix = '  ' * indent + ('├─ ' if indent > 0 else '')
		status = '[有內容]' if chapter.content else '[無內容]'
		print(f"{prefix}{chapter.title} {status}")
		if chapter.children:
			print_chapters_tree(chapter.children, indent + 1)


def print_summaries(chapters: List[ChapterInfo], indent: int = 0) -> None:
	"""Print chapter summaries."""
	for chapter in chapters:
		if chapter.summary:
			prefix = '#' * (indent + 2)
			print(f"\n{prefix} {chapter.title}\n")
			print(chapter.summary)

		if chapter.children:
			print_summaries(chapter.children, indent + 1)


def count_chapters(chapters: List[ChapterInfo]) -> int:
	"""Count total chapters including nested ones."""
	count = len(chapters)
	for chapter in chapters:
		count += count_chapters(chapter.children)
	return count


def sanitize_filename(title: str) -> str:
	"""Sanitize book title for use as filename."""
	# Remove or replace invalid filename characters
	sanitized = re.sub(r'[<>:"/\\|?*]', '', title)
	# Replace multiple spaces/underscores with single underscore
	sanitized = re.sub(r'[\s_]+', '_', sanitized)
	# Remove leading/trailing underscores
	sanitized = sanitized.strip('_')
	# Limit length
	if len(sanitized) > 100:
		sanitized = sanitized[:100]
	return sanitized


def main(
	epub_path: str,
	use_llm: bool = True,
	api_key: Optional[str] = None,
	model: Optional[str] = None,
	language: str = 'zh-TW',
	output_file: Optional[str] = None,
	strategy: str = 'map_reduce',
):
	"""
	Main function for EPUB summarization.

	Args:
		epub_path: Path to the EPUB file.
		use_llm: Whether to use Claude API (False for dry run).
		api_key: Anthropic API key.
		model: Claude model to use.
		language: Output language.
		output_file: Optional file to save results.
		strategy: Summarization strategy ('map_reduce' or 'refine').
	"""
	print(f"載入 EPUB: {epub_path}")

	# 1. Initialize summarizer
	summarizer = EPUBSummarizer(epub_path)

	# 2. Get chapter structure from TOC
	chapters = summarizer.get_chapters()
	total_chapters = count_chapters(chapters)
	print(f"找到 {len(chapters)} 個頂層章節，共 {total_chapters} 個章節")

	# 3. Load chapter content
	print("\n載入章節內容...")
	summarizer.load_all_chapters(chapters)

	print("\n章節結構：")
	print_chapters_tree(chapters)

	# 4. Generate summary based on strategy
	if strategy == 'refine':
		# Refine strategy: iteratively refine summary with each chapter
		if use_llm:
			from llm import create_refine_functions

			print(f"\n使用 Claude API 生成摘要 (策略: refine, 語言: {language})...")
			refine_fn, finalize_fn = create_refine_functions(
				api_key=api_key,
				model=model,
				language=language,
			)
		else:
			print("\n[測試模式] 使用假摘要 (refine 策略)...")
			def refine_fn(existing_summary, new_content, new_title, book_title, chapter_index, total_chapters):
				return f"{existing_summary}\n[{chapter_index}/{total_chapters}] {new_title}: {len(new_content)} chars"
			def finalize_fn(refined_summary, book_title):
				return f"[Final summary of '{book_title}']\n{refined_summary}"

		print("\n使用 Refine 策略生成摘要...")
		book_summary = summarizer.generate_refined_summary(chapters, refine_fn, finalize_fn)
	else:
		# Map-Reduce strategy: summarize each chapter then combine
		if use_llm:
			from llm import create_summarizer_functions

			print(f"\n使用 Claude API 生成摘要 (策略: map_reduce, 語言: {language})...")
			chapter_fn, book_fn = create_summarizer_functions(
				api_key=api_key,
				model=model,
				language=language,
			)
		else:
			print("\n[測試模式] 使用假摘要...")
			chapter_fn = example_summarizer
			book_fn = example_summarizer

		# 5. Generate chapter summaries
		print("\n生成章節摘要...")
		summarizer.summarize_all_chapters(chapters, chapter_fn)

		# 6. Generate book summary
		print("生成全書摘要...")
		book_summary = summarizer.generate_book_summary(chapters, book_fn)

	# 7. Output results
	output_lines = []
	output_lines.append(f"# {book_summary.title}")
	output_lines.append("")
	output_lines.append("## 全書摘要")
	output_lines.append("")
	output_lines.append(book_summary.full_summary)

	# Only include chapter summaries for map_reduce strategy
	if strategy == 'map_reduce':
		output_lines.append("")
		output_lines.append("## 章節摘要")

		def collect_summaries(chapters: List[ChapterInfo], level: int = 2) -> List[str]:
			lines = []
			for chapter in chapters:
				if chapter.summary:
					lines.append("")
					lines.append(f"{'#' * (level + 1)} {chapter.title}")
					lines.append("")
					lines.append(chapter.summary)
				if chapter.children:
					lines.extend(collect_summaries(chapter.children, level + 1))
			return lines

		output_lines.extend(collect_summaries(chapters))

	output_text = '\n'.join(output_lines)

	# Generate output filename if not specified
	if output_file is None:
		# Get epub directory for output
		epub_dir = os.path.dirname(os.path.abspath(epub_path))
		# Use epub filename (without extension) as base name
		epub_basename = os.path.splitext(os.path.basename(epub_path))[0]
		strategy_suffix = 'mapreduce' if strategy == 'map_reduce' else 'refine'
		output_file = os.path.join(epub_dir, f"{epub_basename}-{strategy_suffix}.md")

	# Save output
	with open(output_file, 'w', encoding='utf-8') as f:
		f.write(output_text)
	print(f"\n結果已儲存至: {output_file}")

	return book_summary


if __name__ == '__main__':
	import argparse

	parser = argparse.ArgumentParser(
		description='EPUB 書籍摘要生成工具',
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
範例:
  # 使用 Claude API 生成摘要 (預設 map_reduce 策略)
  # 輸出: book-mapreduce.md
  python summarize.py book.epub

  # 使用 refine 策略（適合長篇書籍）
  # 輸出: book-refine.md
  python summarize.py book.epub --strategy refine

  # 測試模式（不呼叫 API）
  python summarize.py book.epub --dry-run

  # 指定輸出檔案（覆蓋預設檔名）
  python summarize.py book.epub -o custom_summary.md

  # 使用英文輸出
  python summarize.py book.epub --language en

策略說明:
  map_reduce: 先為每個章節生成摘要，再合併成全書摘要（產生章節摘要）
  refine: 逐章節精煉摘要，最終產生全書摘要（僅產生全書摘要，更連貫）
		""",
	)

	parser.add_argument('epub_path', help='EPUB 檔案路徑')
	parser.add_argument(
		'--dry-run',
		action='store_true',
		help='測試模式，不呼叫 LLM API',
	)
	parser.add_argument(
		'--strategy',
		choices=['map_reduce', 'refine'],
		default='map_reduce',
		help='摘要策略（預設: map_reduce）',
	)
	parser.add_argument(
		'--api-key',
		help='Anthropic API Key（預設使用 ANTHROPIC_API_KEY 環境變數）',
	)
	parser.add_argument(
		'--model',
		help='Claude 模型名稱（預設: claude-sonnet-4-20250514）',
	)
	parser.add_argument(
		'--language',
		default='zh-TW',
		help='輸出語言（預設: zh-TW）',
	)
	parser.add_argument(
		'-o', '--output',
		help='輸出檔案路徑（預設: [epub檔名]-[策略].md）',
	)

	args = parser.parse_args()

	main(
		epub_path=args.epub_path,
		use_llm=not args.dry_run,
		api_key=args.api_key,
		model=args.model,
		language=args.language,
		output_file=args.output,
		strategy=args.strategy,
	)
