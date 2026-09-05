# AI Campus Assistant Agent

Web application for CEG, MIT, SAP, and ACT with college-scoped tools,
conversation history, source-aware scraping, RAG metadata, JWT
authentication, and optional LangGraph/OpenRouter tool calling.

## Run

```powershell
python -m pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:8000`; API docs are at `/docs`.
Copy `.env.example` to `.env` and set a newly generated
`OPENROUTER_API_KEY` to enable genuine LLM tool calling.

The scraper only handles public pages, checks `robots.txt`, and requires
college-specific URLs in `scraper.py`. Never bypass access controls or commit
`.env` or API keys.
