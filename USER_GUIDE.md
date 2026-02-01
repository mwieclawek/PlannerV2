# Podręcznik Użytkownika

## Dla Managerów

### Logowanie
1. Otwórz aplikację (http://127.0.0.1:5000)
2. Podaj email i hasło
3. Kliknij "Zaloguj"

### Panel Ustawień

#### Role
- Kliknij "Dodaj rolę"
- Podaj nazwę (np. Barista) i kolor
- Role można edytować (ikona ołówka) i usuwać (ikona kosza)

#### Zmiany
- Kliknij "Dodaj zmianę"
- Podaj nazwę i godziny (np. 08:00 - 16:00)
- **Uwaga**: Godziny muszą być unikalne!

#### Restauracja
- Podaj nazwę lokalu, adres i godziny otwarcia
- Kliknij "Zapisz"

### Panel Zespołu
- Widoczna lista wszystkich pracowników
- Kliknij pracownika aby przypisać/edytować role
- Reset hasła dostępny dla managera

### Panel Grafiku
1. Wybierz tydzień (strzałki ◀ ▶)
2. Kliknij **"Generuj grafik"** - system automatycznie przypisze pracowników
3. Edytuj ręcznie jeśli potrzeba:
   - Kliknij komórkę aby dodać/usunąć przypisanie
   - Możesz dodać wielu pracowników do jednej zmiany
4. **"Zapisz zmiany"** - zapisuje edycje do bazy

> ⚠️ Jeśli wygenerujesz grafik ponownie, ręczne zmiany zostaną utracone!

---

## Dla Pracowników

### Logowanie
1. Otwórz aplikację
2. Podaj email i hasło (otrzymane od managera)

### Dashboard
- Widoczny grafik na bieżący tydzień
- Twoje zmiany są podświetlone

### Dostępność
1. Przejdź do zakładki "Dostępność"
2. Dla każdego dnia/zmiany wybierz:
   - ✅ **Preferuję** - chętnie pracuję
   - ⚪ **Neutralnie** - mogę pracować
   - ❌ **Niedostępny** - nie mogę
3. Kliknij "Zapisz"

---

## FAQ

**Q: Zapomniałem hasła**
A: Poproś managera o reset hasła

**Q: Grafik jest pusty po wygenerowaniu**
A: Sprawdź czy:
- Są zdefiniowane role i zmiany
- Pracownicy mają przypisane role
- Ustawiono wymagania kadrowe

**Q: Nie mogę się zarejestrować jako manager**
A: Potrzebujesz PIN-u: `1234`
