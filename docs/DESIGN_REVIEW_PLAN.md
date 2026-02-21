# Design Review Plan

> **Purpose**: Assessment of the current system design against the core requirements.
> Each item includes the gap, the requirement it violates, and a concrete action.
> Ordered by priority (most impactful first).

## Core Requirements Recap

1. **Understand word meaning** by analyzing how each word is used and where
2. **Compare similar words** — find locations where a similar (but not identical) word appears
3. **Fast and huge database** — handle thousands of occurrences per root
4. **Easy manual updates** — correct roots, add interpretations by hand
5. **Expandable** — add English translations, tafsir, cross-references later

---

## ~~D1 · No ORM Relationships Between Models (HIGH)~~ ✅ DONE

> **Implemented in commit `c42c63c`.** Token.root_id FK → roots.id, Token.verse_id FK → verses.id, bidirectional relationships on all three models, selectinload in repository queries.

**Gap**: Token, Root, and Verse are isolated ORM models with no SQLAlchemy `relationship()` links. Querying "all tokens for a root" requires filtering on the `Token.root` string column, and there is no FK constraint ensuring referential integrity.

**Requirement violated**: #1, #2, #3 — comparing words by root requires fast JOINs.

**Action**:
- ~~Add `root_id` FK column to Token referencing `roots.id`.~~
- ~~Add `sura`/`aya` FK columns to Token or a join table to Verse.~~
- ~~Define SQLAlchemy `relationship()` on Token, Root, and Verse.~~
- ~~Update repositories and routes to use eager-loading (`selectinload`) instead of multiple queries.~~

---

## ~~D2 · Root.token_ids JSON Column Does Not Scale (HIGH)~~ ✅ DONE

> **Implemented in commit `c42c63c`.** Column renamed to `tokens_legacy`, new code uses ORM relationship. `Root.tokens` relationship replaces JSON list.

**Gap**: `Root.token_ids` stores a flat JSON list of token IDs. For common roots (e.g. ك ت ب) with 1000+ tokens, this column becomes huge, slow to query, and impossible to index.

**Requirement violated**: #3 — "fast and huge database."

**Action**:
- ~~Remove `Root.token_ids` entirely once the FK relationship (D1) is in place.~~
- ~~Rely on `SELECT * FROM tokens WHERE root_id = ?` instead.~~
- Keep `Root.token_count` as a denormalized counter (update via trigger or application logic).

---

## ~~D3 · Verse Table Is Never Populated (MEDIUM)~~ ✅ DONE

> **Implemented in commit `c42c63c`.** Verse table populated (6,236 rows) via migration script and tokenize_quran.py. Verse endpoint reads from Verse table with token fallback.

**Gap**: The `Verse` model exists with proper columns but no code (service, script, or task) ever inserts rows into it. The API reconstructs verse text by joining Token rows (`" ".join(t.text_ar for t in tokens)`).

**Requirement violated**: #5 — expandability for verse-level annotations (translations, tafsir).

**Action**:
- ~~Populate the Verse table during tokenization (one INSERT per verse).~~
- ~~Add a `verses ↔ tokens` relationship so `verse.tokens` is a lazy-loaded collection.~~
- Use the Verse table for future translations and tafsir references stored in `metadata_`.

---

## ~~D4 · Token.references JSON Is Redundant (MEDIUM)~~ ✅ DONE

> **Implemented in commit `c42c63c`.** Column marked DEPRECATED, removed from API schema. index_references.py now sets root_id FK. Column kept for backward compat.

**Gap**: `Token.references` stores a JSON array of related token IDs. With proper FK relationships (D1), this information is derivable via `SELECT id FROM tokens WHERE root_id = ?` — no need to denormalize into every row.

**Requirement violated**: #4 — manual updates require recalculating references when a root is corrected.

**Action**:
- ~~Deprecate `Token.references` once D1 is implemented.~~
- ~~Provide a `/quran/root/{root}` endpoint that queries dynamically (already exists).~~
- ~~Optionally keep as a materialized cache that is rebuilt by `index_references.py`.~~

---

## D5 · No Mechanism for Manual Root Corrections via API (MEDIUM)

**Gap**: The requirement says "easy to update manually" but there is no PATCH/PUT endpoint for correcting a token's root. Corrections currently require direct DB access or running a script.

**Requirement violated**: #4 — easy manual updates.

**Action**:
- Add `PATCH /quran/token/{id}` to update `root`, `status`, `interpretations`.
- Add `PATCH /quran/root/{root}` to update `meaning`, `metadata_`.
- Protect with simple auth (API key or basic auth).
- Invalidate Redis cache for affected keys on update.

---

## D6 · No Full-Text Search Index (LOW)

**Gap**: Text search uses `LIKE '%query%'` which forces a full table scan. With 77,000+ tokens this is slow for arbitrary substring searches.

**Requirement violated**: #1 — analyzing word usage requires fast search.

**Action**:
- For PostgreSQL: add GIN/GiST index with `pg_trgm` extension.
- For SQLite: add FTS5 virtual table shadowing the Token table.
- Update `TokenRepository.asearch()` to use the appropriate index.

---

## D7 · No "Similar Word" Comparison Feature (LOW)

**Gap**: The core requirement mentions "comparing with similar but not identical words." The system groups by exact root but has no concept of morphological similarity, semantic proximity, or near-miss roots.

**Requirement violated**: #2 — compare similar words.

**Action**:
- Add computed columns for morphological pattern (وزن) on Token.
- Add a `related_roots` JSON field on Root for manually curated similar roots.
- Consider adding Levenshtein distance search for normalized word forms.
- (Long-term) Add word embeddings for semantic similarity.

---

## D8 · Database Migration Strategy Missing (LOW)

**Gap**: Schema changes are applied via `Base.metadata.create_all()` which only adds new tables/columns — it cannot rename, drop, or alter existing columns. There is no Alembic migration setup.

**Requirement violated**: #5 — expandability requires safe schema evolution.

**Action**:
- Add Alembic with `alembic init` and configure for both SQLite and PostgreSQL.
- Generate initial migration from current schema.
- All future schema changes go through migration files.

---

## Summary Priority Matrix

| ID | Priority | Effort | Depends On |
|----|----------|--------|------------|
| D1 | HIGH     | Medium | —          |
| D2 | HIGH     | Low    | D1         |
| D3 | MEDIUM   | Low    | D1         |
| D4 | MEDIUM   | Low    | D1         |
| D5 | MEDIUM   | Medium | —          |
| D6 | LOW      | Medium | —          |
| D7 | LOW      | High   | D1         |
| D8 | LOW      | Low    | —          |

Recommended execution order: **D1 → D2 → D3 → D4 → D5 → D8 → D6 → D7**
