import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';

class EmployeeDetailDialog extends ConsumerStatefulWidget {
  final TeamMember user;
  final VoidCallback onEdit;
  final VoidCallback onEditRoles;
  final VoidCallback onResetPassword;
  final VoidCallback? onEditName;

  const EmployeeDetailDialog({
    super.key,
    required this.user,
    required this.onEdit,
    required this.onEditRoles,
    required this.onResetPassword,
    this.onEditName,
  });

  @override
  ConsumerState<EmployeeDetailDialog> createState() =>
      _EmployeeDetailDialogState();
}

class _EmployeeDetailDialogState extends ConsumerState<EmployeeDetailDialog> {
  late int _selectedMonth;
  late int _selectedYear;
  late Future<UserStats> _statsFuture;

  static const List<String> _monthNames = [
    'Styczeń',
    'Luty',
    'Marzec',
    'Kwiecień',
    'Maj',
    'Czerwiec',
    'Lipiec',
    'Sierpień',
    'Wrzesień',
    'Październik',
    'Listopad',
    'Grudzień',
  ];

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _selectedMonth = now.month;
    _selectedYear = now.year;
    _statsFuture = _fetchStats();
  }

  Future<UserStats> _fetchStats() {
    return ref.read(apiServiceProvider).getUserStats(
      widget.user.id,
      month: _selectedMonth,
      year: _selectedYear,
    );
  }

  void _changeMonth(int delta) {
    setState(() {
      var m = _selectedMonth + delta;
      var y = _selectedYear;
      while (m <= 0) {
        m += 12;
        y -= 1;
      }
      while (m > 12) {
        m -= 12;
        y += 1;
      }
      _selectedMonth = m;
      _selectedYear = y;
      _statsFuture = _fetchStats();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Container(
        width: 500,
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.8,
        ),
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildHeader(),
            const Divider(height: 32),
            Expanded(
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildInfoSection(),
                    const SizedBox(height: 24),
                    _buildStatsSection(),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),
            _buildActions(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        CircleAvatar(
          radius: 32,
          backgroundColor: Theme.of(context).colorScheme.primaryContainer,
          child: Text(
            widget.user.fullName.isNotEmpty
                ? widget.user.fullName[0].toUpperCase()
                : '?',
            style: GoogleFonts.inter(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                widget.user.fullName,
                style: GoogleFonts.inter(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '@${widget.user.username}',
                style: GoogleFonts.inter(
                  color: Colors.grey.shade600,
                  fontSize: 14,
                ),
              ),
              if (widget.user.email != null) ...[
                const SizedBox(height: 2),
                Text(
                  widget.user.email!,
                  style: GoogleFonts.inter(
                    color: Colors.grey.shade600,
                    fontSize: 14,
                  ),
                ),
              ],
            ],
          ),
        ),
        IconButton(
          onPressed: () => Navigator.pop(context),
          icon: const Icon(Icons.close),
        ),
      ],
    );
  }

  Widget _buildInfoSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Informacje',
          style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        _buildInfoRow(
          Icons.person,
          'Imię i nazwisko',
          widget.user.fullName,
          onTap: widget.onEditName,
        ),
        const SizedBox(height: 8),
        _buildInfoRow(
          Icons.work_outline,
          'Role',
          'Kliknij edytuj, aby zarządzać',
          onTap: widget.onEditRoles,
        ),
        const SizedBox(height: 8),
        _buildInfoRow(
          Icons.payments_outlined,
          'Stawka godzinowa',
          widget.user.hourlyRate != null
              ? '${widget.user.hourlyRate!.toStringAsFixed(2)} PLN/h'
              : 'Nie ustawiono (kliknij, aby dodać)',
          onTap: () {
            Navigator.pop(context);
            widget.onEdit();
          },
        ),
        if (widget.user.targetHoursPerMonth != null ||
            widget.user.targetShiftsPerMonth != null) ...[
          const SizedBox(height: 8),
          _buildInfoRow(
            Icons.track_changes,
            'Cele miesięczne',
            '${widget.user.targetHoursPerMonth ?? "-"}h / ${widget.user.targetShiftsPerMonth ?? "-"} zmian',
            onTap: () {
              Navigator.pop(context);
              widget.onEdit();
            },
          ),
        ],
        const SizedBox(height: 8),
        _buildInfoRow(
          Icons.lock_reset,
          'Hasło',
          'Resetuj hasło',
          onTap: widget.onResetPassword,
        ),
      ],
    );
  }

  Widget _buildInfoRow(
    IconData icon,
    String label,
    String value, {
    VoidCallback? onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          children: [
            Icon(icon, size: 20, color: Colors.grey.shade600),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 14,
                      color:
                          onTap != null
                              ? Theme.of(context).colorScheme.primary
                              : Colors.black87,
                      fontWeight:
                          onTap != null ? FontWeight.w500 : FontWeight.normal,
                    ),
                  ),
                ],
              ),
            ),
            if (onTap != null)
              Icon(Icons.chevron_right, size: 16, color: Colors.grey.shade400),
          ],
        ),
      ),
    );
  }

  Widget _buildStatsSection() {
    final monthLabel = '${_monthNames[_selectedMonth - 1]} $_selectedYear';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(
              'Statystyki',
              style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const Spacer(),
            IconButton(
              icon: const Icon(Icons.chevron_left, size: 20),
              tooltip: 'Poprzedni miesiąc',
              onPressed: () => _changeMonth(-1),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
            ),
            Text(
              monthLabel,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
            IconButton(
              icon: const Icon(Icons.chevron_right, size: 20),
              tooltip: 'Następny miesiąc',
              onPressed: () => _changeMonth(1),
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
            ),
          ],
        ),
        const SizedBox(height: 12),
        FutureBuilder<UserStats>(
          future: _statsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Text(
                'Błąd pobierania statystyk: ${snapshot.error}',
                style: const TextStyle(color: Colors.red),
              );
            }
            if (!snapshot.hasData) {
              return const Text('Brak danych');
            }

            final stats = snapshot.data!;
            final targetSuffix =
                stats.targetHoursPerMonth != null
                    ? ' / ${stats.targetHoursPerMonth}h'
                    : '';
            return Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: _buildStatCard(
                        'Przepracowane ($monthLabel)',
                        '${stats.selectedMonthWorkedHours.toStringAsFixed(1)}h (${stats.selectedMonthShifts} zm.)',
                        Icons.event_available,
                        Colors.green.shade50,
                        Colors.green.shade700,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildStatCard(
                        'Zaplanowane ($monthLabel)',
                        '${stats.selectedMonthPlannedHours.toStringAsFixed(1)}h$targetSuffix',
                        Icons.calendar_month,
                        Colors.blue.shade50,
                        Colors.blue.shade700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildStatCard(
                        'Ukończone zmiany (łącznie)',
                        stats.totalShiftsCompleted.toString(),
                        Icons.check_circle_outline,
                        Theme.of(context).colorScheme.primaryContainer,
                        Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildStatCard(
                        'Przepracowane (łącznie)',
                        '${stats.totalHoursWorked.toStringAsFixed(1)}h',
                        Icons.access_time,
                        Theme.of(context).colorScheme.secondaryContainer,
                        Theme.of(context).colorScheme.secondary,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  'Ostatnie 6 miesięcy',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: Colors.grey.shade700,
                  ),
                ),
                const SizedBox(height: 8),
                Container(
                  height: 150,
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey.shade200),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children:
                        stats.monthlyShifts.reversed.map((m) {
                          final count = (m['count'] as num?)?.toInt() ?? 0;
                          final hrs = (m['hours'] as num?)?.toDouble() ?? 0.0;
                          return Column(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              Text(
                                '${hrs.toStringAsFixed(0)}h',
                                style: const TextStyle(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 11,
                                ),
                              ),
                              const SizedBox(height: 4),
                              Container(
                                width: 20,
                                height:
                                    (count * 5)
                                        .clamp(4, 100)
                                        .toDouble(), // Scale factor
                                decoration: BoxDecoration(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.primary.withOpacity(0.7),
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                (m['month'] as String).substring(
                                  5,
                                ), // Show MM from YYYY-MM
                                style: TextStyle(
                                  fontSize: 10,
                                  color: Colors.grey.shade600,
                                ),
                              ),
                            ],
                          );
                        }).toList(),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildStatCard(
    String title,
    String value,
    IconData icon,
    Color bg,
    Color fg,
  ) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bg.withOpacity(0.3),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: bg),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: fg, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: fg,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: GoogleFonts.inter(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              color: Colors.black87,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActions() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zamknij'),
        ),
        const SizedBox(width: 8),
        ElevatedButton.icon(
          onPressed: widget.onEdit,
          icon: const Icon(Icons.edit),
          label: const Text('Edytuj dane'),
          style: ElevatedButton.styleFrom(
            backgroundColor: Theme.of(context).colorScheme.primary,
            foregroundColor: Theme.of(context).colorScheme.onPrimary,
          ),
        ),
      ],
    );
  }
}
