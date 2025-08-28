"""Text processing utilities for document chunking and preprocessing."""

import re
from typing import List


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks for vector embeddings.
    
    Args:
        text: The text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or chunk_size <= 0:
        return []
    
    # Clean and normalize text
    text = clean_text(text)
    
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If this isn't the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence endings within the last 100 characters
            sentence_break = find_sentence_boundary(text, start, end)
            if sentence_break > start:
                end = sentence_break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Calculate next start position with overlap
        start = max(start + 1, end - overlap)
        
        # Prevent infinite loop
        if start >= len(text):
            break
    
    return chunks


def find_sentence_boundary(text: str, start: int, preferred_end: int) -> int:
    """Find the best place to break text at a sentence boundary."""
    # Look for sentence endings in the last portion of the chunk
    search_start = max(start, preferred_end - 100)
    search_text = text[search_start:preferred_end]
    
    # Find the last occurrence of sentence-ending punctuation
    sentence_endings = r'[.!?]\s+'
    matches = list(re.finditer(sentence_endings, search_text))
    
    if matches:
        # Return position after the sentence ending
        last_match = matches[-1]
        return search_start + last_match.end()
    
    # If no sentence boundary found, try paragraph breaks
    if '\n\n' in search_text:
        last_paragraph = search_text.rfind('\n\n')
        return search_start + last_paragraph + 2
    
    # Fallback to word boundary
    if ' ' in search_text:
        last_space = search_text.rfind(' ')
        return search_start + last_space + 1
    
    # No good boundary found, use preferred end
    return preferred_end


def clean_text(text: str) -> str:
    """Clean and normalize text for processing."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    # Normalize line breaks
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    
    # Remove excessive newlines but preserve paragraph structure
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract key terms from text (simple implementation)."""
    if not text:
        return []
    
    # Simple keyword extraction based on word frequency
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter common stop words
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'can', 'this', 'that', 'these', 'those', 'a', 'an', 'as', 'from', 'up',
        'out', 'off', 'over', 'under', 'again', 'further', 'then', 'once'
    }
    
    # Count word frequencies
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) >= 3:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    keywords = sorted(word_freq.keys(), key=lambda w: word_freq[w], reverse=True)
    return keywords[:max_keywords]


def summarize_text(text: str, max_sentences: int = 3) -> str:
    """Generate a simple extractive summary of text."""
    if not text:
        return ""
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= max_sentences:
        return '. '.join(sentences) + '.'
    
    # Simple approach: take first, middle, and last sentences
    if max_sentences == 3 and len(sentences) >= 3:
        selected = [
            sentences[0],
            sentences[len(sentences) // 2],
            sentences[-1]
        ]
    else:
        # Take evenly spaced sentences
        step = max(1, len(sentences) // max_sentences)
        selected = sentences[::step][:max_sentences]
    
    return '. '.join(selected) + '.'