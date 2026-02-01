# Strict Browser Agent Click-Through Plan

**Role:** High-Speed Click Executor (Gemini 1.5 Flash / 3 Pro Fast)
**Goal:** Execute UI tests as fast as possible, purely following coordinates/selectors. Minimize "thinking" or DOM analysis time. NO SCREENSHOTS.
**Output:** Log results to `TEST_RESULTS.log` (Append mode).

## Agent Configuration Parameters
*   **Model Temperature:** 0.0 (Deterministic execution)
*   **Thinking Budget:** Minimize. Trust the selectors/coordinates below.
*   **Screenshot Policy:** **DISABLE**. Do not take screenshots unless a fatal error occurs. This saves huge amounts of time.
*   **Wait Times:** Use fixed `wait(500)` instead of `wait_for_selector` where possible for speed, unless network dependent.
*   **Browser Window:** Start MAXIMIZED (1920x1080) to ensure coordinate stability.
*   **Task:** Split into micro-tasks if possible, but preferably one continuous fast flow.

---

## EXECUTION SCRIPT

### 0. Initialization
1.  **Open Log File**: Create/Append to `TEST_RESULTS.log`.
2.  **Log Start**: Write "START: [Timestamp]"
3.  **Navigate**: `http://localhost:5000`

### 1. Registration (Manager) - FAST PATH
*   **Action**: Click "Zarejestruj się" (Bottom link).
    *   *Selector*: `text="Zarejestruj się"` OR *Pixel*: `(530, 710)`
*   **Wait**: 500ms
*   **Input Name**: Click `(500, 470)` -> Type "SpeedMgr_[RANDOM_ID]"
*   **Input Email**: Tab -> Type "speed_mgr_[RANDOM_ID]@test.com"
*   **Input Pass**: Tab -> Type "pass123"
*   **Role Selection**:
    *   Tab (Focus Role)
    *   Type "m" (Select Manager)
    *   Enter
*   **Submit**: Tab -> Enter (Or Click `(500, 680)`)
*   **Log**: "STEP 1: Registration Submitted"

### 2. Verify Dashboard Load
*   **Wait**: 2000ms (Allow redirect)
*   **Check**: Look for text "Panel Managera" or "Brak nadchodzących zmian".
*   **Log**: IF found -> "STEP 2: Dashboard Loaded - PASS" ELSE "STEP 2: FAIL"

### 3. Setup (Konfiguracja)
*   **Nav**: Click Tab "Konfiguracja" (Bottom Nav, 2nd icon) OR `text="Konfiguracja"`.
*   **Wait**: 500ms
*   **Add Role**:
    *   Click FAB (+) `(Right-Bottom corner)` -> "Dodaj Stanowisko"
    *   Input: "FastRole"
    *   Click "Zapisz"
*   **Add Shift**:
    *   Click FAB (+) -> "Dodaj Zmianę"
    *   Input: "FastShift", Start "09:00", End "17:00"
    *   Click "Zapisz"
*   **Log**: "STEP 3: Config Setup - DONE"

### 4. Requirements (BUG CHECK)
*   **Nav**: Click Tab "Wymagania" (Bottom Nav, 3rd icon) OR `text="Wymagania"`.
*   **Wait**: 1000ms
*   **CRITICAL CHECK**:
    *   Check for text "Wymagania Obsadowe".
    *   Check specifically for **absence** of "Error" or Red Screen.
*   **Action**:
    *   Click first cell `(Monday, FastShift)`
    *   Type "1"
    *   Click "Zapisz" (Top right or Bottom FAB)
*   **Log**: IF success -> "STEP 4: Requirements Save - PASS (Fix Verified)" ELSE "STEP 4: FAIL"

### 5. Schedule Generation
*   **Nav**: Click Tab "Grafik" (Bottom Nav, 1st icon).
*   **Action**: Click "Generuj Grafik (AI)".
*   **Wait**: 3000ms (AI processing)
*   **Log**: "STEP 5: Generation Triggered - DONE"

### 6. Cleanup & Exit
*   **Action**: Click "Wyloguj" (Top Right icon).
*   **Log**: "END: [Timestamp] - SUCCESS"

---

## Error Handling
*   If ANY step fails (element not found > 2s):
    1.  Log "ERROR at [Step Name]" to file.
    2.  Exit immediately. Do not retry.
