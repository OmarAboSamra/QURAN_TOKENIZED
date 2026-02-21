# Root Cross-Check Guide (Second Agent)

> **Audience**: A second AI agent using a different model, tasked with
> independently verifying Arabic root assignments made by the first agent.
>
> **Goal**: Compare your own linguistic judgment against the existing
> root assignments and flag any disagreements.

> **Workspace root**: `c:\quran-backend`

---

## Background

A first agent has reviewed all 77,433 Qur'anic word tokens and assigned
a root (جذر) to each one.  The assignments follow these rules:

1. **Content words** (nouns, verbs, adjectives) → trilateral/quadrilateral
   Arabic root (e.g., كتاب → كتب, يعبدون → عبد)
2. **Function words** (particles, prepositions, pronouns, demonstratives,
   relative pronouns, conjunctions) → the **normalized word itself** as
   root (e.g., في → في, الذين → الذين, ولا → ولا)
3. **Foreign proper nouns** (إبراهيم, موسى, فرعون, etc.) → the
   **normalized word itself**
4. **Every unique normalized form maps to exactly one root** — all
   occurrences of the same word share the same root.

---

## Your Task

Review the root assignments and produce a corrections file listing any
entries where you disagree with the assigned root.

### Step 1 — Get the data

The file `data/root_assignments_for_review.json` contains all 14,801
unique word→root mappings.  Each entry looks like:

```json
{
  "normalized": "الكتـب",
  "assigned_root": "كتب",
  "example_text": "ٱلْكِتَـٰبُ",
  "count": 150,
  "first_occurrence": "2:2"
}
```

| Field             | Meaning                                      |
|-------------------|----------------------------------------------|
| `normalized`      | The word after removing diacritics/tatweel    |
| `assigned_root`   | The root assigned by the first agent          |
| `example_text`    | One Arabic text occurrence (with diacritics)  |
| `count`           | How many times this word appears in the Qur'an|
| `first_occurrence`| Sura:Aya of first appearance                  |

### Step 2 — Evaluate each mapping

For each entry, use your Arabic linguistics knowledge to determine
whether `assigned_root` is correct.

#### Rules for evaluation

1. **Content words**: The root should be the **trilateral (or quadrilateral)
   base** of the word.  Strip all prefixes (ال، ب، ك، ل، ف، و، س، ي، ت، ن، أ),
   suffixes (ون، ين، ات، ة، هم، كم، نا، ه، ها، ي), and augmented letters
   (حروف الزيادة: سألتمونيها) to find the root consonants.

2. **Function words**: If the word is a particle, preposition, pronoun,
   demonstrative, or relative pronoun, the root should equal the
   **normalized word itself** (not a trilateral root).

3. **Foreign proper nouns**: If the word is a non-Arabic proper noun
   (e.g., إبراهيم، موسى، عيسى، فرعون), the root should equal the
   **normalized word itself**.

4. **Root = normalized means "no root"**: When `assigned_root` equals
   `normalized`, it means the first agent classified this word as having
   no trilateral root.  Verify this classification.

#### Common patterns to check

| Pattern                          | Example              | Expected root  |
|----------------------------------|----------------------|----------------|
| Simple noun/verb                 | كتاب                 | كتب            |
| Definite article prefix          | الكتاب               | كتب            |
| Conjunction + content word       | وقال                 | قول            |
| Preposition + content word       | بالحق                | حقق            |
| Verb with imperfect prefix       | يعلمون               | علم            |
| فعيل adjective                   | عليم                 | علم            |
| فعول adjective                   | غفور                 | غفر            |
| Hollow verb                      | قال                  | قول            |
| Defective verb                   | هدى                  | هدي            |
| Preposition (no root)            | في، من، على          | في، من، علي    |
| Pronoun (no root)                | هو، هم، أنا          | هو، هم، انا    |
| Demonstrative (no root)          | ذلك، هذا             | ذلك، هـذا      |
| Relative pronoun (no root)       | الذي، الذين          | الذي، الذين    |
| Compound function words          | ولا، وما، بما        | ولا، وما، بما  |
| Prep + pronoun suffix            | عليهم، فيها، به      | عليهم، فيها، به|

### Step 3 — Process in batches

The file has 14,801 entries.  Process them in batches:

```powershell
# Load and process in Python
.venv\Scripts\python.exe -c "
import json
with open('data/root_assignments_for_review.json', encoding='utf-8') as f:
    data = json.load(f)
print(f'Total entries: {len(data)}')
# Process entries 0-99
for entry in data[0:100]:
    print(f'{entry[\"normalized\"]} -> {entry[\"assigned_root\"]} ({entry[\"count\"]}x)')
"
```

You can also use the fetch script to see tokens in context:

```powershell
.venv\Scripts\python.exe scripts/review_roots_fetch.py --offset 0 --limit 50
```

### Step 4 — Record disagreements

Create a JSON file `data/root_crosscheck_corrections.json` with this format:

```json
{
  "agent_model": "<your model name>",
  "reviewed_at": "<ISO timestamp>",
  "total_reviewed": 14801,
  "total_disagreements": 0,
  "corrections": [
    {
      "normalized": "example_word",
      "current_root": "current_assigned_root",
      "suggested_root": "your_suggested_root",
      "reason": "Brief explanation of why you disagree",
      "confidence": "high|medium|low"
    }
  ]
}
```

#### Confidence levels

| Level    | When to use                                                |
|----------|------------------------------------------------------------|
| `high`   | You are certain the assigned root is wrong                 |
| `medium` | You believe the root is wrong but have some uncertainty    |
| `low`    | You suspect an issue but it could go either way            |

### Step 5 — Apply corrections

After the cross-check is complete, the human will review corrections
from both agents and apply the final results.  To apply corrections
directly (if authorized):

```powershell
# The correction script reads root_crosscheck_corrections.json and
# updates all tokens with matching normalized forms.
.venv\Scripts\python.exe scripts/apply_crosscheck_corrections.py --dry-run
.venv\Scripts\python.exe scripts/apply_crosscheck_corrections.py
```

---

## Quick Reference: Arabic Root Extraction

### Trilateral roots (most common)
Strip all affixes to find 3 root consonants:
- كاتبون → كتب (remove ا augment, ون suffix)
- استغفروا → غفر (remove است prefix, وا suffix)
- يتعلمون → علم (remove ي prefix, ت، و، ن)

### Weak roots (حروف العلة)
- Hollow: قال/يقول → قول (middle letter و/ي)
- Defective: هدى/يهدي → هدي (final letter و/ي)
- Assimilated: وعد/يعد → وعد (first letter و)

### Doubled roots
- ضلّ → ضلل (2nd and 3rd radicals are the same)
- مسّ → مسس
- حقّ → حقق

### Hamzated roots
- أمن/يؤمن → امن
- سأل → سال
- قرأ → قرا

---

## Important: Do NOT modify the database directly

Work only with the JSON files.  The human will decide which corrections
to apply after comparing both agents' outputs.

---

## File Locations

| File                                    | Purpose                         |
|-----------------------------------------|---------------------------------|
| `data/root_assignments_for_review.json` | Input: all word→root mappings   |
| `data/root_crosscheck_corrections.json` | Output: your disagreements      |
| `scripts/review_roots_fetch.py`         | Fetch tokens from DB (context)  |
| `scripts/export_root_assignments.py`    | Regenerate the review file      |
