# Humanizer mini-module

Source: `c:\Users\Rohan\Downloads\humanizer-main\humanizer-main`

This mini-module is a text-only reference for removing obvious AI-writing patterns from outbound copy and other internal writing.

## What it is

`humanizer` is a writing-editing framework based on Wikipedia's "Signs of AI writing" guidance. The goal is not just to remove robotic phrasing, but to make the writing sound like it came from a real person.

## What to use it for

Use this module when:
- Copy sounds too polished or too generic
- Variations feel structurally similar
- Emails contain AI wording, formulaic transitions, or over-explained claims
- You want a final cleanup pass before launch

## Core workflow

1. Identify obvious AI patterns.
2. Rewrite the sections that trigger them.
3. Keep the meaning intact.
4. Keep the intended voice.
5. Add some actual personality.
6. Do a final anti-AI audit pass:
   - "What makes the below so obviously AI generated?"
   - "Now make it not obviously AI generated."

## High-value patterns to watch for

### Content patterns
- Significance inflation
- Notability name-dropping
- Superficial `-ing` analysis
- Promotional language
- Vague attributions
- Formulaic "challenges" sections

### Language patterns
- AI vocabulary like `additionally`, `pivotal`, `showcase`, `testament`
- Copula avoidance such as `serves as`, `features`, `boasts`
- Negative parallelisms like `it's not just X, it's Y`
- Rule-of-three writing
- Synonym cycling
- False ranges

### Style patterns
- Em dash overuse
- Boldface overuse
- Inline-header lists
- Title Case headings everywhere
- Emojis in professional writing
- Curly quotes in copied chatbot output

### Communication patterns
- Chatbot artifacts like `I hope this helps`
- Knowledge-cutoff disclaimers
- Sycophantic tone

### Filler and hedging
- Filler phrases like `in order to`
- Excessive hedging like `could potentially possibly`
- Generic positive conclusions

## Voice rules

Avoiding AI patterns is only half the job. Good writing also needs a point of view.

Use these rules:
- Have opinions when appropriate
- Vary sentence rhythm
- Acknowledge complexity
- Use first person when it helps
- Let a little mess remain
- Prefer concrete feelings over generic abstraction

## Repo contents

This module keeps the original text references in Markdown:
- `humanizer/README.md`
- `humanizer/SKILL.md`
- `humanizer/WARP.md`

Treat `humanizer/SKILL.md` as the source of truth inside this mini-module.
