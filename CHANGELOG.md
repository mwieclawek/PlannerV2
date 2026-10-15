# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.1.0] - 2026-10-15

### Added
- **Direct Shift Swap (Bezpośrednia wymiana zmian)**:
  - Możliwość zaoferowania bezpośredniej wymiany zmiany z poziomu widoku „Cała załoga”.
  - Przycisk „Wymień” przy zmianach współpracowników na tej samej roli stanowiskowej.
  - Interaktywny modal wyboru własnej zmiany do oddania z natychmiastową walidacją braku kolizji czasowych.
  - Pełny obieg akceptacji/odrzucenia propozycji wymiany w panelu pracownika i managera.
- **Whole Team Schedule View (Widok całego zespołu)**:
  - Dodano przełącznik widoku u pracownika („Moje zmiany” / „Cała załoga”), umożliwiający podgląd pełnego harmonogramu restauracji dla wszystkich ról.
- **Browser Password Saving (Obsługa menedżerów haseł)**:
  - Dodano autofill hints (`AutofillHints.username`, `AutofillHints.password`) oraz strukturę `AutofillGroup` na formularzu logowania, umożliwiającą natywne zapisywanie i uzupełnianie poświadczeń przez przeglądarki.
- **Draft Schedules & 11h Rest Warnings (Grafiki robocze)**:
  - Obsługa trybu roboczego grafików przed ich publikacją (`is_published`).
  - Mechanizm ostrzeżeń dla managera przed naruszeniem kodeksowego 11-godzinnego odpoczynku dobowego pracownika między zmianami.
- **Shift Audit Log (Historia i audyt zmian grafiku)**:
  - Tabela `shiftauditlog` i migracja bazy danych Alembic rejestrująca każde utworzenie, zmianę godzin, edycję przypisania i usunięcie zmiany wraz z autorem operacji.
  - Interfejs podglądu historii zmian dla managera w module układania grafiku.

### Changed
- **Giełda zmian (Giveaway Claims)**:
  - Wymuszenie walidacji ról: pracownik może przejąć wystawioną na giełdzie zmianę wyłącznie wtedy, gdy posiada przypisaną do niej rolę stanowiskową.
- **Architektura CI / Jenkins**:
  - Wdrożono uruchamianie pełnego pakietu testów backendu (256 testów) w pipeline Jenkins z automatycznym raportowaniem JUnit XML i failowaniem buildu przy błędach.
  - Dynamiczne generowanie kluczy `JWT_SECRET_KEY`, `ENCRYPTION_KEY` i `MANAGER_REGISTRATION_PIN` w środowisku CI zamiast wartości statycznych.
- **Migracja JWT**:
  - Pełna migracja z biblioteki `python-jose` na `PyJWT` ze standaryzowanymi algorytmami kryptograficznymi.

### Fixed
- **Błędy stref czasowych w testach**:
  - Rozwiązano błędy `StatementError: Datetime values must have timezone information` w `pos_service.py` oraz `test_kds.py` poprzez wymuszenie świadomych obiektów `datetime.now(timezone.utc)`.
- **Eliminacja fałszywych błędów Trio**:
  - Usunięto pakiet `trio` ze środowiska testowego oraz dodano fixture `anyio_backend = "asyncio"`, eliminując błąd `RuntimeError: must be called from async context`.
- **Obsługa dialektu PostgreSQL**:
  - Dodano pakiet `psycopg[binary]` dla kompatybilności SQLAlchemy 2.1 oraz automatyczną normalizację prefiksu `postgres://` na `postgresql://`.
- **Bezpieczeństwo uprawnień managera**:
  - Zablokowano możliwość eskalacji uprawnień użytkownika do roli superadmina oraz modyfikacji `tenant_id` przez managera lokalu.
  - Zaimplementowano usuwanie tokenów FCM przy deaktywacji konta użytkownika.

---

## [v2.0.0] - 2026-10-14
- Architektura Multi-Tenancy (izolacja wielu restauracji w jednej instancji).
- Panel Superadmina (`/#/superadmin`).
- Dual-login (email lub username + Login ID/slug).
- Refaktoryzacja modeli i endpointów pod model lokalu.
