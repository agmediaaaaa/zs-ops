# Humanizer

A Claude Code skill that removes signs of AI-generated writing from text, making it sound more natural and human.

## Installation

### Recommended

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/blader/humanizer.git ~/.claude/skills/humanizer
```

### Manual install/update

```bash
mkdir -p ~/.claude/skills/humanizer
cp SKILL.md ~/.claude/skills/humanizer/
```

## Usage

```text
/humanizer
[paste your text here]
```

Or ask directly:

```text
Please humanize this text: [your text]
```

## Overview

Based on [Wikipedia's "Signs of AI writing"](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing). The framework removes obvious AI-writing patterns and adds a final audit pass to catch anything still sounding synthetic.

## Pattern groups

- Content patterns
- Language patterns
- Style patterns
- Communication patterns
- Filler and hedging

## Version history

- 2.2.0 - Added a final audit and second-pass rewrite
- 2.1.1 - Fixed pattern 18 example
- 2.1.0 - Added before/after examples for all 24 patterns
- 2.0.0 - Complete rewrite based on raw Wikipedia article content
- 1.0.0 - Initial release

## License

MIT
