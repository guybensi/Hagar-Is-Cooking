# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Telegram bot (Hebrew UI, English code) that turns a free-text dish request into a full cooking
session: search mako.co.il via Tavily → pick a result → scrape + Groq-structure the recipe →
interactive ingredient checklist → Groq decides BUY/SKIP/SUBSTITUTE for what's missing → user
confirms substitutions → Groq rewrites the final recipe → deliver as one message or step-by-step
with a 💡 "why" explanation per step.

## Commands

```bash
uv sync                              # install/sync dependencies
uv run python -m app                 # run the bot (long polling; needs a real .env)
uv run pytest                        # full test suite (all external calls mocked)
uv run pytest tests/handlers/test_checklist_handler.py   # single file
uv run pytest tests/handlers/test_checklist_handler.py::test_toggle_flips_checked_state_and_persists  # single test
uv run ruff check .                  # lint
uv run ruff check --fix .            # lint, auto-fixing what's fixable
```

CI (`.github/workflows/ci.yml`) runs `ruff check .` and `pytest` on every push and PR. There are
no live-API integration tests — everything is mocked, so CI needs no secrets.

Cloud deployment (Fly.io) uses `Dockerfile` + `fly.toml` at the repo root; see the "Deploying to
Fly.io" section in `README.md` for the full `fly launch`/`volumes create`/`secrets set`/`deploy`
runbook. No webhook server — the bot still uses long polling, so only process uptime + env vars
matter, not a public endpoint.

## Architecture

### Custom FSM, not `ConversationHandler`

The entire conversation is driven by `SessionState` (`app/models/session.py`), persisted as one
JSON blob per `chat_id` in the `sessions` table (`app/database/session_repository.py`) — not
python-telegram-bot's built-in `ConversationHandler`. Every handler follows the same shape:

1. Load (or create) the `SessionData` for `chat_id` via `SessionService`.
2. Check `session.state` is the state the handler expects; if not, treat the button/message as
   stale (`labels.STALE_SELECTION_MESSAGE`) and no-op.
3. Do the work (call a service, hit Groq/Tavily/httpx).
4. Persist the mutated session via `session_service.advance_to(session, new_state, **fields)`.

This is why state survives bot restarts "for free," and why `/start` mid-flow can re-render
exactly where the user left off (`start_handler._build_resume_content`) instead of resetting —
except for the *transient* states (`SEARCHING`, `EXTRACTING`, `STRUCTURING`,
`DECIDING_SUBSTITUTIONS`, `GENERATING_FINAL_RECIPE`, see `TRANSIENT_STATES`), which mean "crashed
mid external call" and always reset to `IDLE` since there's nothing in-flight left to resume.

### Handler cross-imports are intentional

Handlers import rendering helpers from *other* handler modules instead of duplicating
message/keyboard-building logic:

- `selection_handler` renders the checklist using `checklist_handler.build_checklist_message`
  / `build_checklist_keyboard`.
- `checklist_handler` renders substitution questions using
  `substitution_handler.build_substitution_question_message` / `build_substitution_keyboard`,
  and triggers final-recipe generation via `substitution_handler.generate_and_render_final_recipe`
  (shared because three different paths can reach "nothing left to substitute": no missing
  ingredients, no SUBSTITUTE decisions, or the last substitution answered).
- `substitution_handler` renders the delivery-mode keyboard via
  `delivery_handler.build_delivery_mode_keyboard`.
- `delivery_handler` renders the first interactive step via `interactive_handler.render_step`.
- `start_handler` imports from all of the above to rebuild the resume-on-restart content.

The import graph is one-directional (`start_handler` → everything; `checklist_handler` →
`substitution_handler` → `delivery_handler` → `interactive_handler`) — nothing imports back
toward `start_handler`, so there are no cycles. Keep new handlers consistent with this direction.

### Delivery mode is switchable, not one-shot

`mode:full` / `mode:interactive` aren't just the initial delivery choice — the same two
callbacks are reused as toggle buttons on the full-recipe message and on every interactive step,
so the user can flip between views freely. `delivery_handler.handle_mode_choice` accepts them
from any state in `MODE_SWITCHABLE_STATES` (`AWAITING_DELIVERY_MODE`, `DELIVERING_INTERACTIVE`,
`COMPLETED`), not just the first choice, and switching into interactive resumes at
`session.current_step_index` rather than restarting at step 1. Because `COMPLETED` is reachable
this way from multiple paths (full mode, or finishing all interactive steps),
`RecipeHistoryService.log_completed_once` gates on `SessionData.history_logged` so toggling back
and forth doesn't write duplicate `recipe_history` rows.

### Cancel is always one tap away

Every in-flow keyboard (search results, checklist, substitution question, delivery mode, full
recipe, interactive steps) ends with a row from `utils/telegram_helpers.cancel_row()`, wired to a
single `cancel` callback (`start_handler.handle_cancel_callback`) that resets the session
unconditionally — no state check needed, since resetting is always safe. Add `cancel_row()` to
any new in-flow keyboard's row list to keep this consistent.

### Extraction is fetch-only; structuring is LLM-only

`recipe_extraction_service.py` fetches and cleans the mako.co.il page via Tavily's `extract` API
(`TavilyClient.extract(urls=url, format="text")` — the same Tavily account/key already used for
search), not a hand-rolled scraper. An earlier version used raw `httpx` + BeautifulSoup, but
mako.co.il was returning too little real content to that approach in production (likely
anti-bot/JS rendering) — Tavily's extract endpoint handles it reliably. Either way, this service
does **not** attempt to split ingredients from instructions — that's delegated entirely to a
single Groq call (`recipe_structuring_service` → `GroqClient.structure_recipe`). Don't add
structure-specific parsing for ingredients/instructions here; if extraction quality is bad, the
fix belongs in the structuring prompt, not in new fetch/parsing logic. Raises
`RecipeExtractionError` on a Tavily-side failure or an empty `results` list (checks
`failed_results` for the reason before raising).

### Groq: strict structured outputs + two independent retry layers

`GroqClient` (`app/services/llm/groq_client.py`) is the only place that talks to Groq. Every
public method (`normalize_dish_query`, `structure_recipe`, `decide_substitutions`,
`rewrite_final_recipe`, `explain_step`) goes through `_structured_completion`, which:

- Builds a strict `json_schema` `response_format` from a Pydantic model via
  `schema_builder.build_json_schema_response_format` (recursively sets
  `additionalProperties: false` and lists every field — including optional ones — in
  `required`, since Groq/OpenAI strict mode requires optionality to be expressed via a `null`
  member of the type instead of an absent key).
- Retries transient *network* errors (rate limits, timeouts, connection errors) via
  `utils/retry.retry_transient_errors` (tenacity, exponential backoff) — this wraps the raw SDK
  call in `_create_completion`.
- Separately retries *validation* failures (bad/incomplete JSON) up to
  `max_validation_retries` times by re-prompting with the validation error appended — this is
  content-aware and independent of the network retry.
- Raises `LLMStructuringError` after exhausting validation retries; each service
  (`recipe_structuring_service`, `substitution_service`, `final_recipe_service`,
  `explanation_service`) catches that and re-raises its own domain exception
  (`RecipeStructuringError`, `SubstitutionDecisionError`, `FinalRecipeGenerationError`,
  `ExplanationError`), which handlers catch to show a Hebrew error message and revert session
  state.

When adding a new Groq-backed capability: add a prompt module under `app/prompts/` (`SYSTEM_PROMPT`
+ `build_user_prompt`), a typed method on `GroqClient`, and a thin service wrapping it that
translates `LLMStructuringError` into a domain-specific exception — don't call `GroqClient`
directly from handlers.

### Dependency wiring: `bot_data`, not a DI container

Shared services (`GroqClient`, `RecipeSearchService`, `RecipeExtractionService`,
`RecipeStructuringService`, `SubstitutionService`, `FinalRecipeService`, `ExplanationService`,
the SQLAlchemy engine and session factory) are constructed once in `build_application()`
(`app/bot/application.py`) and stashed in `application.bot_data[...]`. Handlers pull them out of
`context.bot_data`. Per-request objects that need a specific `AsyncSession` (`SessionRepository`,
`UserRepository`, `RecipeHistoryRepository`, and the `SessionService`/`RecipeHistoryService` built
on top of them) are instead constructed fresh inside each handler's
`async with session_scope(session_factory) as db_session:` block — never put in `bot_data`.

### Logging context

Call `bind_chat_context(chat_id)` (`app/utils/logging.py`) at the top of every handler, right
after extracting `chat_id`. It binds `chat_id` into structlog's contextvars (clearing any prior
binding first) so every subsequent log line in that update — across handler and service code —
is automatically tagged, without threading `chat_id` through every log call.

### Everything Hebrew-facing lives in `app/static/`

`app/static/labels.py` (strings) and `app/static/emojis.py` (emoji constants) are the only place
user-facing Hebrew text should be written. Code, comments, log messages, and identifiers stay in
English. Message-building functions (e.g. `build_checklist_message`, `build_full_recipe_message`)
compose these labels rather than hardcoding text inline.

### Testing conventions

`tests/` mirrors `app/` 1:1. `tests/conftest.py` provides: `session_factory` (function-scoped
in-memory SQLite via `db_engine`), `test_settings`, and Telegram fakes — `make_update` /
`make_callback_update` build `MagicMock(spec=...)` `Update`/`CallbackQuery` objects (so
`isinstance` checks like the error handler's still work) with `AsyncMock` message/query methods,
and `make_context` / the `context_with_db` fixture build a fake `ContextTypes.DEFAULT_TYPE` with
`bot_data["session_factory"]` pre-wired. Handler tests seed a `SessionData` directly via
`SessionRepository.upsert` rather than driving the whole flow end-to-end from `/start`. No test
hits real Telegram, Groq, or Tavily — Groq/Tavily/httpx calls are mocked at the client boundary
(`respx` for httpx), and repository tests run against the real in-memory SQLite engine to
exercise actual SQL/ORM round-trips.
