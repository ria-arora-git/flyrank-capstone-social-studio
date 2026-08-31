Build Log — AI usage

I used an AI assistant (Claude) throughout this project, mainly to move faster on boilerplate and to
sanity-check the idempotency design, which is the part of this brief I was most worried about
getting subtly wrong. Below is an honest account of where it helped, where its first pass was
wrong or incomplete, and what I changed.

Where it helped
* Database schema. The AI suggested the four-table layout (`posts`, `variants`, `slots`,
  `publish_attempts`) and, specifically, putting a `UNIQUE` constraint on an `idempotency_key`
  column rather than trying to de-duplicate publishes with application-level checks. That one
  design decision is what makes the whole idempotency guarantee possible, so I spent real time
  making sure I understood why it works, not just that it did.
* FastAPI route boilerplate. Request/response models, status codes, and the general shape of
  each endpoint were drafted quickly this way, which let me spend more time on the scheduler and
  adapter logic instead of re-typing CRUD routes. The commit history reflects this build order:
  ingestion (`src/ingest.py`) → constraints (`src/constraints.py`) → generator
  (`src/generator.py`) → endpoints (`src/server.py`) — each landed as its own commit.
* Test scripts. The structure of `test_smoke.py` and `test_crash_recovery.py` — in particular,
  using real Python threads to actually race concurrent publish calls instead of just calling a
  function twice in a row — came from the assistant. Calling it with threads matters: a
  sequential test would "pass" even with a broken idempotency check, because there'd be no real
  race to catch. Both scripts ran clean end-to-end in the terminal (`ALL SMOKE CHECKS DONE`,
  and the crash-recovery run finishing with `mock_x_posts count (must be exactly 1 — no
  duplicate): 1`).
* Took help in writing the documentation properly and understanding anything that i was unable to understand on my own.

Where I had to fix or rethink things

* The idempotency check itself. An early version checked "does an attempt already exist for
  this slot?" with a `SELECT` before doing the `INSERT`. That's not actually safe — two threads
  can both run the `SELECT`, both see nothing, and both proceed to `INSERT`. The fix was to skip
  the `SELECT` entirely and just attempt the `INSERT` directly, letting the database's `UNIQUE`
  constraint reject the second one. The `try/except sqlite3.IntegrityError` in `claim_slot()` is
  the whole mechanism — I made sure I could explain why a `SELECT`-then-`INSERT` pattern doesn't
  give you this guarantee before moving on.
* URL ingestion. The brief says a post can come in "as a URL or as pasted Markdown," and my
  first version quietly required a pasted body either way, which isn't really honoring the "as a
  URL" case. I added `src/ingest.py` to actually fetch the page and strip it down to plain text
  with BeautifulSoup when no body is provided, and kept the option to paste a body alongside a
  URL for convenience. Running this against a real URL (a LinkedIn post of mine) worked
  end-to-end, but showed a real gap: the extracted body includes a lot of page furniture — nav
  text, the sign-in wall, and a long list of unrelated "more relevant posts" — not just the
  article text. It's honest evidence the fetch path works, but the extraction is coarser than
  I'd want in a real product; I'd narrow the BeautifulSoup selector to the actual post container
  if I had more time before submission.
* Database connections across threads. Since the scheduler runs on a background thread while
  FastAPI handles requests on others, I made sure every function opens and closes its own SQLite
  connection rather than sharing one connection across threads — SQLite connections aren't
  guaranteed thread-safe by default, and WAL mode is what actually makes multiple short-lived
  connections against the same file safe to use concurrently.
* Crash recovery. It would have been easy to have the recovery step just re-run the same "claim
  + publish" logic used for a fresh slot, but that would try to `INSERT` a new row and
  immediately fail against the existing `idempotency_key`, since the whole point is that the row
  is already there. `recover_stale_attempts()` instead `UPDATE`s the existing stuck row in
  place — it never inserts a second one.
* Test-runner dependency. The first run of `test_smoke.py` failed immediately with
  `RuntimeError: The starlette.testclient module requires the httpx2 package to be installed`,
  not because of anything wrong in my code, but because `TestClient` has a runtime dependency
  that wasn't in my `venv` yet. Installed `httpx2` and reran — same test, same assertions, now
  passing clean. Worth noting in case the grader's environment hits the same missing-dependency
  error on a fresh `venv`.
* A messy commit I had to undo. My first attempt at the variant generator landed as a stray
  `generator.py` at the repo root instead of `src/generator.py`, breaking the module layout the
  rest of the app expects. I caught it before building further on top of it and used
  `git reset --hard HEAD~1` + `git push --force` to remove that commit entirely, then redid the
  work correctly as `src/generator.py`. I'm noting the force-push here rather than pretending
  the history was always clean.
* Fresh-database schema initialization. Later, after killing and restarting the live `uvicorn`
  process by hand (`kill -9 ...`), a subsequent start against a `data.sqlite` file that hadn't
  been (re-)seeded threw a repeating `[scheduler] tick error: no such table: publish_attempts`.
  This wasn't a duplicate-publish bug — the scheduler's polling loop is resilient to it, it just
  logs and retries — but it was a good reminder that the schema-creation step needs to run (via
  `seed.py` or an explicit init) before the server is pointed at a brand-new or wiped `.sqlite`
  file, and that I should treat "table missing" and "row already claimed" as two very different
  failure modes when reading scheduler logs.

