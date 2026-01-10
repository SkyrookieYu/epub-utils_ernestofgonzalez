"""EPUB Summarization - Extract and summarize EPUB book chapters."""

from .summarize import BookSummary, ChapterInfo, EPUBSummarizer
from .llm import ClaudeSummarizer, create_summarizer_functions, create_refine_functions

__version__ = '0.1.0'

__all__ = [
	'EPUBSummarizer',
	'ChapterInfo',
	'BookSummary',
	'ClaudeSummarizer',
	'create_summarizer_functions',
	'create_refine_functions',
]
