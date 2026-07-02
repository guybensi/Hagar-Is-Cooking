# Hagar Is Cooking 🍳

🤖 **Try it now on Telegram:** [@Hagar_Is_Cooking_bot](http://t.me/Hagar_Is_Cooking_bot) — live,
public, free to use.

A Telegram AI cooking assistant, in Hebrew, that turns "אני רוצה פסטה" into a complete,
ingredient-aware cooking session:

1. Understands what you feel like eating (free text, in Hebrew or mixed language).
2. Searches **mako.co.il only** for matching recipes (via Tavily) and lets you pick one — each
   result also links straight to the original page.
3. Fetches and cleans the recipe page (via Tavily's extract API), then asks Groq to structure it
   (name, ingredients, instructions).
4. Shows an interactive ☑/⬜ checklist so you can mark what you already have.
5. For everything missing, Groq decides **BUY** / **SKIP** / **SUBSTITUTE** — and asks you to
   confirm any proposed substitutions.
6. Generates a final recipe rewritten to match exactly what you have.
7. Delivers it either as a full recipe message or step-by-step with a 💡 "why?" button per step
   — freely switchable between the two at any time.

A ❌ cancel button is always available on every keyboard, so you can bail out and start a new
dish at any point in the flow.

Built with `python-telegram-bot`, the Groq API (structured JSON outputs), Tavily Search,
SQLite (via SQLAlchemy async), and Pydantic — service-oriented, fully tested, with CI on every
push.

## Installation

Requires [uv](https://docs.astral.sh/uv/) and Python 3.12+ (uv will install the interpreter if
needed).

```bash
uv sync
```

This creates a `.venv` and installs both runtime and dev dependencies from `pyproject.toml` /
`uv.lock`.

## Environment variables

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from [@BotFather](https://t.me/BotFather). |
| `GROQ_API_KEY` | Yes | API key from [console.groq.com](https://console.groq.com). |
| `TAVILY_API_KEY` | Yes | API key from [tavily.com](https://tavily.com). |
| `GROQ_MODEL` | No | Groq model id. Defaults to `openai/gpt-oss-120b` (native structured-output support). |
| `DATABASE_PATH` | No | SQLite file path. Defaults to `hagar_is_cooking.db`. |
| `LOG_LEVEL` | No | Python log level. Defaults to `INFO`. |

`.env` is git-ignored — never commit real credentials. `.env.example` is the template that *is*
committed and must always stay blank.

## Running locally

```bash
uv run python -m app
```

This creates the SQLite tables on first run (if they don't already exist) and starts long
polling. Talk to your bot on Telegram — send `/start` to begin.

### Tests and linting

```bash
uv run pytest        # full test suite (all external calls mocked, no network/API keys needed)
uv run ruff check .  # lint
```

CI (`.github/workflows/ci.yml`) runs both on every push and pull request.

## Deploying to Fly.io

The bot uses long polling (not webhooks), so the only requirement is a host that keeps the
process running continuously with the right env vars — no public HTTPS endpoint needed. A
`Dockerfile` and `fly.toml` are included for that.

1. [Install flyctl](https://fly.io/docs/hands-on/install-flyctl/) and sign in: `fly auth login`.
2. From the repo root, create the app (pick a globally-unique name if `hagar-is-cooking` is
   taken — edit the `app = "..."` line in `fly.toml` to match):
   ```bash
   fly launch --no-deploy --copy-config
   ```
   This reads `fly.toml` as-is and just registers the app; `--no-deploy` skips deploying before
   secrets are set.
3. Create the persistent volume for the SQLite database (must match `fly.toml`'s
   `[mounts] source`, and be created in the same region as `primary_region`):
   ```bash
   fly volumes create hagar_data --region iad --size 1
   ```
4. Set your secrets (never put these in `fly.toml` — it's committed to git):
   ```bash
   fly secrets set TELEGRAM_BOT_TOKEN=... GROQ_API_KEY=... TAVILY_API_KEY=...
   ```
5. Deploy:
   ```bash
   fly deploy
   ```
   No local Docker install is required — `flyctl` builds the image on Fly's remote builders if
   Docker isn't available locally.
6. Make sure only **one** instance is ever running — Telegram's long-polling API rejects a
   second concurrent poller (`409 Conflict`) for the same bot token:
   ```bash
   fly scale count 1 --max-per-region=1
   ```
7. Watch logs / confirm it's alive:
   ```bash
   fly logs
   ```

To redeploy after code changes, just `fly deploy` again — the `sessions`/`users`/`recipe_history`
SQLite data on the `hagar_data` volume survives across deploys and restarts.

## Project structure

```
app/
├── __main__.py              # entrypoint: uv run python -m app
├── config/settings.py       # Pydantic Settings loaded from env vars / .env
├── bot/
│   ├── application.py       # builds the PTB Application, wires shared services into bot_data
│   └── error_handler.py     # global error boundary -> Hebrew friendly message + structured log
├── handlers/                # one module per stage of the conversation flow
│   ├── registry.py          # registers every command/callback/message handler in one place
│   ├── start_handler.py     # /start (incl. resume-on-restart), /help, /cancel + ❌ cancel button
│   ├── search_handler.py    # free text -> Groq-normalized query -> Tavily search -> results
│   ├── selection_handler.py # selected result -> extract -> Groq-structure -> checklist
│   ├── checklist_handler.py # ☑/⬜ toggling, "finished" -> substitution decisions
│   ├── substitution_handler.py # yes/no substitution Q&A -> final recipe generation
│   ├── delivery_handler.py  # full-recipe/interactive mode choice + switching + full recipe view
│   └── interactive_handler.py # step-by-step navigation + 💡 why explanations
├── services/                # business logic, one responsibility per service
│   ├── recipe_search_service.py       # Tavily site:mako.co.il search
│   ├── recipe_extraction_service.py   # Tavily extract API -> cleaned page text
│   ├── recipe_structuring_service.py  # Groq: raw text -> StructuredRecipe
│   ├── substitution_service.py        # Groq: missing ingredients -> BUY/SKIP/SUBSTITUTE
│   ├── final_recipe_service.py        # Groq: rewrite recipe to match what's available
│   ├── explanation_service.py         # Groq: "why does this step matter?"
│   ├── session_service.py             # FSM transitions on top of SessionRepository
│   ├── recipe_history_service.py      # logs completed recipes
│   └── llm/
│       ├── groq_client.py     # AsyncGroq wrapper: structured completions, retry + validation
│       └── schema_builder.py  # Pydantic model -> Groq strict json_schema response_format
├── models/                  # Pydantic domain models (SearchResult, Recipe*, Substitution*, Session*)
├── database/                 # SQLAlchemy async engine, ORM models, repositories
│   ├── engine.py
│   ├── models.py             # users / sessions / recipe_history tables
│   ├── user_repository.py
│   ├── session_repository.py # durable per-chat conversation state (JSON blob)
│   └── recipe_history_repository.py
├── prompts/                  # one module per Groq use case (SYSTEM_PROMPT + build_user_prompt)
├── utils/                     # logging, retry decorator, Telegram helpers, text truncation
└── static/                    # centralized Hebrew UI strings and emoji constants

tests/                         # mirrors app/ 1:1 -- every module above has a matching test file
```

### Architecture notes

- **FSM, not `ConversationHandler`.** The conversation flow is a custom state machine
  (`SessionState`) persisted as a JSON blob per `chat_id` (`sessions` table), not PTB's built-in
  `ConversationHandler`. This gives durable, restart-safe state (`/start` mid-flow re-renders
  wherever you left off) and handles the flow's variable-length sub-loops (checklist toggling,
  per-item substitution Q&A, interactive step navigation) more naturally than a single linear
  state graph.
- **Scrape + LLM-structure, not scrape + parse.** `recipe_extraction_service` only fetches and
  denoises the HTML into clean text; all ingredient/instruction field-splitting is delegated to
  a single Groq structuring call. mako.co.il's markup can change, and duplicating brittle
  parsing logic across two layers would be worse than the extra token cost.
- **Groq structured outputs, strict mode.** Every Groq call uses `response_format:
  json_schema` (strict) built from the relevant Pydantic model, validated on the way back in
  with a bounded re-prompt-and-retry loop for schema violations (separate from the
  transient-network retry via `tenacity`).

## Future improvements

- Persistent pantry memory across sessions (remember what a user always has on hand).
- Multi-language UI (currently Hebrew-only, by design).
- Additional recipe sources beyond mako.co.il.
- Per-user rate limiting / Groq & Tavily quota guarding.
- Webhook-mode deployment (currently long polling — fine at this scale, but polling is a single
  point of contention if you ever need to scale beyond one instance).
- Alembic-based schema migrations (currently `create_all` on startup).
- Surface `recipe_history` as a user-facing "my past recipes" feature.
- Nutrition info, recipe/step images, voice input.
- Concurrent multi-session support per user (currently one active session per chat).
- Admin/analytics dashboard, response caching for popular queries.
