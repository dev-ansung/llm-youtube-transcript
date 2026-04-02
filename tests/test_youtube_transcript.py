"""Tests for llm-youtube-transcript plugin."""
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from llm_youtube_transcript import (
    extract_video_id,
    format_as_json,
    format_as_srt,
    format_as_text,
    format_as_vtt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VIDEO_ID = "dQw4w9WgXcQ"


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


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

class TestExtractVideoId:
    def test_watch_url(self):
        assert extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ) == VIDEO_ID

    def test_watch_url_with_extra_params(self):
        assert extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123"
        ) == VIDEO_ID

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == VIDEO_ID

    def test_short_url_with_params(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=abc") == VIDEO_ID

    def test_shorts_url(self):
        assert extract_video_id(
            "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        ) == VIDEO_ID

    def test_embed_url(self):
        assert extract_video_id(
            "https://www.youtube.com/embed/dQw4w9WgXcQ"
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
# Formatting – text
# ---------------------------------------------------------------------------

class TestFormatAsText:
    def test_no_timestamps(self):
        result = format_as_text(SAMPLE_SNIPPETS, timestamps=False)
        assert result == (
            "Never gonna give you up "
            "Never gonna let you down "
            "Never gonna run around and desert you"
        )

    def test_with_timestamps(self):
        result = format_as_text(SAMPLE_SNIPPETS, timestamps=True)
        lines = result.splitlines()
        assert lines[0] == "[00:00] Never gonna give you up"
        assert lines[1] == "[00:03] Never gonna let you down"
        assert lines[2] == "[00:07] Never gonna run around and desert you"

    def test_timestamp_hours(self):
        long_snippet = _make_snippet("Late text", 3661.0, 2.0)
        result = format_as_text([long_snippet], timestamps=True)
        assert result == "[1:01:01] Late text"

    def test_empty_snippets(self):
        assert format_as_text([], timestamps=False) == ""
        assert format_as_text([], timestamps=True) == ""


# ---------------------------------------------------------------------------
# Formatting – JSON
# ---------------------------------------------------------------------------

class TestFormatAsJson:
    def test_produces_valid_json(self):
        result = format_as_json(SAMPLE_SNIPPETS)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 3

    def test_fields_present(self):
        result = format_as_json(SAMPLE_SNIPPETS)
        entry = json.loads(result)[0]
        assert entry["text"] == "Never gonna give you up"
        assert entry["start"] == 0.0
        assert entry["duration"] == 3.5

    def test_empty_snippets(self):
        result = format_as_json([])
        assert json.loads(result) == []


# ---------------------------------------------------------------------------
# Formatting – SRT
# ---------------------------------------------------------------------------

class TestFormatAsSrt:
    def test_structure(self):
        result = format_as_srt(SAMPLE_SNIPPETS)
        blocks = [b.strip() for b in result.split("\n\n") if b.strip()]
        assert blocks[0].startswith("1\n")
        assert "00:00:00,000 --> 00:00:03,500" in blocks[0]
        assert "Never gonna give you up" in blocks[0]

    def test_index_increments(self):
        result = format_as_srt(SAMPLE_SNIPPETS)
        assert "\n1\n" in "\n" + result
        assert "\n2\n" in result
        assert "\n3\n" in result


# ---------------------------------------------------------------------------
# Formatting – VTT
# ---------------------------------------------------------------------------

class TestFormatAsVtt:
    def test_starts_with_webvtt(self):
        result = format_as_vtt(SAMPLE_SNIPPETS)
        assert result.startswith("WEBVTT")

    def test_structure(self):
        result = format_as_vtt(SAMPLE_SNIPPETS)
        assert "00:00:00.000 --> 00:00:03.500" in result
        assert "Never gonna give you up" in result


# ---------------------------------------------------------------------------
# CLI command (via Click test runner)
# ---------------------------------------------------------------------------

def _get_cli():
    """Import and return the llm CLI for integration testing."""
    import llm.cli
    return llm.cli.cli


def _mock_transcript(snippets=None):
    """Return a mock YouTubeTranscriptApi instance."""
    if snippets is None:
        snippets = SAMPLE_SNIPPETS
    mock_api = MagicMock()
    mock_api.fetch.return_value = iter(snippets)
    return mock_api


class TestCliCommand:
    def test_text_output(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli, ["youtube-transcript", VIDEO_ID], catch_exceptions=False
            )
        assert result.exit_code == 0
        assert "Never gonna give you up" in result.output

    def test_json_output(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli,
                ["youtube-transcript", VIDEO_ID, "--format", "json"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["text"] == "Never gonna give you up"

    def test_srt_output(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli,
                ["youtube-transcript", VIDEO_ID, "--format", "srt"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "00:00:00,000 --> " in result.output

    def test_vtt_output(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli,
                ["youtube-transcript", VIDEO_ID, "--format", "vtt"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert result.output.startswith("WEBVTT")

    def test_timestamps_flag(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli,
                ["youtube-transcript", VIDEO_ID, "--timestamps"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "[00:00]" in result.output

    def test_full_url_input(self):
        runner = CliRunner()
        cli = _get_cli()
        with patch(
            "llm_youtube_transcript.YouTubeTranscriptApi",
            return_value=_mock_transcript(),
        ):
            result = runner.invoke(
                cli,
                [
                    "youtube-transcript",
                    f"https://www.youtube.com/watch?v={VIDEO_ID}",
                ],
                catch_exceptions=False,
            )
        assert result.exit_code == 0

    def test_invalid_url_shows_error(self):
        runner = CliRunner()
        cli = _get_cli()
        result = runner.invoke(
            cli, ["youtube-transcript", "not-a-valid-url-or-id"]
        )
        assert result.exit_code != 0
        assert "Error" in result.output

    def test_transcripts_disabled_error(self):
        from youtube_transcript_api._errors import TranscriptsDisabled
        runner = CliRunner()
        cli = _get_cli()
        mock_api = MagicMock()
        mock_api.fetch.side_effect = TranscriptsDisabled(VIDEO_ID)
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            result = runner.invoke(cli, ["youtube-transcript", VIDEO_ID])
        assert result.exit_code != 0
        assert "disabled" in result.output.lower()

    def test_video_unavailable_error(self):
        from youtube_transcript_api._errors import VideoUnavailable
        runner = CliRunner()
        cli = _get_cli()
        mock_api = MagicMock()
        mock_api.fetch.side_effect = VideoUnavailable(VIDEO_ID)
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            result = runner.invoke(cli, ["youtube-transcript", VIDEO_ID])
        assert result.exit_code != 0
        assert "unavailable" in result.output.lower()

    def test_no_transcript_found_error(self):
        from youtube_transcript_api._errors import NoTranscriptFound
        runner = CliRunner()
        cli = _get_cli()
        mock_api = MagicMock()
        mock_api.fetch.side_effect = NoTranscriptFound(VIDEO_ID, ["en"], {})
        with patch("llm_youtube_transcript.YouTubeTranscriptApi", return_value=mock_api):
            result = runner.invoke(cli, ["youtube-transcript", VIDEO_ID, "-l", "en"])
        assert result.exit_code != 0
        assert "transcript" in result.output.lower()
