# Frontend Implementation Tasks - Sprint 4: Advanced Control & Configuration

## Cel
Wdrożenie panelu konfiguracyjnego oraz przebudowa widoku grafiku na tryb "Edycja Lokalna -> Zapis".

## 1. Panel Konfiguracji (Manager > Setup)
Plik: `lib/screens/manager/setup_tab.dart` (rozbudowa) lub nowy ekran

- [ ] **Zakładka "Restauracja"**:
    - Pola do edycji nazwy, godzin otwarcia (jako tekst lub struktura).
- [ ] **Zakładka "Role"**:
    - Lista ról z przyciskami Edytuj/Usuń.
    - Obsługa zapytania `DELETE` (potwierdzenie akcji).
- [ ] **Zakładka "Zmiany"**:
    - Lista definicji zmian (np. "Poranna 06:00-14:00").
    - Edycja/Usuń.
    - Walidacja: Blokada dodania duplikatu czasu (komunikat "Taka zmiana już istnieje").

## 2. Przebudowa Grafiku (Draft Mode)
Plik: `lib/screens/manager/scheduler_tab.dart`

- [ ] **Stan Lokalny**:
    - Dane grafiku (`_scheduleEntries`) są edytowane lokalnie w pamięci aplikacji.
- [ ] **Akcja "Generuj"**:
    - Pobiera propozycję z backendu (bez zapisu w DB).
    - Nadpisuje stan lokalny.
    - **Ostrzeżenie**: Jeśli w stanie lokalnym są niezapisane zmiany, wyświetl Dialog: "Wygenerowanie nowego grafiku usunie Twoje obecne zmiany. Kontynuować?".
- [ ] **Akcja "Dodaj/Edytuj" (Ręczna)**:
    - Zamiast strzelać do API (`saveAssignment`), modyfikuj listę `_scheduleEntries` w pamięci.
    - **Multiple Staff**: Umożliw dodanie wielu pracowników do tej samej komórki (Multiple Chips / List wewnątrz komórki).
- [ ] **Akcja "Zapisz"**:
    - Przycisk "Zapisz zmiany" (np. FAB lub w pasku).
    - Wysyła cały obecny stan (z zakresu widocznego tygodnia) do `POST /scheduler/save_batch`.
    - Po sukcesie: Wyświetl "Zapisano".

## 3. UI/UX Tweaks
- [ ] **Info o niezapisanych zmianach**: Jeśli użytkownik próbuje zmienić datę lub wyjść, a ma niezapisane zmiany -> Warning.
