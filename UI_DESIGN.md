# Specyfikacja UI

## Paleta Kolorów

| Nazwa | Hex | Użycie |
|-------|-----|--------|
| Primary | `#4F46E5` (Indigo) | Przyciski, akcenty |
| Success | `#22C55E` | Potwierdzenia |
| Warning | `#F59E0B` | Ostrzeżenia |
| Error | `#EF4444` | Błędy |
| Background | `#F8FAFC` | Tło |
| Surface | `#FFFFFF` | Karty |

## Typografia

- **Nagłówki**: Google Fonts - Outfit
- **Treść**: Google Fonts - Inter
- **Rozmiary**: 12/14/16/20/24/32px

## Komponenty

### Przyciski
- `ElevatedButton` - główne akcje (Zapisz, Generuj)
- `OutlinedButton` - akcje drugorzędne (Anuluj)
- `IconButton` - akcje inline (Edytuj, Usuń)

### Formularze
- `TextField` z `OutlineInputBorder`
- Walidacja inline z `errorText`
- `DropdownButtonFormField` dla select

### Karty
- `Card` z `elevation: 2`
- Padding: 16px
- Border radius: 12px

## Ekrany

### Login (`/login`)
- Logo aplikacji
- Pola: Email, Hasło
- Przyciski: Zaloguj, Zarejestruj

### Manager Dashboard (`/manager`)
- Bottom Navigation: Grafik | Zespół | Ustawienia
- AppBar z nazwą użytkownika

### Scheduler Tab
- Tydzień picker (← Tydzień →)
- Grid: Dni × Zmiany
- Komórki z chipami pracowników
- FAB: Generuj / Zapisz

### Setup Tab
- Sekcja: Restauracja (nazwa, adres, godziny)
- Sekcja: Role (lista + formularz)
- Sekcja: Zmiany (lista + formularz)

### Employee Dashboard (`/employee`)
- Prosty widok tygodnia
- Podświetlone własne zmiany
- Zakładka dostępności

## Responsywność

| Breakpoint | Layout |
|------------|--------|
| < 600px | Mobile (stack) |
| 600-1200px | Tablet (2 columns) |
| > 1200px | Desktop (sidebar + content) |

## Animacje

- Przejścia między ekranami: `PageRouteBuilder`
- Loading states: `CircularProgressIndicator`
- Snackbary: 3s auto-dismiss
