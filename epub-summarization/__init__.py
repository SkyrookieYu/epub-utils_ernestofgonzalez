"""EPUB Summarization - Extract and summarize EPUB book chapters."""

from .summarize import BookSummary, ChapterInfo, EPUBSummarizer
from .llm import (
	BaseSummarizer,
	ClaudeSummarizer,
	OpenAISummarizer,
	create_summarizer_functions,
	create_refine_functions,
)

__version__ = '0.1.0'

__all__ = [
	'EPUBSummarizer',
	'ChapterInfo',
	'BookSummary',
	'BaseSummarizer',
	'ClaudeSummarizer',
	'OpenAISummarizer',
	'create_summarizer_functions',
	'create_refine_functions',
]
