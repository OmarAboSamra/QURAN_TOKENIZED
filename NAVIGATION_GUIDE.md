# Enhanced Frontend Navigation Guide

## Overview

The `/demo-enhanced` endpoint now supports **full Qur'an navigation** with URL-driven state management, allowing users to browse any sura with pagination and share deep links.

## URL Structure

```
/demo-enhanced?sura=<N>&page=<P>
```

**Parameters:**
- `sura` (optional): Sura number 1-114. Default: 1
- `page` (optional): Page number ≥ 1. Default: 1

**Examples:**
```
/demo-enhanced                    → Sura 1, Page 1 (default)
/demo-enhanced?sura=1             → Sura 1, Page 1
/demo-enhanced?sura=2&page=1      → Sura 2 (Al-Baqarah), Page 1
/demo-enhanced?sura=2&page=3      → Sura 2, Page 3
/demo-enhanced?sura=3             → Sura 3 (Aal-E-Imran), Page 1
```

## Features

### 1. Sura Dropdown Navigation

**Location:** Top header, right side  
**Format:** "1. الفاتحة - Al-Fatiha"  
**Behavior:**
- Lists all 114 suras with Arabic and English names
- Selecting a sura:
  - Sets `currentSura` state to selected value
  - Resets `currentPage` to 1
  - Updates URL to `?sura=<N>&page=1`
  - Fetches `/quran/tokens?sura=<N>&page=1&page_size=1000`
  - Fetches `/quran/stats?sura=<N>` to calculate total pages

**Implementation:**
```javascript
const handleSuraChange = (sura) => {
    setCurrentSura(sura);
    setCurrentPage(1);
    updateURL(sura, 1);  // Uses window.history.pushState
};
```

### 2. Pagination Controls

**Location:** Above and below verse list  
**Display:** "الصفحة 1 من 6" (Page 1 of 6)  
**Buttons:**
- "▶ السابقة" (Previous)
- "التالية ◀" (Next)

**Behavior:**
- Hidden when `totalPages === 1` (e.g., short suras)
- Clicking Next/Previous:
  - Clamps page between 1 and totalPages
  - Updates `currentPage` state
  - Updates URL to `?sura=<N>&page=<P>`
  - Fetches new page data
  - Scrolls to top smoothly

**Calculation:**
```javascript
const PAGE_SIZE = 1000;
const totalPages = Math.ceil(suraStats.total_tokens / PAGE_SIZE);
```

**Example:** Sura 2 (Al-Baqarah) has ~6,200 words  
- Page 1: Tokens 1-1000 (Verses 1-142)
- Page 2: Tokens 1001-2000 (Verses 143-212)
- ...
- Page 7: Remaining tokens

### 3. Jump to Āyah Dropdown

**Location:** Top header, center  
**Format:** "آية 1", "آية 2", etc.  
**Behavior:**
- Dynamically populated with ayah numbers present on current page
- Selecting an ayah:
  - Finds element with `id="ayah-<N>"`
  - Smoothly scrolls it into view (centered)
  - Applies yellow flash highlight for 1 second
  - Optionally updates URL hash `#ayah=<N>`

**Implementation:**
```javascript
const handleJumpToAyah = (ayah) => {
    if (!ayah) return;
    const element = document.getElementById(`ayah-${ayah}`);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.style.backgroundColor = '#fef3c7';
        setTimeout(() => {
            element.style.backgroundColor = '';
        }, 1000);
    }
};
```

### 4. Search Box

**Location:** Below header, above pagination  
**Label:** "🔍 البحث في الصفحة الحالية"  
**Behavior:**
- Filters tokens on **currently loaded page only** (client-side)
- Searches in:
  - `text_ar` (original Arabic text)
  - `normalized` (without diacritics)
  - `root` (Arabic root)
- Debounced 300ms to avoid lag
- Shows result count: "42 نتيجة"

**Implementation:**
```javascript
const filteredTokens = useMemo(() => {
    if (!searchTerm) return tokens;
    const term = searchTerm.toLowerCase();
    return tokens.filter(token =>
        token.text_ar.includes(term) ||
        token.normalized.includes(term) ||
        (token.root && token.root.includes(term))
    );
}, [tokens, searchTerm]);
```

### 5. Info Bar

**Location:** Below header  
**Display:**
- **Right side:** Sura info
  - "سورة البقرة (2)"
  - "الصفحة 1 من 6 – الآيات 1–142"
- **Left side:** Stats for current sura
  - Total words
  - Total verses
  - Unique roots

**Data Source:**
```
GET /quran/stats?sura=2
```

**Response:**
```json
{
    "total_tokens": 6221,
    "total_verses": 286,
    "total_roots": 892,
    "suras": 114
}
```

## Backend API Changes

### Enhanced `/quran/stats` Endpoint

**Before:**
```
GET /quran/stats  → Overall database stats
```

**After:**
```
GET /quran/stats              → Overall stats (all suras)
GET /quran/stats?sura=2       → Stats for Sura 2 only
```

**Implementation:**
```python
async def get_stats(
    sura: Optional[int] = Query(None, ge=1, le=114),
    db: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    if sura:
        # Sura-specific stats
        total_tokens = await token_repo.acount_filtered(db, sura=sura)
        # ... count verses and roots for this sura
    else:
        # Overall stats
        total_tokens = await token_repo.acount(db)
        # ... count all verses and roots
```

## Example User Flows

### Flow 1: Browse Sura 2

1. User opens: `/demo-enhanced`
2. Frontend loads Sura 1, Page 1 (default)
3. User selects "2. البقرة - Al-Baqarah" from dropdown
4. URL changes to: `/demo-enhanced?sura=2&page=1`
5. Frontend fetches:
   - `GET /quran/stats?sura=2` → Get total tokens (6221)
   - `GET /quran/tokens?sura=2&page=1&page_size=1000` → Get first 1000 tokens
6. Frontend displays:
   - Header: "سورة البقرة (2)"
   - Info: "الصفحة 1 من 7 – الآيات 1–142"
   - Pagination: "Page 1 of 7" with Next button
   - Tokens grouped by verse

### Flow 2: Navigate to Page 3 of Sura 2

1. User clicks "التالية ◀" (Next) button twice
2. URL updates each time:
   - Click 1: `/demo-enhanced?sura=2&page=2`
   - Click 2: `/demo-enhanced?sura=2&page=3`
3. Frontend fetches:
   - `GET /quran/tokens?sura=2&page=3&page_size=1000`
4. Display updates to verses on page 3
5. Page scrolls to top smoothly

### Flow 3: Jump to Specific Verse

1. User is viewing Sura 2, Page 1 (verses 1-142)
2. "Jump to Āyah" dropdown shows: آية 1, آية 2, ..., آية 142
3. User selects "آية 50"
4. Frontend:
   - Finds `<div id="ayah-50">`
   - Scrolls smoothly to center it in viewport
   - Applies yellow flash highlight
5. Verse 50 is now visible and highlighted

### Flow 4: Search Within Page

1. User is viewing Sura 2, Page 1
2. User types "الله" in search box
3. After 300ms debounce:
   - Frontend filters tokens client-side
   - Only verses containing "الله" are shown
   - Result count displayed: "23 نتيجة"
4. User clears search → All verses reappear

### Flow 5: Share Deep Link

1. User navigates to Sura 2, Page 3
2. URL is: `/demo-enhanced?sura=2&page=3`
3. User copies URL and shares with colleague
4. Colleague opens link → Sees exact same view (Sura 2, Page 3)
5. No additional navigation needed

## Technical Details

### State Management

**URL as Source of Truth:**
```javascript
// On mount, parse URL
useEffect(() => {
    const params = getQueryParams();
    setCurrentSura(params.sura);  // Default: 1
    setCurrentPage(params.page);  // Default: 1
}, []);

// When sura/page changes, update URL
function updateURL(sura, page) {
    const url = new URL(window.location);
    url.searchParams.set('sura', sura);
    url.searchParams.set('page', page);
    window.history.pushState({}, '', url);
}
```

**React State:**
```javascript
const [currentSura, setCurrentSura] = useState(1);
const [currentPage, setCurrentPage] = useState(1);
const [totalPages, setTotalPages] = useState(1);
const [tokens, setTokens] = useState([]);
const [suraStats, setSuraStats] = useState(null);
const [searchTerm, setSearchTerm] = useState('');
```

### Data Fetching

**When sura or page changes:**
```javascript
useEffect(() => {
    const fetchData = async () => {
        setLoading(true);
        
        // 1. Get stats to calculate pages
        const statsRes = await fetch(`/quran/stats?sura=${currentSura}`);
        const stats = await statsRes.json();
        const pages = Math.ceil(stats.total_tokens / PAGE_SIZE);
        setTotalPages(pages);
        
        // 2. Get tokens for current page
        const tokensRes = await fetch(
            `/quran/tokens?sura=${currentSura}&page=${currentPage}&page_size=${PAGE_SIZE}`
        );
        const tokensData = await tokensRes.json();
        setTokens(tokensData.tokens);
        
        setLoading(false);
    };
    
    fetchData();
}, [currentSura, currentPage]);
```

### Verse Grouping

**Transform flat token list into verse groups:**
```javascript
const verseGroups = useMemo(() => {
    const groups = {};
    filteredTokens.forEach(token => {
        if (!groups[token.aya]) {
            groups[token.aya] = [];
        }
        groups[token.aya].push(token);
    });
    return groups;
}, [filteredTokens]);

// Render
Object.entries(verseGroups)
    .sort(([a], [b]) => parseInt(a) - parseInt(b))
    .map(([aya, tokens]) => (
        <VerseGroup key={aya} verse={aya} tokens={tokens} />
    ))
```

## Component Architecture

```
App (Main Container)
├── NavigationHeader
│   ├── Sura Dropdown (114 suras)
│   ├── Jump to Āyah Dropdown
│   └── Current Sura Info Badge
├── Info Bar (Stats + Ayah Range)
├── SearchBar (Client-side filter)
├── Pagination (Top)
├── Verse List
│   └── VerseGroup (for each ayah)
│       └── TokenCard (for each token)
│           └── Root Badge (clickable)
├── Pagination (Bottom)
└── RootModal (for root lookup)
```

## Styling Notes

**RTL Support:**
- All text right-aligned
- Flexbox with `justify-end` for RTL layout
- Select dropdowns use `dir="rtl"` attribute
- Gradient backgrounds flow right-to-left

**Responsive Design:**
- Header: 3-column grid on desktop, stacked on mobile
- Token cards: 3 columns → 2 → 1 based on screen size
- Pagination controls scale on mobile

**Accessibility:**
- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus indicators on form controls
- Loading spinner with descriptive text
- Error messages with retry button

## Testing Checklist

- [ ] Load `/demo-enhanced` → Shows Sura 1, Page 1
- [ ] Load `/demo-enhanced?sura=2` → Shows Sura 2, Page 1
- [ ] Load `/demo-enhanced?sura=2&page=3` → Shows Sura 2, Page 3
- [ ] Change sura via dropdown → URL updates, data reloads
- [ ] Click Next/Previous → Page increments/decrements, URL updates
- [ ] Jump to ayah → Scrolls smoothly, highlights verse
- [ ] Type in search → Filters client-side, shows count
- [ ] Click root badge → Modal opens with all occurrences
- [ ] Pagination hides for short suras (e.g., Sura 1)
- [ ] Error handling works (try `?sura=999`)
- [ ] Loading spinner shows during fetch
- [ ] Browser back/forward buttons work correctly
- [ ] Share URL with colleague → Opens exact same view

## Future Enhancements

**Planned:**
- [ ] Add verse-level bookmarking with `#ayah=N` hash
- [ ] Implement server-side search across all suras
- [ ] Add "Recently Viewed" suras list
- [ ] Support for translations (English, Urdu, etc.)
- [ ] Advanced filters: by root, by word length, by status
- [ ] Export current page as PDF or JSON
- [ ] Keyboard shortcuts (j/k for prev/next page)

**Nice to Have:**
- [ ] Progressive Web App (PWA) support
- [ ] Offline mode with Service Worker
- [ ] Dark mode toggle
- [ ] Font size adjuster
- [ ] Audio recitation integration
- [ ] Tafsir (commentary) panel

## Troubleshooting

**Problem:** Page loads but no tokens shown  
**Solution:** Check if sura has been processed via `/pipeline/process-sura?sura=N`

**Problem:** Page X shows "no data" but page X-1 works  
**Solution:** Page is out of range. Frontend should clamp to `totalPages`

**Problem:** URL changes but data doesn't reload  
**Solution:** Ensure `currentSura` and `currentPage` are in `useEffect` dependency array

**Problem:** Search doesn't work  
**Solution:** Search is client-side only. Only filters currently loaded page.

**Problem:** Jump to ayah not working  
**Solution:** Ensure `<div id="ayah-${aya}">` exists and `scroll-mt-24` class applied

## API Reference

### GET /quran/tokens
```
?sura=N         → Filter by sura (1-114)
?page=P         → Page number (1-indexed)
?page_size=K    → Items per page (default: 50, max: 500)
```

### GET /quran/stats
```
?sura=N         → Stats for specific sura (optional)
```

**Response:**
```json
{
    "total_tokens": 6221,
    "total_verses": 286,
    "total_roots": 892,
    "suras": 114
}
```

### GET /quran/root/:root
```
?page_size=K    → Items per page
```

**Response:**
```json
{
    "root": "رحم",
    "total_count": 42,
    "tokens": [...],
    "page": 1,
    "page_size": 100
}
```

---

**Last Updated:** November 13, 2025  
**Version:** 1.0.0
