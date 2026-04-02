"""Tests for llm-youtube-transcript plugin."""
from unittest.mock import MagicMock, patch

import llm
import pytest

from llm_youtube_transcript import (
    extract_video_id,
    youtube_loader,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VIDEO_ID = "dQw4w9WgXcQ"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


def _make_snippet(text: str, start: float, duration: float):
    """Create a FetchedTranscriptSnippet-like object for testing."""
    snippet = MagicMock()
    snippet.text = text
    snippet.start = start
    snippet.duration = duration
    return snippet


SAMPLE_SNIPPETS = [
    _make_snippet("Never gonna give you up", 0.0, 3.5),
    _make_snippet("Never gonna let you down", 3.5, 3.5),
    _make_snippet("Never gonna run around and desert you", 7.0, 4.0),
]


def _mock_api(snippets=None):
    """Return a mock YouTubeTranscriptApi instance whose fetch() returns snippets."""
    if snippets is None:
        snippets = SAMPLE_SNIPPETS
    mock_api = MagicMock()
    mock_api.fetch.return_value = iter(snippets)
    return mock_api


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

class TestExtractVideoId:
    def test_watch_url(self):
        assert extract_video_id(VIDEO_URL) == VIDEO_ID

    def test_watch_url_with_extra_params(self):
        assert extract_video_id(
            f"https://www.youtube.com/watch?v={VIDEO_ID}&t=42s&list=PL123"
        ) == VIDEO_ID

    def test_short_url(self):
        assert extract_video_id(f"https://youtu.be/{VIDEO_ID}") == VIDEO_ID

    def test_short_url_with_params(self):
        assert extract_video_id(f"https://youtu.be/{VIDEO_ID}?si=abc") == VIDEO_ID

    def test_shorts_url(self):
        assert extract_video_id(
            f"https://www.youtube.com/shorts/{VIDEO_ID}"
        ) == VIDEO_ID

    def test_embed_url(self):
        assert extract_video_id(
            f"https://www.youtube.com/embed/{VIDEO_ID}"
        ) == VIDEO_ID

    def test_bare_video_id(self):
        assert extract_video_id(VIDEO_ID) == VIDEO_ID

    def test_invalid_input_raises(self):
        with pytest.raises(ValueError, match="Could not extract"):
            extract_video_id("not-a-video-id")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("")

    def test_too_short_id_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("short")

    def test_too_long_id_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("a" * 12)


# ---------------------------------------------------------------------------
# Fragment loader
# ---------------------------------------------------------------------------

class TestYoutubeLoader:
    def test_returns_fragment(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(VIDEO_URL)
        assert isinstance(fragment, llm.Fragment)

    def test_source_is_canonical_url(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(VIDEO_URL)
        assert fragment.source == VIDEO_URL

    def test_text_contains_transcript(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(VIDEO_URL)
        text = str(fragment)
        assert "Never gonna give you up" in text
        assert "Never gonna let you down" in text

    def test_accepts_bare_video_id(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(VIDEO_ID)
        assert fragment.source == VIDEO_URL

    def test_accepts_short_url(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(f"https://youtu.be/{VIDEO_ID}")
        assert fragment.source == VIDEO_URL

    def test_accepts_shorts_url(self):
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_api(),
        ):
            fragment = youtube_loader(f"https://www.youtube.com/shorts/{VIDEO_ID}")
        assert fragment.source == VIDEO_URL

    def test_invalid_url_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not extract"):
            youtube_loader("not-a-valid-url-or-id")

    def test_transcripts_disabled_raises(self):
        from youtube_transcript_api._errors import TranscriptsDisabled
        mock_api = MagicMock()
        mock_api.fetch.side_effect = TranscriptsDisabled(VIDEO_ID)
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            with pytest.raises(ValueError, match="disabled"):
                youtube_loader(VIDEO_URL)

    def test_video_unavailable_raises(self):
        from youtube_transcript_api._errors import VideoUnavailable
        mock_api = MagicMock()
        mock_api.fetch.side_effect = VideoUnavailable(VIDEO_ID)
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            with pytest.raises(ValueError, match="unavailable"):
                youtube_loader(VIDEO_URL)

    def test_no_transcript_found_raises(self):
        from youtube_transcript_api._errors import NoTranscriptFound
        mock_api = MagicMock()
        mock_api.fetch.side_effect = NoTranscriptFound(VIDEO_ID, ["en"], {})
        mock_api.list.side_effect = NoTranscriptFound(VIDEO_ID, ["en"], {})
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            with pytest.raises(ValueError, match="No transcript"):
                youtube_loader(VIDEO_URL)

    def test_fallback_to_non_english(self):
        """When English is not available, falls back to the first available transcript."""
        from youtube_transcript_api._errors import NoTranscriptFound

        non_english_snippets = [_make_snippet("Bonjour le monde", 0.0, 2.0)]
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.fetch.return_value = iter(non_english_snippets)

        mock_api = MagicMock()
        mock_api.fetch.side_effect = NoTranscriptFound(VIDEO_ID, ["en"], {})
        mock_api.list.return_value = iter([mock_transcript_obj])

        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            fragment = youtube_loader(VIDEO_URL)

        assert "Bonjour le monde" in str(fragment)

