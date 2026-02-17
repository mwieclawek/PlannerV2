import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'bug_report_dialog.dart';

class HelpDialog extends StatelessWidget {
  const HelpDialog({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Dialog(
      insetPadding: const EdgeInsets.all(16),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 550, maxHeight: 600),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Header
            Container(
              padding: const EdgeInsets.fromLTRB(24, 20, 8, 12),
              decoration: BoxDecoration(
                color: colorScheme.primaryContainer.withOpacity(0.3),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
              ),
              child: Row(
                children: [
                  Icon(Icons.help_outline, color: colorScheme.primary),
                  const SizedBox(width: 10),
                  Text(
                    'Pomoc',
                    style: GoogleFonts.outfit(
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),

            // Content
            Flexible(
              child: ListView(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                shrinkWrap: true,
                children: [
                  _HelpSection(
                    icon: Icons.calendar_month,
                    title: 'Grafik pracy',
                    items: const [
                      'Na zakładce Home widzisz dzisiejszy grafik w widoku dziennym lub tygodniowym.',
                      'W zakładce Grafik możesz generować automatyczne grafiki i edytować je ręcznie.',
                      'Po wygenerowaniu grafik jest w trybie szkicu — zapisz zmiany przyciskiem "Zapisz".',
                    ],
                  ),
                  _HelpSection(
                    icon: Icons.event_available,
                    title: 'Dostępność',
                    items: const [
                      'Pracownicy zgłaszają dostępność na każdy dzień i zmianę.',
                      'Statusy: ✅ Preferuję, ⚪ Neutralnie, ❌ Niedostępny.',
                      'System automatycznie uwzględnia preferencje przy generowaniu.',
                    ],
                  ),
                  _HelpSection(
                    icon: Icons.swap_horiz,
                    title: 'Oddawanie zmian',
                    items: const [
                      'Pracownik może oddać swoją zmianę w zakładce "Mój grafik".',
                      'Manager widzi otwarte oddania w zakładce "Zmiany" z sugestiami zastępstw.',
                      'Manager może przydzielić zmianę innemu pracownikowi lub anulować oddanie.',
                    ],
                  ),
                  _HelpSection(
                    icon: Icons.fact_check,
                    title: 'Obecności',
                    items: const [
                      'Pracownik rejestruje wejście i wyjście w zakładce "Obecność".',
                      'Manager zatwierdza lub odrzuca wpisy obecności.',
                    ],
                  ),
                  _HelpSection(
                    icon: Icons.people,
                    title: 'Zarządzanie zespołem',
                    items: const [
                      'Konta pracowników tworzy manager w zakładce "Zespół".',
                      'Można dezaktywować użytkownika — nie będzie mógł się zalogować.',
                      'Przypisz role (stanowiska), aby pracownik pojawiał się w grafiku.',
                    ],
                  ),
                  _HelpSection(
                    icon: Icons.settings,
                    title: 'Konfiguracja',
                    items: const [
                      'Zdefiniuj role (np. Kelner, Barista) i zmiany (np. Rano 8-16).',
                      'Ustaw wymagania kadrowe — ile osób na każdym stanowisku w danym dniu.',
                    ],
                  ),
                  const SizedBox(height: 8),
                ],
              ),
            ),

            // Footer with bug report button
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 8, 24, 20),
              child: Column(
                children: [
                  const Divider(),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton.icon(
                      onPressed: () {
                        Navigator.pop(context);
                        showDialog(
                          context: context,
                          builder: (_) => const BugReportDialog(),
                        );
                      },
                      icon: const Icon(Icons.bug_report, size: 18),
                      label: const Text('Zgłoś błąd'),
                      style: OutlinedButton.styleFrom(
                        foregroundColor: colorScheme.error,
                        side: BorderSide(color: colorScheme.error.withOpacity(0.5)),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HelpSection extends StatelessWidget {
  final IconData icon;
  final String title;
  final List<String> items;

  const _HelpSection({
    required this.icon,
    required this.title,
    required this.items,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ExpansionTile(
      leading: Icon(icon, size: 20, color: theme.colorScheme.primary),
      title: Text(title, style: theme.textTheme.titleSmall?.copyWith(fontWeight: FontWeight.w600)),
      tilePadding: const EdgeInsets.symmetric(horizontal: 8),
      childrenPadding: const EdgeInsets.only(left: 52, right: 16, bottom: 12),
      children: items
          .map((item) => Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('• ', style: theme.textTheme.bodyMedium),
                    Expanded(child: Text(item, style: theme.textTheme.bodyMedium)),
                  ],
                ),
              ))
          .toList(),
    );
  }
}
