# llm-youtube-transcript

[![PyPI](https://img.shields.io/pypi/v/llm-youtube-transcript.svg)](https://pypi.org/project/llm-youtube-transcript/)
[![Tests](https://github.com/dev-ansung/llm-youtube-transcript/actions/workflows/test.yml/badge.svg)](https://github.com/dev-ansung/llm-youtube-transcript/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/dev-ansung/llm-youtube-transcript/blob/main/LICENSE)

[LLM](https://llm.datasette.io/) plugin for loading YouTube video transcripts as [fragments](https://llm.datasette.io/en/stable/fragments.html).

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```bash
llm install llm-youtube-transcript
```

## Usage

Use the `youtube:` fragment prefix to load a transcript and pass it directly to an LLM prompt:

```bash
llm -f 'youtube:https://www.youtube.com/watch?v=dQw4w9WgXcQ' 'summarize this transcript'
```

You can also pass a bare video ID or any supported YouTube URL:

```bash
# Bare video ID
llm -f 'youtube:dQw4w9WgXcQ' 'summarize this transcript'

# youtu.be short link
llm -f 'youtube:https://youtu.be/dQw4w9WgXcQ' 'summarize this transcript'

# YouTube Shorts URL
llm -f 'youtube:https://www.youtube.com/shorts/dQw4w9WgXcQ' 'summarize this transcript'
```

### Combining with other fragments

You can combine the transcript with other fragments or system prompts:

```bash
llm -f 'youtube:dQw4w9WgXcQ' -s 'You are a helpful assistant.' 'give me the key points'
```

### Language fallback

The plugin tries to fetch the English transcript first. If no English transcript is available it automatically falls back to the first available transcript for that video.

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