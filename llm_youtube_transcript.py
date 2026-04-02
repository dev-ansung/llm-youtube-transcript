import re
from typing import List

import llm
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    CouldNotRetrieveTranscript,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
from youtube_transcript_api._transcripts import FetchedTranscriptSnippet

# Regex patterns for extracting a video ID from various YouTube URL formats
_VIDEO_ID_PATTERNS = [
    r"(?:v=)([a-zA-Z0-9_-]{11})",          # ?v=VIDEO_ID  (watch URLs)
    r"youtu\.be/([a-zA-Z0-9_-]{11})",       # youtu.be/VIDEO_ID
    r"/shorts/([a-zA-Z0-9_-]{11})",         # /shorts/VIDEO_ID
    r"/embed/([a-zA-Z0-9_-]{11})",          # /embed/VIDEO_ID
    r"/v/([a-zA-Z0-9_-]{11})",              # /v/VIDEO_ID
]


def extract_video_id(url_or_id: str) -> str:
    """Extract a YouTube video ID from a URL or return the raw ID unchanged.

    Args:
        url_or_id: A full YouTube URL or an 11-character video ID.

    Returns:
        The 11-character video ID.

    Raises:
        ValueError: If no valid video ID can be found.
    """
    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url_or_id)
        if match:
            return match.group(1)

    # Accept bare 11-character video IDs (letters, digits, hyphens, underscores)
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url_or_id):
        return url_or_id

    raise ValueError(
        f"Could not extract a YouTube video ID from: {url_or_id!r}\n"
        "Supported formats: full watch URL, youtu.be short link, /shorts/ URL, "
        "or an 11-character video ID."
    )


def _snippets_to_text(snippets: List[FetchedTranscriptSnippet]) -> str:
    """Render transcript snippets as plain text (one line per snippet)."""
    return "\n".join(snippet.text for snippet in snippets)


@llm.hookimpl
def register_fragment_loaders(register):
    register("youtube", youtube_loader)


def youtube_loader(argument: str) -> llm.Fragment:
    """
    Fetch the transcript of a YouTube video and return it as a Fragment.

    Accepts a full YouTube URL or a bare 11-character video ID.

    Example usage:
      llm -f 'youtube:https://www.youtube.com/watch?v=dQw4w9WgXcQ' 'summarize'
      llm -f 'youtube:dQw4w9WgXcQ' 'summarize'
    """
    try:
        video_id = extract_video_id(argument)
    except ValueError:
        raise

    source_url = f"https://www.youtube.com/watch?v={video_id}"

    try:
        api = YouTubeTranscriptApi()
        try:
            transcript = api.fetch(video_id, languages=["en"])
        except NoTranscriptFound:
            # Fall back to the first available transcript for non-English videos
            transcript_list = api.list(video_id)
            transcript = next(iter(transcript_list)).fetch()
    except TranscriptsDisabled:
        raise ValueError(f"Transcripts are disabled for video: {video_id}")
    except VideoUnavailable:
        raise ValueError(f"Video unavailable: {video_id}")
    except NoTranscriptFound:
        raise ValueError(f"No transcript found for video: {video_id}")
    except CouldNotRetrieveTranscript as exc:
        raise ValueError(f"Could not retrieve transcript: {exc}")

    text = _snippets_to_text(list(transcript))
    return llm.Fragment(text, source=source_url)
