# Podręcznik Użytkownika — PlannerV2

Kompleksowa instrukcja obsługi systemu do zarządzania grafikami pracy, personelem, powiadomieniami i zamówieniami kuchennymi.

---

## Spis Treści

1. [Pierwsze Kroki](#1-pierwsze-kroki)  
2. [Panel Managera](#2-panel-managera)  
3. [Panel Pracownika](#3-panel-pracownika)  
4. [Moduł POS / Kitchen Display System](#4-moduł-pos--kitchen-display-system)  
5. [System Powiadomień i Web Push](#5-system-powiadomień-i-web-push)  
6. [Konfiguracja Serwera i Pierwsze Logowanie](#6-konfiguracja-serwera-i-pierwsze-logowanie)  
7. [Najczęstsze Pytania (FAQ)](#7-najczęstsze-pytania-faq)  
8. [Pomoc i Zgłaszanie Błędów](#8-pomoc-i-zgłaszanie-błędów)  
9. [Panel SuperAdmina (Multi-Tenancy)](#9-panel-superadmina-multi-tenancy)  

---

## 1. Pierwsze Kroki

### 1.1 Kto może korzystać z systemu?

System rozróżnia trzy główne role:

| Rola | Uprawnienia |
|------|-------------|
| **Superadmin** | Zarządzanie globalnymi instancjami lokali (Tenants), tworzenie pierwszych managerów, podgląd wszystkich użytkowników |
| **Manager** | Pełna kontrola nad lokalem: konfiguracja, personel, grafiki, obecności, POS, urlopy |
| **Pracownik** | Podgląd grafiku, zgłaszanie dostępności, rejestracja obecności, wymiana i giełda zmian, wnioski urlopowe |

> **Ważne**: Samodzielna rejestracja użytkowników jest wyłączona. Konta w lokalu tworzy wyłącznie Manager lub Superadmin.

### 1.2 Logowanie (Multi-Tenancy)

System wspiera architekturę wielu restauracji (Tenantów) na pojedynczej instancji. Logowanie może odbywać się na dwa sposoby:

1. **Logowanie adresem e-mail** — używasz swojego globalnie unikalnego adresu e-mail oraz hasła (identyfikator lokalu nie jest wymagany).
2. **Logowanie nazwą użytkownika** — wpisujesz swój **Login** (username), **Hasło** oraz **Kod restauracji** (slug / Login ID).

Kroki logowania:
1. Otwórz aplikację w przeglądarce lub na urządzeniu mobilnym.
2. Wypełnij odpowiednie pola formularza w zależności od wybranej metody.
3. Kliknij **„Zaloguj"**.

> **Wskazówka**: Jeśli aplikacja prosi o adres serwera, skontaktuj się z Managerem — może udostępnić parametry połączenia przez **kod QR** (przycisk QR w pasku aplikacji).

#### Komunikaty logowania i błędów

| Komunikat | Znaczenie | Działanie |
|-----------|-----------|-----------|
| *„Nieprawidłowy login lub hasło.”* | Błędne dane uwierzytelniające | Sprawdź login/hasło lub poproś Managera o reset hasła |
| *„Twoje konto zostało zdeaktywowane. Skontaktuj się z administratorem.”* | Konto wyłączone przez Managera | Skontaktuj się z Managerem lokalu |
| *„Błąd połączenia z serwerem. Sprawdź połączenie internetowe lub adres serwera.”* | Brak łączności z backendem | Sprawdź połączenie z siecią lub adres serwera w konfiguracji |

### 1.3 Zmiana Hasła

Każdy użytkownik może samodzielnie zmienić hasło:

1. Kliknij ikonę profilu w prawym górnym rogu -> **„Zmień hasło"**.
2. Podaj dotychczasowe hasło oraz nowe hasło.
3. **Wymogi dotyczące hasła**: minimum 8 znaków, co najmniej jedna wielka litera oraz co najmniej jedna cyfra.
4. Kliknij **„Zmień"**.

> **Wskazówka**: Jeśli zapomniałeś hasła, Manager lokalu może zresetować je w zakładce **Zespół**.

---

## 2. Panel Managera

Po zalogowaniu jako Manager dostępny jest dolny pasek nawigacyjny z zakładkami:

| Zakładka | Opis |
|----------|------|
| **Home** | Dashboard — podgląd dziennego grafiku i statystyki zespołu |
| **Konfiguracja** | Ustawienia restauracji, stanowisk (ról), definicji zmian i wymagań kadrowych |
| **Grafik** | Tygodniowy grafik — generowanie AI, ręczna edycja, publikacja |
| **Obecności** | Ewidencja czasu pracy, zatwierdzanie wpisów, eksport raportu PDF |
| **Zespół** | Zarządzanie pracownikami, statystyki, giełda zmian, wnioski urlopowe |

Górny pasek aplikacji zawiera:
- **Pomoc** — instrukcje i formularz zgłaszania problemów
- **QR** — generowanie kodu QR z adresem serwera dla pracowników
- **Powiadomienia** — lista notyfikacji z panelem zarządzania uprawnieniami Web Push
- **Moduł POS** — przejście do systemu zamówień restauracyjnych
- **Wyloguj**

---

### 2.1 Home (Dashboard)

- **Kalendarz miesięczny** — kliknięcie wybranego dnia prezentuje szczegóły obsady.
- **Lista zmian** — lista zaplanowanych pracowników, godziny pracy i przypisane role.
- **Statystyki dzienne** — podsumowanie liczby pracowników na poszczególnych stanowiskach.

---

### 2.2 Konfiguracja

Zakładka składa się z trzech podsekcji:

#### Podsekcja 1: Restauracja
- Nazwa restauracji (wymagana)
- Adres lokalu
- Godziny otwarcia i zamknięcia (format HH:MM)

#### Podsekcja 2: Role i Zmiany

##### Role (Stanowiska)
Role definiują stanowiska pracy (np. Barista, Kasjer, Kelner, Kucharz).
- Wprowadź nazwę roli i zatwierdź przyciskiem **„Dodaj"**.
- System automatycznie przypisze kolor identyfikacyjny.
- Po dodaniu roli przypisz ją odpowiednim pracownikom w zakładce **Zespół**.

##### Zmiany (Shift Definitions)
Definicje przedziałów czasowych (np. „Rano" 08:00–16:00).
- **Powiązanie z rolami (Role-Based Shifts)**: Każda zmiana jest przypisywana do określonych stanowisk. Pracownicy widzą w panelu dyspozycji wyłącznie te zmiany, które odpowiadają ich rolom.
- **Dni obowiązywania**: Zaznacz dni tygodnia, w których dana zmiana występuje.
- **Reguła nakładania zmian**: System blokuje przypisanie pracownika do zmian nakładających się o więcej niż 30 minut (nakładanie do 30 minut jest dozwolone na przekazanie stanowiska).

#### Podsekcja 3: Wymagania Kadrowe
Definiują liczbę pracowników na danej zmianie dla konkretnej roli.
- **Tryb tygodniowy**: Domyślny szablon stałego zapotrzebowania na każdy dzień tygodnia.
- **Tryb per data**: Zapotrzebowanie na konkretne dni kalendarzowe (nadpisuje szablon tygodniowy przy wydarzeniach specjalnych).

#### Podsekcja 4: Opcje i Moduły Operacyjne
- **Wymóg checklisty przy rejestracji obecności**: Przełącznik decydujący, czy pracownicy muszą potwierdzić wykonanie checklisty stanowiskowej podczas rejestracji wyjścia (check-out). Wyłączenie opcji sprawia, że okno checklisty nie jest wyświetlane.
- **Moduł Zamknięcia Dnia (`enable_daily_closeout`)**: Aktywuje procedurę dziennego rozliczenia i zamykania dnia w lokalu.
- **Pula Napiwków (Tip Pooling)**: Włączenie modułu rozliczania napiwków. W przypadku wyłączenia kafelek Tip Poolingu jest automatycznie ukrywany na pulpicie managera.

---

### 2.3 Grafik

#### Generowanie Automatyczne (OR-Tools Solver)
1. Przejdź do wybranego tygodnia za pomocą strzałek nawigacyjnych.
2. Kliknij **„Generuj grafik"**.
3. Algorytm optymalizacyjny uwzględnia:
   - Zgłoszone dyspozycje pracowników (dostępny / niedostępny)
   - Przypisane role i uprawnienia do zmian
   - Zdefiniowane zapotrzebowanie kadrowe
   - Miesięczne cele godzinowe i zmianowe
   - Ochronę kodeksowego odpoczynku dobowego (minimum 11 godzin przerwy)
   - Dni obowiązywania zmian
4. Wygenerowany grafik pojawia się jako **Szkic (Draft)** — nie jest jeszcze widoczny dla pracowników.

#### Edycja Ręczna i Publikacja
- Kliknij **„+ Dodaj"** w komórce, aby ręcznie przypisać pracownika.
- Kliknij na przypisanego pracownika, aby go usunąć lub zmienić obsadę.
- **Zapisz zmiany**: Zapisuje grafik w bazie danych jako wersję roboczą.
- **Opublikuj**: Publikuje grafik dla zespołu. Pracownicy natychmiast widzą swoje zmiany i otrzymują powiadomienie Push / Web Push.

---

### 2.4 Obecności

Ewidencja i rozliczanie rzeczywistego czasu pracy:
- **Zatwierdzanie obecności nieplanowanych**: Wpisy zarejestrowane przez pracowników poza grafikiem trafiają do statusu `PENDING` i wymagają zatwierdzenia lub odrzucenia przez Managera.
- **Obecności planowane**: Wpisy zgodne z opublikowanym grafikiem uzyskują status `CONFIRMED` automatycznie.
- **Ręczne dodanie obecności**: Umożliwia uzupełnienie ewidencji w przypadku zapomnienia przez pracownika.
- **Eksport PDF**: Generuje oficjalny raport ewidencji czasu pracy z podsumowaniem godzin za wybrany okres.

---

### 2.5 Zespół

- **Lista pracowników**: Przegląd personelu, przypisanych stanowisk i wypracowanych godzin.
- **Tworzenie konta**: Kliknij „+”, podaj imię i nazwisko, login, hasło (min. 8 znaków, 1 wielka litera, 1 cyfra) oraz adres e-mail.
- **Zarządzanie pracownikiem**:
  - Przypisywanie i zmiana ról (stanowisk)
  - Aktualizacja danych osobowych i adresu e-mail
  - Ustalanie miesięcznych celów godzinowych i zmianowych
  - Resetowanie hasła pracownika
  - Aktywacja i dezaktywacja konta (`is_active`)
- **Giełda zmian**: Podgląd ofert oddania zmiany, sugerowane zastępstwa na podstawie dostępności i uprawnień, zatwierdzanie transferu zmiany.
- **Wnioski urlopowe**: Przeglądanie, zatwierdzanie i odrzucanie wniosków pracowników wraz z podglądem w kalendarzu urlopowym.

---

## 3. Panel Pracownika

Dolny pasek nawigacyjny pracownika zawiera zakładki:

| Zakładka | Opis |
|----------|------|
| **Mój Grafik** | Opublikowane zmiany, widok całego zespołu, oddawanie i wymiana zmian |
| **Dostępność** | Deklaracja dyspozycji tygodniowej oraz wnioski urlopowe |
| **Obecność** | Rejestracja czasu pracy (check-in / check-out) |
| **Giełda** | Przegląd ofert i przejmowanie zmian od współpracowników |

---

### 3.1 Mój Grafik

- **Widok tygodniowy**: Prezentuje Twoje godziny pracy, stanowisko oraz współpracowników na danej zmianie.
- **Przełącznik „Cała załoga"**: Umożliwia wgląd w grafik wszystkich pracowników lokalu.
- **Oddanie zmiany na giełdę**: Kliknij swoją zmianę -> „Oddaj zmianę”. Zmiana trafi na giełdę, gdzie inny uprawniony pracownik może ją przejąć.
- **Bezpośrednia wymiana zmian (Direct Swap)**: W widoku grafiku zespołu możesz zaproponować bezpośrednią wymianę zmiany współpracownikowi o tym samym stanowisku. Informacja o chęci wymiany pojawia się priorytetowo na ekranie głównym (Home) u Ciebie, u wskazanego pracownika oraz u Managera lokalu.
- **Google Calendar**: W menu profilu możesz połączyć konto z Kalendarzem Google. Zmiany będą synchronizowane automatycznie w trybie offline.

---

### 3.2 Dostępność

#### Deklaracja Dyspozycji
1. Przejdź do wybranego tygodnia za pomocą strzałek.
2. Na liście widoczne są wyłącznie zmiany przypisane do Twoich ról.
3. Kliknij komórkę, aby wybrać stan:
   - **Dostępny (zielony)**: Mogę pracować na tej zmianie.
   - **Niedostępny (czerwony)**: Nie mogę pracować na tej zmianie.
4. Kliknij **„Zapisz"**.

> **Ważne**: Brak złożenia dyspozycji na dany tydzień skutkuje nieprzypisaniem do żadnej zmiany przez algorytm.

#### Wnioski Urlopowe
1. W podsekcji „Wnioski urlopowe” kliknij **„Nowy wniosek"**.
2. Wskaż datę początkową, datę końcową oraz opcjonalny powód.
3. Po wysłaniu wniosek otrzymuje status `PENDING`. Po decyzji Managera otrzymasz powiadomienie Push z informacją o zatwierdzeniu (`APPROVED`) lub odrzuceniu (`REJECTED`).

---

### 3.3 Obecność

1. Wybierz datę (domyślnie bieżąca).
2. Wprowadź godzinę wejścia i wyjścia (jeśli zmiana była zaplanowana, godziny uzupełnią się automatycznie).
3. Kliknij **„Zapisz"**.
4. W przypadku włączenia w lokalu wymogu checklisty, przed zapisem wyświetli się okno weryfikacji zadań stanowiskowych. Jeśli opcja jest wyłączona, rejestracja nie wymaga potwierdzania checklisty.
5. Wpisy zgodne z grafikiem zatwierdzane są automatycznie. Wpisy poza grafikiem oczekują na potwierdzenie Managera.

---

### 3.4 Giełda Zmian

- Przeglądaj otwarte oferty oddania zmian zgłoszone przez innych pracowników.
- System automatycznie oznacza brak kolizji czasowych oraz zgodność z Twoimi uprawnieniami stanowiskowymi.
- Kliknięcie **„Przejmij"** natychmiast przenosi zmianę na Twoje konto i powiadamia Managera oraz oddającego.

---

## 4. Moduł POS / Kitchen Display System (KDS)

System obsługi sali i kuchni z obsługą pracy offline:

### 4.1 Ekran Kelnera (POS)
- Wybór strefy (np. Sala Główna, Ogródek) i numeru stolika.
- Dodawanie dań z dynamicznych kategorii menu wraz z modyfikatorami i uwagami.
- Obsługa kursów dań (przystawki, dania główne, desery).
- Przekazanie zamówienia do kuchni i monitorowanie statusu realizacji.
- Rozliczanie rachunków z obsługą płatności dzielonych (gotówka, karta, voucher, płatności mobilne).

### 4.2 Ekran Kuchni (KDS)
- Prezentacja zamówień w czasie rzeczywistym z uwzględnieniem silnika pacingu (synchronizacja czasu przygotowania dań w obrębie danego kursu).
- Zmiana stanów dań: Nowe -> W przygotowaniu -> Gotowe do wydania.
- **Działanie Offline-First**: KDS działa stabilnie nawet przy zaniku sieci Wi-Fi. Zmiany buforowane są lokalnie i synchronizowane w paczkach (batch sync) po przywróceniu połączenia z weryfikacją monotoniczności stanów (anti-ghosting).

---

## 5. System Powiadomień i Web Push

PlannerV2 dostarcza powiadomienia trzema uzupełniającymi się kanałami:

### 5.1 Powiadomienia w Aplikacji (In-App)
- Ikona dzwonka w prawym górnym rogu z licznikiem nieprzeczytanych wiadomości.
- Okno dialogowe z historią powiadomień i opcją oznaczenia jako przeczytane.

### 5.2 Powiadomienia Przeglądarkowe (Web Push)
- Działają w przeglądarkach stacjonarnych i mobilnych (Chrome, Firefox, Edge, Safari).
- W trybie pierwszoplanowym powiadomienie wyświetla się jednocześnie w przeglądarce oraz w widocznym banerze na górze ekranu.
- W trybie tła (zamknięta karta) powiadomienia odbiera Service Worker (`firebase-messaging-sw.js`), wyświetlając natywną notyfikację systemową.

### 5.3 Konfiguracja Powiadomień na Urządzeniach Apple iOS (PWA)
Aby otrzymywać powiadomienia Push na iPhone / iPad (iOS 16.4+):
1. Otwórz aplikację w przeglądarce Safari.
2. Kliknij przycisk **Udostępnij** (kwadrat ze strzałką w górę) i wybierz **„Do ekranu początkowego”** (Add to Home Screen).
3. Uruchom aplikację z ikony na ekranie początkowym (jako pełnoekranową aplikację PWA).
4. Kliknij ikonę dzwonka w prawym górnym rogu i kliknij przycisk **„Włącz powiadomienia”**.
5. W wyświetlonym oknie dialogowym systemu iOS wybierz **„Pozwól”**.

### 5.4 Rozwiązywanie Problemów z Powiadomieniami
- **Status „Powiadomienia są zablokowane”**: Przejdź do ustawień przeglądarki (ikona kłódki przy adresie strony lub Ustawienia iOS -> Planista -> Powiadomienia) i zezwól na wysyłanie powiadomień, po czym odśwież aplikację.
- **Brak powiadomień w tle na iOS**: Upewnij się, że aplikacja została zainstalowana na ekranie początkowym PWA, a wersja systemu iOS to co najmniej 16.4.

---

## 6. Konfiguracja Serwera i Pierwsze Logowanie

### 6.1 Ustawienie Adresu Serwera
1. Przy pierwszym uruchomieniu aplikacja wyświetla ekran konfiguracji.
2. Wybierz **Skanuj kod QR** (Manager wyświetla kod z poziomu ikony QR w swoim panelu) lub wprowadź adres URL serwera ręcznie.
3. Parametry zostaną zapisane w pamięci urządzenia.

### 6.2 Tworzenie Pierwszego Konta
- W środowisku wielodostępnym pierwsze konto Managera lokalu tworzy Superadmin w panelu `/#/superadmin`.
- W instalacji autonomicznej pierwsze konto tworzone jest przez endpoint `POST /auth/register` z podaniem kodu PIN (`MANAGER_REGISTRATION_PIN`).

---

## 7. Najczęstsze Pytania (FAQ)

### Dlaczego grafik nie obsadza pracowników, mimo że są dostępni?
1. Upewnij się, że pracownicy zapisali deklarację dostępności na dany tydzień.
2. Sprawdź, czy pracownicy mają przypisane role odpowiadające wymaganiom danej zmiany.
3. Sprawdź, czy w konfiguracji zdefiniowano wymagania kadrowe na ten okres.
4. Upewnij się, że dni obowiązywania zmian obejmują planowane dni pracy.

### Czy algorytm przypisze pracownika przekraczającego cel godzinowy?
Tak. Zapewnienie pełnej obsady zmian jest priorytetem wyższym niż miękkie limity godzinowe. Jeśli dostępny jest tylko pracownik przekraczający cel, solver dokona przypisania, generując odpowiednie ostrzeżenie dla Managera.

### Jak zresetować hasło pracownika?
Manager przechodzi do zakładki **Zespół**, otwiera kartę wybranego pracownika, wybiera **„Reset hasła”**, podaje nowe hasło spełniające wymogi złożoności (min. 8 znaków, 1 wielka litera, 1 cyfra) i zatwierdza operację.

---

## 8. Pomoc i Zgłaszanie Błędów

- **Panel Pomocy**: Dostępny pod ikoną znaku zapytania na górnym pasku aplikacji.
- **Zgłaszanie usterek**: W panelu pomocy wybierz **„Zgłoś błąd”**, podaj tytuł i opis problemu. Zgłoszenie zostanie automatycznie przesłane do repozytorium GitHub Issues projektu.
- **Polityka prywatności**: Link dostępny na ekranie logowania oraz w ustawieniach aplikacji.

---

## 9. Panel SuperAdmina (Multi-Tenancy)

Panel nadrzędny dostępny pod adresem `/#/superadmin` dla kont z uprawnieniem `SUPERADMIN`:

1. **Zarządzanie Lokalami (Tenants)**:
   - Dodawanie nowych restauracji (nazwa oraz unikalny identyfikator slug / Login ID).
   - Włączanie i wyłączanie dostępu do systemu dla danej restauracji.
   - Edycja parametrów lokalu.
2. **Konta Globalne**:
   - Tworzenie pierwszego konta Managera dla nowo utworzonej restauracji.
   - Wgląd w bazę użytkowników ze wszystkich restauracji.
   - Awaryjny reset haseł dla wybranych kont menedżerskich.
3. **Podgląd i Zarządzanie Logami Systemowymi**:
   - Dedykowana zakładka **„Logi systemowe”** w górnym pasku nawigacyjnym.
   - **Filtrowanie per lokal**: możliwość wyboru konkretnej restauracji z listy lub wglądu w logi globalne / wszystkie lokale.
   - **Filtrowanie po poziomie**: przełączniki poziomów `Wszystkie`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `DEBUG` z kodowaniem kolorystycznym.
   - **Wyszukiwarka fraz**: natychmiastowe filtrowanie logów po treści, nazwie loggera lub ścieżce HTTP.
   - **Tracebacki błędów**: automatyczne grupowanie i możliwość rozwijania/zwijania pełnego stack trace'a błędu 500 oraz kopiowanie do schowka.
   - **Skrót z listy lokali**: na karcie każdej restauracji w zakładce pierwszej dostępny jest przycisk **„Logi”**, który automatycznie otwiera widok logów z wybranym filtrem dla tego lokalu.
   - **Czyszczenie pliku logów**: przycisk z ikoną kosza umożliwia wyczyszczenie bieżącego pliku logów serwera.
