# llm-youtube-transcript

[![PyPI](https://img.shields.io/pypi/v/llm-youtube-transcript.svg)](https://pypi.org/project/llm-youtube-transcript/)
[![Tests](https://github.com/dev-ansung/llm-youtube-transcript/actions/workflows/test.yml/badge.svg)](https://github.com/dev-ansung/llm-youtube-transcript/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dev-ansung/llm-youtube-transcript/blob/main/LICENSE)

[LLM](https://llm.datasette.io/) plugin for fetching YouTube video transcripts and piping them into LLM prompts.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```bash
llm install llm-youtube-transcript
```

## Usage

Fetch a transcript and print it to stdout:

```bash
llm youtube-transcript https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

You can also pass a bare video ID or a `youtu.be` short link:

```bash
llm youtube-transcript dQw4w9WgXcQ
llm youtube-transcript https://youtu.be/dQw4w9WgXcQ
llm youtube-transcript https://www.youtube.com/shorts/dQw4w9WgXcQ
```

### Pipe into an LLM prompt

```bash
llm youtube-transcript dQw4w9WgXcQ | llm "summarize this transcript"
```

### Options

| Option | Default | Description |
|---|---|---|
| `-l/--language CODE` | *(video default)* | Request a specific language (e.g. `en`, `fr`). Repeat for a priority list. |
| `--format text\|json\|srt\|vtt` | `text` | Output format. |
| `--timestamps/--no-timestamps` | `--no-timestamps` | Prefix each line with a timestamp (text format only). |

### Format examples

**Plain text (default)**

```bash
llm youtube-transcript dQw4w9WgXcQ
# Never gonna give you up Never gonna let you down ...
```

**Plain text with timestamps**

```bash
llm youtube-transcript dQw4w9WgXcQ --timestamps
# [00:00] Never gonna give you up
# [00:03] Never gonna let you down
```

**JSON** – includes `text`, `start` (seconds), and `duration` (seconds) for every snippet:

```bash
llm youtube-transcript dQw4w9WgXcQ --format json
```

**SRT** (SubRip subtitles):

```bash
llm youtube-transcript dQw4w9WgXcQ --format srt
```

**WebVTT**:

```bash
llm youtube-transcript dQw4w9WgXcQ --format vtt
```

### Language selection

Pass `-l`/`--language` one or more times to specify a priority list. The first
available language wins:

```bash
# Try French first, fall back to English
llm youtube-transcript dQw4w9WgXcQ -l fr -l en
```

> **Note:** Auto-generated and manually-created captions are both returned by
> `youtube-transcript-api`. If you need to distinguish between them, use
> `--format json` and check the source URL.

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

```bash
cd llm-youtube-transcript
python -m venv venv
source venv/bin/activate
```

Install the dependencies and test dependencies:

```bash
pip install -e '.[test]'
```

Run the tests:

```bash
python -m pytest
```