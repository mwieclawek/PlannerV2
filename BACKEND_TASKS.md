# Backend Implementation Tasks - Sprint 4: Advanced Control & Configuration

## Cel
Rozbudowa zarządzania (CRUD), walidacja zmian i zmiana podejścia do zapisu grafiku (Tryb edycji/zapisu).

## 1. Zarządzanie Słownikami (CRUD)
Plik: `backend/app/routers/manager.py`

- [ ] **Edycja/Usuwanie Ról**:
    - `PUT /manager/roles/{id}`: Aktualizacja nazwy/koloru.
    - `DELETE /manager/roles/{id}`: Usunięcie roli (Sprawdzić czy nie używana w grafikach? Opcjonalnie Cascade lub Block).
- [ ] **Edycja/Usuwanie Zmian**:
    - `PUT /manager/shifts/{id}`: Aktualizacja.
    - `DELETE /manager/shifts/{id}`: Usunięcie.
- [ ] **Walidacja Unikalności Zmian**:
    - Przy tworzeniu/edycji zmiany sprawdzić, czy nie istnieje inna o identycznym `start_time` i `end_time` (klucz biznesowy).

## 2. Konfiguracja Restauracji
Plik: `backend/app/routers/manager.py` (lub nowy `config.py`)

- [ ] **Model i Endpoint**:
    - Model `RestaurantConfig`: `name`, `opening_hours` (JSON), `address`, etc.
    - `GET /manager/config`: Pobierz konfig.
    - `POST /manager/config`: Zapisz/Nadpisz konfig.

## 3. Zmiana Logiki Generowania i Zapisu Grafiku
Plik: `backend/app/routers/scheduler.py`

- [ ] **Refaktor `POST /scheduler/generate`**:
    - **Zmiana**: Nie zapisuj wyniku od razu do bazy!
    - **Return**: Zwróć wygenerowaną listę obiektów `Schedule` jako "propozycję" (JSON).
- [ ] **Nowy Endpoint**: `POST /scheduler/save_batch` (lub `/bulk`)
    - **Input**: Lista obiektów `Schedule` (lub podobnych DTO).
    - **Logika**: 
        1. Wyczyść grafik w danym zakresie dat (na podstawie dat w payloadzie).
        2. Zapisz przesłaną listę.
    - **Cel**: Obsługa przycisku "Zapisz", który utrwala zarówno grafik z AI jak i ręczne zmiany zrobione na froncie przed zapisem.
