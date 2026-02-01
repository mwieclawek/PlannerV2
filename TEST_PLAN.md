# Planner V2 - Comprehensive Test Plan

This document outlines the testing strategy for the Planner V2 application, focusing on the Manager and Employee workflows, API integration, and critical bug verification.

## 1. Environment Setup
Before running tests, ensure the environment is correctly configured:
- **Backend**: Running on `http://localhost:8000` (`uvicorn backend.app.main:app --reload`).
- **Frontend**: Running on `http://localhost:5000` (`flutter run -d web-server`).
- **Database**: `planner.db` (SQLite) initialized.

---

## 2. Manual End-to-End (E2E) Scenarios
These tests should be performed in a Chrome browser using the incognito mode to avoid caching issues.

### Scenario A: Manager Workflow (Critical Path)
**Goal**: Verify the entire scheduling loop from configuration to generation.

1.  **Registration**
    *   Navigate to `/`.
    *   Click "Zarejestruj się".
    *   **Input**: Name: "Test Manager", Email: `manager@test.com`, Pass: `password`, **Role: Manager**.
    *   **Expected**: Redirect to Manager Dashboard ("Panel Managera").

2.  **Configuration (Setup)**
    *   Go to "Konfiguracja" tab.
    *   **Action**: Add Job Role (e.g., "Barista", Color: Red).
    *   **Action**: Add Shift (e.g., "Rano", 08:00 - 16:00).
    *   **Expected**: New items appear in the lists below immediately.

3.  **Requirements Definitions (Fix Verification)**
    *   Go to "Wymagania" tab.
    *   **Check**: Page loads without Red Screen of Death (verifies `Requirement.id` type fix).
    *   **Action**: Set "Barista" count to `1` for "Rano" shift on Monday.
    *   **Action**: Click "Zapisz Wymagania".
    *   **Expected**: Green snackbar "Wymagania zapisane".

4.  **Schedule Generation**
    *   Go to "Grafik" tab.
    *   **Action**: Click "Generuj Grafik (AI)".
    *   **Expected**: Result display (either "Sukces" or "Niewykonalne" - *not* an application crash).

### Scenario B: Employee Workflow
**Goal**: Verify availability submission and schedule viewing.

1.  **Registration**
    *   Navigate to `/` (or logout).
    *   Click "Zarejestruj się".
    *   **Input**: Name: "Jan Kowalski", Email: `jan@test.com`, Pass: `password`, **Role: Pracownik**.
    *   **Expected**: Redirect to Employee Dashboard ("Panel Pracownika").

2.  **Availability**
    *   **Action**: In "Dostępność" tab, click on Monday cells to mark availability.
    *   **Action**: Click "Zapisz".
    *   **Expected**: Success message.

3.  **My Schedule**
    *   Go to "Mój Grafik" tab.
    *   **Check**: Page loads without error invocation types (verifies `time` vs `String` serialization).
    *   **Expected**: "Brak zmian w tym tygodniu" (if schedule not generated yet) or card list.

---

## 3. Automated Integration Tests
Located in `frontend/integration_test/manager_flow_test.dart`.

**Command:**
```bash
flutter test integration_test/manager_flow_test.dart -d chrome
```
*Note: Requires `chromedriver` in PATH.*

**Scope:**
- Automated registration of Manager.
- Interaction with Setup inputs.
- Verification of Requirements tab loading (automated regression test for the "String vs int" bug).

---

## 4. Unit Tests
Located in `frontend/test/`.

### Model Tests (`requirements_test.dart`)
**Goal**: Verify JSON serialization resilience.
- **TestCase 1**: Parse `Requirement` JSON with UUID string as `id`.
- **TestCase 2**: Parse `EmployeeSchedule` JSON with "08:00:00" string as `start_time`.

**Command:**
```bash
flutter test test/model_test.dart
```

---

## 5. Critical Bug Regression List
| ID | Bug Description | Verification Step | Status |
|----|-----------------|-------------------|--------|
| **BUG-01** | `TypeError: 'String' is not a subtype of 'int'` in Requirements | Open "Wymagania" tab. If grid loads, PASS. | **FIXED** |
| **BUG-02** | `type 'time' is not a subtype of type 'String'` in Employee Schedule | Open "Mój Grafik" tab. If UI loads, PASS. | **FIXED** |
