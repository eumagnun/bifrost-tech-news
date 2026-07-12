# GEMINI.md — Blogpost Generator

## Project Overview

Automated blog post generator that scrapes the top story from Hacker News, creates an engaging PT-BR (Brazilian Portuguese) adaptation using Google Gemini, and generates a themed mascot illustration — all in a single script.

## Architecture

This is a **single-file Python CLI tool** (`gerar-blogpost.py`) with four sequential stages:

1. **Scraping** — Fetches the highest-voted story from the Hacker News front page using `requests` + `BeautifulSoup`.
2. **Text Generation** — Sends the story title to `gemini-3.1-flash-lite` (with thinking enabled at LOW level) to produce a 2000+ word professional, didactic post in Brazilian Portuguese. The post includes a creative **Dragon Ball use case** section that uses characters and scenarios from the Dragon Ball universe to explain the technical concept through analogy.
3. **Image Generation** — Uses the `gemini-3.1-flash-lite-image` model via the `client.interactions` API to generate an **anime-style Dragon Ball illustration** of the project mascot "Nano Bana" (a banana warrior in Saiyan armor with nanotech elements) contextualized to the article theme.
4. **HTML Rendering & Site Build** — Converts the Markdown output to HTML using the `markdown` library, saves it to `posts/{slug}.html` using `template.html`, saves the mascot image to `posts/images/{slug}.png`, appends post metadata to `posts.json`, and rebuilds `index.html` (displaying the 10 newest posts) and `archive.html` (displaying all posts) using `list_template.html`.

## Tech Stack

- **Language:** Python 3
- **AI SDK:** `google-genai` (unified client, `genai.Client`)
- **Models:** `gemini-3.1-flash-lite` (text), `gemini-3.1-flash-lite-image` (image)
- **Scraping:** `requests`, `beautifulsoup4`
- **Image Processing:** `Pillow` (PIL)
- **HTML Rendering:** `markdown` (with `extra`, `codehilite`, `nl2br`, `sane_lists` extensions)
- **Environment:** API key loaded from `.env` file via `python-dotenv`

## Key Conventions

- **Language:** All code comments, docstrings, user-facing print statements, and prompts are written in **Brazilian Portuguese (PT-BR)**.
- **Post length:** Generated posts must have a minimum of **2000 words**, with structured sections covering introduction, technical explanation, market impact, practical examples, and conclusion.
- **Dragon Ball use case:** Every post includes a dedicated section that builds a **detailed analogy using the Dragon Ball universe** (characters like Goku, Vegeta, Bulma, Piccolo, etc.) to explain the technical concept in a fun, accessible way.
- **Image style:** Illustrations are generated in **Dragon Ball anime style** (Akira Toriyama aesthetic) — with cel-shading, bold outlines, energy effects, and dynamic battle compositions.
- **Single-file design:** All functions live in `gerar-blogpost.py`. Do not split into multiple modules unless explicitly asked.
- **Gemini client initialization:** Use `genai.Client(api_key=...)` at module level. Do not instantiate multiple clients.
- **Image generation pattern:** Uses `client.interactions.create()` with `response_modalities=['image', 'text']`, then iterates `interaction.steps` to extract base64-encoded image data.
- **Error handling:** Functions raise exceptions on failure; `main()` wraps everything in a single try/except.
- **Output:** New posts are saved to `posts/{slug}.html`, images to `posts/images/{slug}.png`, and list pages `index.html` and `archive.html` are regenerated. All posts are tracked in `posts.json`.

## File Structure

```
blogpost-generator/
├── gerar-blogpost.py    # Main script (all logic)
├── template.html        # HTML template for individual posts
├── list_template.html   # HTML template for landing/archive list pages
├── requirements.txt     # Python dependencies
├── readme.md            # Setup instructions
├── index.html           # Landing page listing the 10 newest posts (regenerated)
├── archive.html         # Page listing all posts (regenerated)
├── posts.json           # Database of all posts metadata
├── posts/               # Generated posts directory
│   ├── images/          # Generated images directory
│   └── *.html           # Individual post pages
└── .venv/               # Virtual environment (not committed)
```

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your_key_here"
python gerar-blogpost.py
```

## Guidelines for AI Assistants

- Preserve the PT-BR language convention in all code comments, docstrings, and user-facing strings.
- When modifying Gemini API calls, use the `google-genai` SDK patterns already established (unified client, `types.GenerateContentConfig`, `client.interactions`).
- Do not add new dependencies without explicit approval.
- Keep the mascot "Nano Bana" concept intact in image generation prompts unless asked to change it.
