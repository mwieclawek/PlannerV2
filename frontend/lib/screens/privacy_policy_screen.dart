import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class PrivacyPolicyScreen extends StatelessWidget {
  const PrivacyPolicyScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Polityka Prywatności',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Polityka Prywatności aplikacji Planista (restoplan.pl)',
              style: GoogleFonts.outfit(
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              'Ostatnia aktualizacja: 25 luty 2026',
              style: GoogleFonts.inter(
                fontSize: 13,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 16),
            Text(
              'Niniejsza Polityka Prywatności określa zasady gromadzenia, przetwarzania i ochrony danych osobowych użytkowników aplikacji internetowej i mobilnej Planista, dostępnej pod adresem restoplan.pl.',
              style: GoogleFonts.inter(fontSize: 14),
            ),
            const SizedBox(height: 24),
            _buildSection(
              context,
              '1. Kto jest Administratorem Danych?',
              'Właścicielem aplikacji i Administratorem Danych Osobowych w zakresie danych technicznych oraz danych konta użytkownika jest twórca oprogramowania – Mateusz Więcławek (osoba fizyczna). W sprawach związanych z prywatnością i funkcjonowaniem systemu możesz skontaktować się pod adresem e-mail: kontakt@restoplan.pl.\n\nWażne zastrzeżenie (Powierzenie przetwarzania): W kontekście szczegółowych danych związanych z zatrudnieniem (np. grafik pracy, wnioski urlopowe, stawki), Administratorem Danych Osobowych jest Twój Pracodawca (np. właściciel lub menedżer lokalu). Aplikacja Planista działa w tym zakresie jedynie jako podmiot przetwarzający (procesor) na zlecenie Pracodawcy, dostarczając narzędzie do zarządzania zespołem.',
            ),
            _buildSection(
              context,
              '2. Jakie dane przetwarzamy?',
              'Podczas korzystania z aplikacji przetwarzamy następujące kategorie danych:\n\n• Dane konta: imię, nazwisko, adres e-mail, nazwa użytkownika, zaszyfrowane hasło, przypisana rola w systemie.\n\n• Dane operacyjne i pracownicze: dyspozycyjność, wnioski urlopowe, frekwencja, historia przypisanych zmian, kody PIN (dla menedżerów).\n\n• Dane techniczne: standardowe logi serwera (adres IP, rodzaj przeglądarki, czas logowania) zbierane wyłącznie w celu zapewnienia stabilności i bezpieczeństwa systemu.\n\n• Integracje z usługami zewnętrznymi: w przypadku dobrowolnej integracji z Kalendarzem Google, przetwarzamy tokeny autoryzacyjne w celu synchronizacji grafiku.',
            ),
            _buildSection(
              context,
              '3. Cel i podstawa prawna przetwarzania danych',
              'Dane są przetwarzane na podstawie niezbędności do wykonania umowy o świadczenie usług drogą elektroniczną (art. 6 ust. 1 lit. b RODO) oraz naszego prawnie uzasadnionego interesu (art. 6 ust. 1 lit. f RODO), w następujących celach:\n\n• Umożliwienie logowania, korzystania z funkcji aplikacji i zarządzania profilami pracowników.\n\n• Zapewnienie bezpieczeństwa platformy, wykrywanie nieprawidłowości oraz wsparcie techniczne.\n\n• Rozwój i optymalizacja działania aplikacji Planista.\n\nNie wykorzystujemy danych użytkowników do profilowania reklamowego ani nie sprzedajemy ich podmiotom trzecim.',
            ),
            _buildSection(
              context,
              '4. Gdzie przechowujemy dane i komu je udostępniamy?',
              'Wszystkie dane zgromadzone w aplikacji Planista są przechowywane na bezpiecznych, europejskich serwerach firmy Hetzner (Hetzner Online GmbH), z zachowaniem najwyższych standardów bezpieczeństwa.\n\nWewnątrz aplikacji dostęp do Twoich danych operacyjnych (grafik, urlopy) ma Menedżer/Administrator przestrzeni roboczej w Twoim miejscu pracy. Część danych (np. imię i godziny pracy) może być widoczna dla innych pracowników w ramach tego samego lokalu (np. w celu wymiany zmian).\n\nAplikacja Planista wykorzystuje również usługi Google API (Google Calendar API). Wykorzystanie informacji z Google API odbywa się zgodnie z Polityką danych użytkowników usług API Google, z rygorystycznym przestrzeganiem zasady ograniczonego użycia (Limited Use).',
            ),
            _buildSection(
              context,
              '5. Czas przechowywania danych i prawa użytkownika',
              'Dane są przechowywane przez czas posiadania aktywnego konta w systemie Planista. Masz prawo do:\n\n• Dostępu do swoich danych oraz ich sprostowania.\n\n• Całkowitego usunięcia konta i danych z systemu (wniosek taki możesz złożyć do swojego Pracodawcy lub bezpośrednio do nas).\n\n• Ograniczenia przetwarzania lub przeniesienia danych.\n\n• Cofnięcia zgody na integracje zewnętrze (np. odłączenie Google Calendar w ustawieniach).',
            ),
            _buildSection(
              context,
              '6. Świadczenie usług i odpowiedzialność',
              'Aplikacja Planista znajduje się w fazie ciągłego rozwoju. Oprogramowanie na obecnym etapie udostępniane jest w modelu "tak jak jest" (as is). Twórca aplikacji dokłada wszelkich starań, aby system funkcjonował bezawaryjnie i bezpiecznie, jednak wyłącza swoją odpowiedzialność odszkodowawczą za ewentualne przerwy w dostępie do usługi czy błędy w synchronizacji danych, w maksymalnym zakresie dopuszczalnym przez obowiązujące prawo.',
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                'Niniejsza polityka prywatności jest dokumentem informacyjnym i może być aktualizowana. O wszelkich zmianach użytkownicy zostaną poinformowani w aplikacji.',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.grey.shade700,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildSection(BuildContext context, String title, String body) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: GoogleFonts.outfit(
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(body, style: GoogleFonts.inter(fontSize: 14, height: 1.6)),
        ],
      ),
    );
  }
}
