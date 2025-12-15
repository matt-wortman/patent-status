# Code Review Report: Patent Status Tracker - USPTO API Field Expansion

**Review Date:** 2025-12-15
**Risk Level:** MEDIUM
**Recommendation:** CONDITIONAL APPROVAL

---

## Summary

This code review covers the recent changes to the Patent Status Tracker application to capture additional USPTO API fields. The changes span four primary files: `database.py`, `uspto_api.py`, `polling.py`, and `ui.py`.

**Overall Assessment:** The code is well-structured and follows consistent patterns established in the original codebase. The implementation correctly adds comprehensive USPTO data capture. However, there are several security concerns, code quality issues, and potential bugs that should be addressed.

---

## Findings

### 1. SECURITY (DEFENSE-IN-DEPTH): Dynamic Column Name Interpolation in `update_patent()` (LOW)

**File:** `src/database.py`
**Lines:** 330-341

```python
def update_patent(application_number: str, **kwargs):
    # ...
    for key, value in kwargs.items():
        if key in allowed_fields:
            fields.append(f"{key} = ?")  # Column name directly interpolated
            values.append(value)

    if fields:
        values.append(app_num)
        query = f"UPDATE patents SET {', '.join(fields)} WHERE application_number = ?"
        cursor.execute(query, values)
```

**Issue:** Column names are interpolated into the SQL query. In the current implementation this is not practically exploitable because `allowed_fields` is a hardcoded allowlist (and values remain parameterized with `?`). The risk is future maintainers accidentally widening `allowed_fields` with unexpected or untrusted keys.

**Recommendation:** Keep the allowlist, and add a small defense-in-depth guard:
- Validate keys match a strict pattern (e.g., `^[a-z_]+$`)
- Or use an explicit mapping dict (`public_key -> db_column_name`)

---

### 2. SECURITY: Bare `except` Clauses Silently Swallow Errors (MEDIUM)

**File:** `src/polling.py`
**Lines:** 166-167, 174-175, 182-183, 193-194, 201-202, 209-210

```python
except Exception:
    pass  # PTA data is optional
```

**Issue:** Multiple bare `except Exception: pass` blocks silently swallow all exceptions including programming errors, network timeouts, and unexpected API responses. This makes debugging difficult and can hide real issues.

**Recommendation:** Log these exceptions even when continuing execution:

```python
except Exception as e:
    import logging
    logging.debug(f"Optional PTA fetch failed for {app_num}: {e}")
```

---

### 3. CORRECTNESS: `validate_api_key()` Uses Bare `except:` (MEDIUM)

**File:** `src/uspto_api.py`
**Lines:** 207-208

```python
def validate_api_key(api_key: str) -> bool:
    try:
        # ...
        return response.status_code == 200
    except:
        return False
```

**Issue:** The bare `except:` catches everything including `KeyboardInterrupt` and `SystemExit`, which is a Python anti-pattern. It also returns `False` for any exception, not distinguishing between network errors and invalid keys.

**Recommendation:**
```python
except requests.exceptions.RequestException:
    return False
```

---

### 4. BUG: Expiration Date Calculation May Be Incorrect for Leap Years (LOW)

**File:** `src/uspto_api.py`
**Lines:** 263-276

```python
def calculate_expiration_date(filing_date: str, pta_days: int) -> str:
    try:
        filing = datetime.strptime(filing_date, '%Y-%m-%d')
        # Add 20 years
        expiration = filing.replace(year=filing.year + 20)
        # Add PTA days
        expiration = expiration + timedelta(days=pta_days or 0)
        return expiration.strftime('%Y-%m-%d')
    except ValueError:
        return ''
```

**Issue:** Using `replace(year=filing.year + 20)` will raise `ValueError` if the filing date is February 29 (leap year) and 20 years later is not a leap year.

**Recommendation:** Use `dateutil.relativedelta` for proper date arithmetic:
```python
from dateutil.relativedelta import relativedelta
expiration = filing + relativedelta(years=20) + timedelta(days=pta_days or 0)
```

---

### 5. PERFORMANCE: Multiple Sequential Database Updates (MEDIUM)

**File:** `src/polling.py`
**Lines:** 95-211

**Issue:** For each patent, `poll_now()` makes up to 8 separate `db.update_patent()` calls:
1. Main metadata update (line 95-143)
2. PTA data update (line 154-165)
3. Assignment bag update (line 192)
4. Attorney bag update (line 200)
5. Foreign priority bag update (line 208)

Each call opens a connection, builds a query, executes, commits, and closes. For large patent portfolios, this creates significant overhead.

**Recommendation:** Batch updates into a single transaction or consolidate into fewer `db.update_patent()` calls by merging kwargs before calling.

---

### 6. CODE DUPLICATION: `poll_now()` and `refresh_single_patent()` (MEDIUM)

**File:** `src/polling.py`
**Lines:** 61-245 and 270-428

**Issue:** The logic in `poll_now()` (per-patent loop body) and `refresh_single_patent()` is nearly identical - approximately 150 lines of duplicated code. This violates DRY and increases maintenance burden.

**Recommendation:** Extract common logic into a private helper function:
```python
def _update_patent_from_api(patent_id: int, app_num: str) -> dict:
    """Fetch all data and update database for a single patent."""
    # Common implementation here
```

---

### 7. BUG: Orphaned Records on Patent Delete (HIGH)

**File:** `src/database.py`
**Lines:** 248-268

```python
def remove_patent(application_number: str) -> bool:
    # ...
    if row:
        patent_id = row['id']
        cursor.execute("DELETE FROM events WHERE patent_id = ?", (patent_id,))
        cursor.execute("DELETE FROM patents WHERE id = ?", (patent_id,))
```

**Issue:** When a patent is removed, only `events` are deleted. The new tables (`continuity`, `documents`, `assignments`) are not cleaned up, leaving orphaned records.

**Important SQLite note:** Declaring `FOREIGN KEY (...) REFERENCES ...` is not enough by itself. SQLite only enforces foreign keys (and `ON DELETE CASCADE`) when `PRAGMA foreign_keys = ON` is set for each connection. This project opens many short-lived connections; each should enable the pragma.

**Recommendation:** Add deletion for new tables:
```python
cursor.execute("DELETE FROM events WHERE patent_id = ?", (patent_id,))
cursor.execute("DELETE FROM continuity WHERE patent_id = ?", (patent_id,))
cursor.execute("DELETE FROM documents WHERE patent_id = ?", (patent_id,))
cursor.execute("DELETE FROM assignments WHERE patent_id = ?", (patent_id,))
cursor.execute("DELETE FROM patents WHERE id = ?", (patent_id,))
```

---

### 8. CORRECTNESS: Missing UNIQUE Constraint on Assignments (LOW)

**File:** `src/database.py`
**Lines:** 196-213

```python
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patent_id INTEGER NOT NULL,
    reel_number TEXT,
    frame_number TEXT,
    reel_frame TEXT,
    ...
)
```

**Issue:** Unlike `continuity` and `documents` tables which have `UNIQUE` constraints, the `assignments` table has no unique constraint. Combined with `save_assignments()` doing `DELETE` then `INSERT`, this works but is less robust.

**Recommendation:** Add a unique constraint on `(patent_id, reel_frame)` to prevent duplicate assignment records if the delete fails or is interrupted.

---

### 9. MAINTAINABILITY: JSON Stored Twice for Assignments (LOW)

**File:** `src/polling.py`
**Lines:** 186-194

```python
# Fetch and save assignments (optional)
try:
    assign_raw = uspto_api.fetch_assignment(app_num)
    assignments = uspto_api.parse_assignment_data(assign_raw)
    db.save_assignments(patent_id, assignments)
    # Also store as JSON in patents table for quick access
    import json
    db.update_patent(app_num, assignment_bag=json.dumps(assignments))
```

**Issue:** Assignment data is stored both in the `assignments` table (normalized) and in `patents.assignment_bag` (as JSON). This redundancy could lead to data inconsistency and wastes storage.

**Recommendation:** Choose one storage approach or document why both are needed. If `assignment_bag` is for quick UI access, consider a computed property or lazy loading from the assignments table instead.

---

### 10. STYLE: Import Inside Function (LOW)

**File:** `src/polling.py`
**Lines:** 191, 277

```python
# Inside poll_now() loop:
import json
db.update_patent(app_num, assignment_bag=json.dumps(assignments))
```

**Issue:** `json` is imported at the module level in `uspto_api.py` but is imported inside functions in `polling.py`. The module-level import in `polling.py` is missing.

**Recommendation:** Move `import json` to the top of `polling.py`.

---

### 11. SECURITY: API Key Printed to Console on Error (LOW)

**File:** `src/credentials.py`
**Lines:** 22-23, 33-34

```python
except Exception as e:
    print(f"Error storing API key: {e}")
    return False
```

**Issue:** The API key itself is not printed, but `print()` is not ideal for a GUI application. Error strings can still leak environment details and are hard to collect from end users.

**Recommendation:** Use proper logging with appropriate log levels, or remove these print statements for production builds.

---

### 12. CORRECTNESS: Return Type Mismatch / Shape Validation in `parse_application_data()` (LOW)

**File:** `src/uspto_api.py`
**Lines:** 100-103

```python
def parse_application_data(raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not raw_data.get('patentFileWrapperDataBag'):
        return None  # Returns None, but type hint says Dict

    wrapper = raw_data['patentFileWrapperDataBag'][0]  # Could index error if empty list
```

**Issue:** The function returns `None` when data is missing, but its type hint claims it returns a `Dict`. The existing `if not raw_data.get('patentFileWrapperDataBag')` check already prevents indexing an empty list. The more realistic correctness issues are:
- Type hint mismatch (`None` is a valid return)
- Limited shape/type validation if the API returns unexpected types

**Recommendation:** Make the return type `Optional[...]` and validate the bag shape defensively:
```python
bag = raw_data.get('patentFileWrapperDataBag', [])
if not bag:
    return None
wrapper = bag[0]
```

---

### 13. UI: CSV Export Missing New Fields (LOW)

**File:** `src/ui.py`
**Lines:** 1134-1172

**Issue:** The `_on_export_csv()` function only exports the original 10 fields and does not include any of the new fields added (patent_number, expiration_date, grant_date, PTA data, etc.).

**Recommendation:** Update the CSV export to include all commonly-useful fields, or make the export configurable to match visible columns.

---

### 14. PERFORMANCE: Rate Limiting Delay (LOW)

**File:** `src/polling.py`
**Lines:** 232-233

```python
# Increased delay due to additional API calls (6 extra endpoints per patent)
time.sleep(1.0)
```

**Issue:** A fixed 1-second delay is used between patents. With 7 API calls per patent (main + 6 optional), this may still hit rate limits for large portfolios. USPTO rate limits are not publicly documented.

**Recommendation:** Consider implementing exponential backoff on 429 responses, or making the delay configurable in settings.

---

### 15. UX: Days Filter Should Allow Arbitrary Values (MEDIUM)

**File:** `src/ui.py`

**Issue:** The Updates tab currently limits the “Last N days” filter to a fixed dropdown list. Users want to type any number of days.

**Recommendation:** Replace or augment the dropdown with a numeric entry (validate integer >= 1), and persist the last-used value in settings.

---

### 16. UX: Patent Center Link Sometimes Redirects to `/401` (MEDIUM)

**Files:** `src/ui.py`, `src/uspto_api.py`

**Issue:** Some users report that opening Patent Center from the app briefly loads the expected URL, then navigates to `https://patentcenter.uspto.gov/401` (blank for them).

**Recommendation:** Treat this as an environment/site behavior issue (browser policy, corporate filtering, Patent Center SPA routing). Mitigations:
- Ensure the application number passed into the URL is always the normalized digits-only form
- Offer a more reliable fallback (Public PAIR) and/or add an alternative Patent Center deep link
- Document a workaround in-app (“If Patent Center shows /401, use Public PAIR”)

---

## Positive Observations

1. **Good Use of Parameterized Queries:** All database operations use parameterized queries with `?` placeholders, preventing SQL injection on values.

2. **Secure Credential Storage:** API keys are stored using Windows Credential Manager via `keyring`, not in files or environment variables.

3. **Proper Connection Handling:** Database connections are opened and closed within each function, preventing connection leaks.

4. **Defensive Parsing:** The API parsing functions use `.get()` with default values, handling missing fields gracefully.

5. **Migration Strategy:** The `migrate_database()` function properly handles schema evolution with ALTER TABLE statements that gracefully fail if columns exist.

6. **Type Hints:** Good use of type hints throughout for better IDE support and documentation.

7. **Consistent Error Types:** Custom `USPTOApiError` exception provides clear error handling patterns.

---

## Recommendations Summary

| Priority | Issue | File | Action |
|----------|-------|------|--------|
| HIGH | Orphaned records on delete | database.py | Delete related rows and enable FK pragma |
| MEDIUM | Silent exception swallowing | polling.py | Add logging for caught exceptions |
| MEDIUM | Code duplication | polling.py | Extract common refresh logic |
| MEDIUM | Multiple DB updates | polling.py | Batch updates per patent |
| MEDIUM | Days filter too limited | ui.py | Add numeric entry for days |
| MEDIUM | Patent Center redirects to /401 | ui.py | Normalize app # and add fallback/workaround |
| MEDIUM | Bare except in validate_api_key | uspto_api.py | Catch specific RequestException |
| LOW | Column name interpolation | database.py | Regex-validate allowed field keys |
| LOW | Leap year bug | uspto_api.py | Handle leap-day safely (no extra deps) |
| LOW | Import in function | polling.py | Move `json` import to module level |
| LOW | `parse_application_data()` typing/shape | uspto_api.py | Return Optional + validate bag |
| LOW | CSV export incomplete | ui.py | Include new fields or match visible columns |

---

## Action Items

### Must Fix Before Merge
1. Delete related rows (`continuity`, `documents`, `assignments`) in `remove_patent()` and enable `PRAGMA foreign_keys = ON` per DB connection

### Should Fix Soon
2. Add logging for silently-caught exceptions in polling.py
3. Extract duplicated code between `poll_now()` and `refresh_single_patent()`
4. Change bare `except:` to `except requests.exceptions.RequestException:` in validate_api_key()
5. Add editable “days” input for Updates tab
6. Improve CSV export to include new fields / match visible columns
7. Add a Patent Center fallback link or guidance for `/401`

### Nice to Have
8. Batch database updates for performance
9. Fix leap-day expiration date without extra dependencies
10. Move `import json` to module level in polling.py
11. Add stricter key validation for `update_patent()`

---

## Merge Recommendation

**CONDITIONAL APPROVAL** - The code can be merged after addressing the HIGH priority issue (cascade delete for orphaned records). The MEDIUM priority issues should be addressed in a follow-up PR.
