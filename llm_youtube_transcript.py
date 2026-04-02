import json
import re
from typing import Iterable, List, Optional

import click
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


def _format_timestamp(seconds: float) -> str:
    """Format seconds as HH:MM:SS (hours omitted when zero)."""
    total_secs = int(seconds)
    hours, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def _format_srt_timestamp(seconds: float) -> str:
    """Format seconds as SRT timestamp HH:MM:SS,mmm."""
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_secs = total_ms // 1000
    hours, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    """Format seconds as WebVTT timestamp HH:MM:SS.mmm."""
    total_ms = int(seconds * 1000)
    ms = total_ms % 1000
    total_secs = total_ms // 1000
    hours, remainder = divmod(total_secs, 3600)
    mins, secs = divmod(remainder, 60)
    return f"{hours:02d}:{mins:02d}:{secs:02d}.{ms:03d}"


def format_as_text(
    snippets: Iterable[FetchedTranscriptSnippet], timestamps: bool
) -> str:
    """Render transcript snippets as plain text."""
    lines: List[str] = []
    for snippet in snippets:
        if timestamps:
            lines.append(f"[{_format_timestamp(snippet.start)}] {snippet.text}")
        else:
            lines.append(snippet.text)
    return ("\n".join(lines) if timestamps else " ".join(lines))


def format_as_json(snippets: Iterable[FetchedTranscriptSnippet]) -> str:
    """Render transcript snippets as JSON."""
    data = [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in snippets
    ]
    return json.dumps(data, indent=2)


def format_as_srt(snippets: Iterable[FetchedTranscriptSnippet]) -> str:
    """Render transcript snippets in SubRip (SRT) format."""
    lines: List[str] = []
    for i, snippet in enumerate(snippets, start=1):
        end = snippet.start + snippet.duration
        lines.append(str(i))
        lines.append(
            f"{_format_srt_timestamp(snippet.start)} --> {_format_srt_timestamp(end)}"
        )
        lines.append(snippet.text)
        lines.append("")
    return "\n".join(lines)


def format_as_vtt(snippets: Iterable[FetchedTranscriptSnippet]) -> str:
    """Render transcript snippets in WebVTT format."""
    lines: List[str] = ["WEBVTT", ""]
    for snippet in snippets:
        end = snippet.start + snippet.duration
        lines.append(
            f"{_format_vtt_timestamp(snippet.start)} --> {_format_vtt_timestamp(end)}"
        )
        lines.append(snippet.text)
        lines.append("")
    return "\n".join(lines)


@llm.hookimpl
def register_commands(cli: click.Group) -> None:
    @cli.command(name="youtube-transcript")
    @click.argument("url_or_id")
    @click.option(
        "-l",
        "--language",
        "languages",
        multiple=True,
        metavar="CODE",
        help=(
            "Language code to request (e.g. 'en', 'fr'). "
            "May be specified multiple times for a priority list. "
            "Defaults to the video's default language."
        ),
    )
    @click.option(
        "--format",
        "fmt",
        type=click.Choice(["text", "json", "srt", "vtt"], case_sensitive=False),
        default="text",
        show_default=True,
        help="Output format.",
    )
    @click.option(
        "--timestamps/--no-timestamps",
        default=False,
        show_default=True,
        help="Prefix each line with a timestamp (text format only).",
    )
    def youtube_transcript_cmd(
        url_or_id: str,
        languages: tuple,
        fmt: str,
        timestamps: bool,
    ) -> None:
        """Fetch the transcript of a YouTube video and print it to stdout.

        URL_OR_ID may be a full YouTube watch URL, a youtu.be short link,
        a /shorts/ URL, or a bare 11-character video ID.

        Examples:

        \b
            llm youtube-transcript https://www.youtube.com/watch?v=dQw4w9WgXcQ
            llm youtube-transcript dQw4w9WgXcQ --format json
            llm youtube-transcript dQw4w9WgXcQ -l en -l fr --timestamps
            llm youtube-transcript dQw4w9WgXcQ | llm "summarize this transcript"
        """
        # --- Resolve video ID ---
        try:
            video_id = extract_video_id(url_or_id)
        except ValueError as exc:
            raise click.ClickException(str(exc))

        # --- Fetch transcript ---
        try:
            api = YouTubeTranscriptApi()
            if languages:
                transcript = api.fetch(video_id, languages=list(languages))
            else:
                # No language requested – try English first, then fall back to
                # whatever transcript is available.
                try:
                    transcript = api.fetch(video_id, languages=["en"])
                except NoTranscriptFound:
                    transcript_list = api.list(video_id)
                    transcript = next(iter(transcript_list)).fetch()
        except TranscriptsDisabled:
            raise click.ClickException(
                f"Transcripts are disabled for video: {video_id}"
            )
        except VideoUnavailable:
            raise click.ClickException(
                f"Video unavailable: {video_id}"
            )
        except NoTranscriptFound:
            lang_hint = f" in language(s): {', '.join(languages)}" if languages else ""
            raise click.ClickException(
                f"No transcript found for video {video_id}{lang_hint}."
            )
        except CouldNotRetrieveTranscript as exc:
            raise click.ClickException(f"Could not retrieve transcript: {exc}")
        except Exception as exc:  # noqa: BLE001
            raise click.ClickException(f"Unexpected error: {exc}")

        # --- Format and output ---
        fmt = fmt.lower()
        if fmt == "text":
            click.echo(format_as_text(transcript, timestamps))
        elif fmt == "json":
            click.echo(format_as_json(transcript))
        elif fmt == "srt":
            click.echo(format_as_srt(transcript))
        elif fmt == "vtt":
            click.echo(format_as_vtt(transcript))
