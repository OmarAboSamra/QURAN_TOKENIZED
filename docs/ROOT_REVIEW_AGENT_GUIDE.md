# Root Review Agent Guide

> **Audience**: An AI agent (Copilot Chat / LLM running in VS Code) that
> will iterate through Qur'anic tokens and correct their Arabic roots
> using its pretrained linguistic knowledge.

> **Workspace root**: `c:\quran-backend`

---

## Overview

The Quran backend database contains ~77,000 word tokens extracted from the
Qur'an.  Each token has a `root` field representing the Arabic root (جذر)
of the word (e.g., the word "كتابًا" has root "كتب").

Many roots were extracted automatically by algorithmic extractors and may
be **incorrect**.  Your job is to:

1. **Fetch** tokens from the database in batches
2. **Evaluate** each token's root using your Arabic linguistics knowledge
3. **Directly apply** the correct root for any incorrect token — updating
   **all occurrences** of the same normalized word throughout the entire book
4. **Continue** to the next batch until every token has been reviewed

**There is no human review step.** You are the authority. Fix roots
directly and move on.

---

## Step 1 — Fetch a Batch of Tokens

Run this command in the terminal (from the workspace root):

```powershell
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 0 --limit 50
```

This outputs JSON like:

```json
{
  "tokens": [
    {
      "token_id": 77555,
      "sura": 1,
      "aya": 1,
      "position": 0,
      "text_ar": "بِسْمِ",
      "normalized": "بسم",
      "current_root": "سمو",
      "root_sources": {"alkhalil": "سمو"},
      "status": "verified",
      "pattern": null
    }
  ],
  "progress": {
    "offset": 0,
    "limit": 50,
    "batch_count": 50,
    "total_matching": 77433,
    "next_offset": 50
  }
}
```

### Useful arguments

| Argument    | Description                          | Example                |
|-------------|--------------------------------------|------------------------|
| `--offset`  | Skip this many tokens                | `--offset 100`         |
| `--limit`   | Tokens per batch (default 50)        | `--limit 25`           |
| `--status`  | Filter: missing, verified, discrepancy, manual_review | `--status verified` |
| `--sura`    | Filter by sura number                | `--sura 2`             |
| `--output`  | Write to file instead of stdout      | `--output batch.json`  |

### Advancing through batches

Use `progress.next_offset` from the output as the next `--offset`:

```powershell
# Batch 1
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 0 --limit 50
# Batch 2
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 50 --limit 50
# Batch 3
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 100 --limit 50
# ... and so on
```

When `next_offset` is `null`, you have reached the end.

---

## Step 2 — Evaluate Each Token's Root

For each token in the batch, use your Arabic linguistics knowledge to
determine whether `current_root` is correct.

### How to reason about Arabic roots

1. **Most Arabic roots are trilateral (ثلاثي)** — 3 consonant letters.
   Examples: كتب (write), قرأ (read), علم (know), حمد (praise).

2. **Some roots are quadrilateral (رباعي)** — 4 letters.
   Examples: زلزل (quake), بسمل (say bismillah), ترجم (translate).

3. **Strip prefixes and suffixes mentally** to find the root:
   - Common prefixes: ال (definite article), بـ، كـ، لـ، فـ، وـ (preposition clitics)
   - Common suffixes: ون، ين، ات، ة، ـهم، ـكم، ـنا (plurals, pronouns)
   - Verb prefixes: يـ، تـ، نـ، أ (imperfect markers)

4. **Particles and pronouns do NOT have roots.** These include:
   - من، في، على، إلى، عن، حتى، إن، أن، لا، ما، لم، لن، إذا، إذ
   - هو، هي، هم، هن، أنت، أنتم، نحن
   - الذي، التي، الذين، اللاتي
   - If a token is a particle/pronoun, set its root to the **normalized
     word itself** (i.e., leave it as its own text without modification).

5. **Proper nouns** may or may not have roots:
   - الله — this is a proper noun; the traditional root is "أله" (some say "وله")
   - إبراهيم، موسى، عيسى — foreign proper nouns, no Arabic root →
     set root to the normalized word itself
   - مكة، يثرب — place names, may have roots

6. **When no root is known** — for particles, pronouns, foreign proper
   nouns, or any word whose trilateral root you cannot determine — set the
   root to the **normalized word itself** (the word as-is, without
   modification).  Do NOT leave it blank or null.

7. **Common errors in the current database**:
   - Root is the full word instead of the base root (e.g., "كتاب" instead of "كتب")
   - Root includes the definite article "ال" (e.g., "الرحم" instead of "رحم")
   - Root is from a wrong derivation pattern
   - Augmented letters (حروف الزيادة: سألتمونيها) not stripped correctly

8. **Reference: well-known Qur'anic word roots**:

   | Word          | Correct Root | Notes                        |
   |---------------|-------------|------------------------------|
   | بِسْمِ        | سمو         | From اسم (name), root is سمو  |
   | ٱللَّهِ       | أله         | Proper noun of God            |
   | ٱلرَّحْمَـٰنِ | رحم         | The Most Merciful             |
   | ٱلرَّحِيمِ    | رحم         | The Most Compassionate        |
   | ٱلْحَمْدُ     | حمد         | Praise                        |
   | رَبِّ         | ربب         | Lord                          |
   | ٱلْعَـٰلَمِينَ | علم         | The worlds                    |
   | مَـٰلِكِ      | ملك         | Master/Owner                  |
   | يَوْمِ        | يوم         | Day                           |
   | ٱلدِّينِ      | دين         | Religion/Judgment             |
   | نَعْبُدُ      | عبد         | We worship                    |
   | نَسْتَعِينُ    | عون         | We seek help                  |
   | ٱهْدِنَا      | هدي         | Guide us                      |
   | ٱلصِّرَ‌ٰطَ    | صرط         | The path                      |
   | ٱلْمُسْتَقِيمَ | قوم         | The straight                  |
   | أَنْعَمْتَ    | نعم         | You have blessed              |
   | ٱلْمَغْضُوبِ  | غضب         | Those who earned anger        |
   | ٱلضَّآلِّينَ   | ضلل         | Those who went astray         |

---

## Step 3 — Directly Apply Correct Roots

When you find a token whose root is wrong, **apply the correction
immediately** using the apply script.  Do NOT stage for review.

### Applying a correction to ALL occurrences of the same word

The apply script updates a single token by ID, but you **must propagate
the correction to every occurrence of the same normalized word** in the
entire book.  Use the following approach:

#### 3a. Find all occurrences of the word

Write a small inline Python query to find every token with the same
`normalized` form:

```powershell
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from backend.db import get_sync_session_maker, init_db
from backend.models.token_model import Token
from sqlalchemy import select
init_db()
S = get_sync_session_maker()
with S() as s:
    ids = [t.token_id for t in s.execute(select(Token).where(Token.normalized == '<NORMALIZED_WORD>')).scalars()]
    print(f'Found {len(ids)} occurrences')
    print(','.join(str(i) for i in ids))
"
```

Replace `<NORMALIZED_WORD>` with the token's `normalized` value from the
batch.

#### 3b. Update all occurrences at once

Use a bulk update to set the correct root for every matching token:

```powershell
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from backend.db import get_sync_session_maker, init_db
from backend.models.token_model import Token, TokenStatus
from backend.models.root_model import Root
from sqlalchemy import select, update
init_db()
S = get_sync_session_maker()
with S() as s:
    # Get or create the Root row
    correct_root = '<CORRECT_ROOT>'
    root_obj = s.execute(select(Root).where(Root.root == correct_root)).scalar_one_or_none()
    if not root_obj:
        root_obj = Root(root=correct_root, token_count=0, token_ids=[])
        s.add(root_obj)
        s.flush()

    # Find all tokens with this normalized form
    tokens = s.execute(select(Token).where(Token.normalized == '<NORMALIZED_WORD>')).scalars().all()

    # Decrement old root counters
    old_roots = {}
    for t in tokens:
        if t.root and t.root != correct_root:
            old_roots[t.root] = old_roots.get(t.root, 0) + 1

    for old_root_str, count in old_roots.items():
        old_root_obj = s.execute(select(Root).where(Root.root == old_root_str)).scalar_one_or_none()
        if old_root_obj and old_root_obj.token_count:
            old_root_obj.token_count = max(0, old_root_obj.token_count - count)

    # Update all tokens
    updated = 0
    for t in tokens:
        t.root = correct_root
        t.root_id = root_obj.id
        t.status = TokenStatus.VERIFIED.value
        sources = t.root_sources or {}
        sources['agent_review'] = correct_root
        t.root_sources = sources
        updated += 1

    root_obj.token_count = (root_obj.token_count or 0) + updated
    s.commit()
    print(f'Updated {updated} tokens: root set to \"{correct_root}\"')
"
```

Replace `<CORRECT_ROOT>` and `<NORMALIZED_WORD>` with the appropriate values.

### Decision rules

| Situation                                   | Action                                                     |
|---------------------------------------------|------------------------------------------------------------|
| Root is wrong and you know the correct root  | Apply the correct root to all occurrences                  |
| Root is wrong but you are unsure of correct  | Use your best linguistic judgment and apply it              |
| Token is a particle/pronoun (no root exists) | Set root to the **normalized word itself** (the word as-is) |
| Proper noun with no Arabic root             | Set root to the **normalized word itself**                  |
| Root is already correct                      | Skip — move to the next token                              |

### Efficiency tip — group by normalized word

Tokens in a batch often share the same normalized form.  Before
evaluating, group them by `normalized`.  Evaluate the root **once per
unique word**, then apply the correction to all of them in a single bulk
update.  This avoids redundant analysis and DB updates.

---

## Step 4 — Continue to Next Batch

After processing every token in the current batch, immediately fetch the
next one:

```powershell
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset <next_offset> --limit 50
```

**Do not pause or wait for human review.**  Continue processing batches
until `next_offset` is `null` (end of data).

### Progress checkpoints

After every 500 tokens processed, print a brief progress summary:

```
✓ Processed 500 tokens (offset 0–499), corrected 42 unique words (affecting 318 tokens total).
  Continuing from offset 500…
```

This helps the human monitor progress if they are watching, but does NOT
require them to take any action.

---

## Database Fields Reference

When a root correction is applied, these fields are updated:

| Field             | Old Value                    | New Value                                      |
|-------------------|------------------------------|-------------------------------------------------|
| `Token.root`      | e.g. "رحمن"                  | e.g. "رحم" (the corrected root)                |
| `Token.root_id`   | FK to old Root row           | FK to new Root row (created if it didn't exist) |
| `Token.status`    | Any status                   | `"verified"` (agent-verified)                   |
| `Token.root_sources` | `{"alkhalil": "رحمن"}`    | `{"alkhalil": "رحمن", "agent_review": "رحم"}`  |
| `Token.updated_at`| Previous timestamp           | Current timestamp (automatic)                   |
| `Root.token_count` (old) | N                      | N - (number of updated tokens)                  |
| `Root.token_count` (new) | M                      | M + (number of updated tokens)                  |

### Fields you do NOT need to update
- `Token.text_ar` — original Arabic text, never changes
- `Token.normalized` — normalized text, never changes  
- `Token.sura`, `Token.aya`, `Token.position` — location, never changes
- `Token.verse_id` — verse FK, unrelated to root
- `Token.pattern` — morphological pattern; left as-is for now
- `Token.interpretations` — meanings; left as-is
- `Token.references` — deprecated, ignore
- `Token.created_at` — immutable

---

## Safety — Git LFS Database Snapshots

The database (`quran.db`) is tracked via **Git LFS**.  Before starting a
root correction session, create a snapshot so the human can roll back if
anything goes wrong:

```powershell
git add quran.db
git commit -m "DB snapshot before root review session"
```

To revert to a previous snapshot:

```powershell
git checkout HEAD~1 -- quran.db
```

---

## File Locations

| File                              | Purpose                                           |
|-----------------------------------|---------------------------------------------------|
| `scripts/review_roots_fetch.py`   | Fetch token batches from DB                       |
| `scripts/review_roots_apply.py`   | Apply corrections to DB (single-token mode)       |
| `data/root_review_applied_log.json` | Permanent: audit log of all applied corrections |

---

## Quick-Start Checklist

```
[ ] 1. Activate venv:       .venv\Scripts\Activate.ps1
[ ] 2. Snapshot DB:          git add quran.db; git commit -m "DB snapshot before review"
[ ] 3. Fetch batch:          .venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 0 --limit 50
[ ] 4. For each unique normalized word with a wrong root:
       - Determine the correct root (or use the word itself if no root exists)
       - Apply the correction to ALL occurrences via bulk update (see Step 3b)
[ ] 5. Fetch next batch (use next_offset), go to step 4
[ ] 6. When next_offset is null, you are done — commit the final DB state:
       git add quran.db; git commit -m "Root review complete"
```
