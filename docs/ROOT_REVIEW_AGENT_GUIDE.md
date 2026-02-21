# Root Review Agent Guide

> **Audience**: An AI agent (Copilot Chat / LLM running in VS Code) that
> will iterate through Qur'anic tokens and verify their Arabic roots
> using its pretrained linguistic knowledge.

> **Workspace root**: `c:\quran-backend`

---

## Overview

The Quran backend database contains ~71,000 word tokens extracted from the
Qur'an.  Each token has a `root` field representing the Arabic root (جذر)
of the word (e.g., the word "كتابًا" has root "كتب").

Many roots were extracted automatically by algorithmic extractors and may
be **incorrect**.  Your job is to:

1. **Fetch** tokens from the database in batches
2. **Evaluate** each token's root using your Arabic linguistics knowledge
3. **Stage** corrections for any roots you believe are wrong
4. **Pause** after 200 staged corrections so the human can review them
5. **Repeat** from step 1 after the human finishes reviewing

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
    "total_matching": 71352,
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
   - If a token is a particle/pronoun and has a root assigned, that is
     likely wrong.  Stage it with `suggested_root` = `null` (or leave blank)
     and explain in the reason.

5. **Proper nouns** may or may not have roots:
   - الله — this is a proper noun; the traditional root is "أله" (some say "وله")
   - إبراهيم، موسى، عيسى — foreign proper nouns, no Arabic root
   - مكة، يثرب — place names, may have roots

6. **Common errors in the current database**:
   - Root is the full word instead of the base root (e.g., "كتاب" instead of "كتب")
   - Root includes the definite article "ال" (e.g., "الرحم" instead of "رحم")
   - Root is from a wrong derivation pattern
   - Augmented letters (حروف الزيادة: سألتمونيها) not stripped correctly

7. **Reference: well-known Qur'anic word roots**:

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

## Step 3 — Stage Suspected Incorrect Roots

When you find a token whose root appears wrong, run:

```powershell
.venv\Scripts\python.exe scripts/review_roots_stage.py --token-id <ID> --suggested-root "<correct_root>" --reason "<explanation>" --confidence <high|medium|low>
```

### Examples

```powershell
# Root is the full word, not the trilateral base
.venv\Scripts\python.exe scripts/review_roots_stage.py --token-id 77557 --suggested-root "رحم" --reason "Current root 'رحمن' is the noun form; trilateral root is رحم" --confidence high

# Root includes the definite article
.venv\Scripts\python.exe scripts/review_roots_stage.py --token-id 77558 --suggested-root "رحم" --reason "Current root 'الرحيم' includes the article ال; base root is رحم" --confidence high

# Particle incorrectly assigned a root
.venv\Scripts\python.exe scripts/review_roots_stage.py --token-id 80001 --suggested-root "" --reason "من is a preposition (particle), it has no Arabic root" --confidence high

# Uncertain — flag for human review
.venv\Scripts\python.exe scripts/review_roots_stage.py --token-id 80500 --suggested-root "وكل" --reason "Could be from وكل (to entrust) or أكل (to eat) depending on context" --confidence low
```

### Confidence levels

| Level    | When to use                                                |
|----------|------------------------------------------------------------|
| `high`   | You are certain the current root is wrong and you know the correct one |
| `medium` | You believe the root is wrong but are not 100% sure of the replacement |
| `low`    | You suspect an issue but need the human to verify          |

### Check progress

```powershell
.venv\Scripts\python.exe scripts/review_roots_stage.py --show
```

---

## Step 4 — Pause at 200 and Notify the Human

After staging corrections, check the count with `--show`.  When the count
reaches **200**, **stop reviewing** and tell the user:

> "I have staged 200 root corrections for your review.
> Please run the following command to review them in the browser:
>
> ```
> streamlit run scripts/review_roots_app.py
> ```
>
> After you finish reviewing and approving, let me know and I will
> continue from offset [next_offset]."

**Do not stage more than 200 corrections at a time.**  Wait for the human
to complete their review before continuing.

---

## Step 5 — Human Reviews in Streamlit

*(This section is for the human, not the agent — included for completeness.)*

The human runs:

```powershell
streamlit run scripts/review_roots_app.py
```

This opens a browser with a table of all staged corrections showing:
- Arabic word (RTL), location (sura:aya:position), normalized form
- Current root (crossed out) → Suggested root (editable text input)
- Reason and confidence level
- Approve checkbox per row

The human:
1. Reviews each row
2. Checks **✓** for corrections they agree with (editing the root if needed)
3. Clicks **Approve selected** (moves to approved file) or **Reject selected** (removes)
4. Repeats until the staging list is empty

---

## Step 6 — Apply Approved Corrections

After the human approves, run:

```powershell
# Preview first
.venv\Scripts\python.exe scripts/review_roots_apply.py --dry-run

# Then apply for real
.venv\Scripts\python.exe scripts/review_roots_apply.py
```

Or the human can click **"Apply now"** in the Streamlit sidebar.

---

## Step 7 — Repeat

After corrections are applied, continue from where you left off:

```powershell
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset <next_offset> --limit 50
```

Repeat steps 2–6 until all tokens have been reviewed.

---

## Database Fields Reference

When a root correction is applied, these fields are updated:

| Field             | Old Value                    | New Value                                      |
|-------------------|------------------------------|-------------------------------------------------|
| `Token.root`      | e.g. "رحمن"                  | e.g. "رحم" (the corrected root)                |
| `Token.root_id`   | FK to old Root row           | FK to new Root row (created if it didn't exist) |
| `Token.status`    | Any status                   | `"verified"` (human-approved)                   |
| `Token.root_sources` | `{"alkhalil": "رحمن"}`    | `{"alkhalil": "رحمن", "agent_review": "رحم"}`  |
| `Token.updated_at`| Previous timestamp           | Current timestamp (automatic)                   |
| `Root.token_count` (old) | N                      | N - 1                                           |
| `Root.token_count` (new) | M                      | M + 1 (Root row created if missing)             |

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

## File Locations

| File                              | Purpose                                           |
|-----------------------------------|---------------------------------------------------|
| `scripts/review_roots_fetch.py`   | Fetch token batches from DB                       |
| `scripts/review_roots_stage.py`   | Stage a suspected-wrong root                      |
| `scripts/review_roots_app.py`     | Streamlit GUI for human review                    |
| `scripts/review_roots_apply.py`   | Apply approved corrections to DB                  |
| `data/root_review_staging.json`   | Temporary: agent's staged corrections             |
| `data/root_review_approved.json`  | Temporary: human-approved corrections             |
| `data/root_review_applied_log.json` | Permanent: audit log of all applied corrections |

---

## Quick-Start Checklist

```
[ ] 1. Activate venv:  .venv\Scripts\Activate.ps1
[ ] 2. Fetch batch:     .venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 0 --limit 50
[ ] 3. For each token with a wrong root, stage it:
       .venv\Scripts\python.exe scripts/review_roots_stage.py --token-id <ID> --suggested-root "<root>" --reason "<why>" --confidence <level>
[ ] 4. Check count:     .venv\Scripts\python.exe scripts/review_roots_stage.py --show
[ ] 5. When count >= 200, tell the user to review:
       streamlit run scripts/review_roots_app.py
[ ] 6. After human review, apply:
       .venv\Scripts\python.exe scripts/review_roots_apply.py
[ ] 7. Continue from next offset, go to step 2
```
