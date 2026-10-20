import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class AttendanceTab extends ConsumerStatefulWidget {
  const AttendanceTab({super.key});

  @override
  ConsumerState<AttendanceTab> createState() => _AttendanceTabState();
}

class _AttendanceTabState extends ConsumerState<AttendanceTab> {
  List<Map<String, dynamic>>? _attendances;
  EmployeeMonthlyEarnings? _earnings;
  bool _isLoading = true;
  String? _error;

  DateTime _selectedMonth = DateTime.now();

  @override
  void initState() {
    super.initState();
    _loadAttendances();
  }

  Future<void> _loadAttendances() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(apiServiceProvider);
      final startDate = DateTime(_selectedMonth.year, _selectedMonth.month, 1);
      final endDate = DateTime(
        _selectedMonth.year,
        _selectedMonth.month + 1,
        0,
      );

      final attendances = await api.getMyAttendance(startDate, endDate);
      EmployeeMonthlyEarnings? earnings;
      try {
        earnings = await api.getMyMonthlyEarnings(
          _selectedMonth.year,
          _selectedMonth.month,
        );
      } catch (_) {}

      setState(() {
        _attendances = attendances;
        _earnings = earnings;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _showRegisterDialog({
    DateTime? initialDate,
    bool initialAbsent = false,
  }) {
    DateTime selectedDate = initialDate ?? DateTime.now();
    final checkInCtrl = TextEditingController();
    final checkOutCtrl = TextEditingController();
    final absenceReasonCtrl = TextEditingController();
    bool isScheduled = false;
    bool isAbsent = initialAbsent;
    String? shiftName;
    bool isLoadingDefaults = true;
    String? validationError;

    showDialog(
      context: context,
      builder:
          (context) => StatefulBuilder(
            builder: (context, setDialogState) {
              // Load defaults when date changes
              void loadDefaults() async {
                setDialogState(() => isLoadingDefaults = true);
                try {
                  final api = ref.read(apiServiceProvider);
                  final defaults = await api.getAttendanceDefaults(
                    selectedDate,
                  );
                  setDialogState(() {
                    isScheduled = defaults['scheduled'] ?? false;
                    checkInCtrl.text =
                        (defaults['check_in'] ?? '08:00').toString();
                    checkOutCtrl.text =
                        (defaults['check_out'] ?? '16:00').toString();
                    shiftName = defaults['shift_name']?.toString();
                    if (!isScheduled) {
                      isAbsent = false;
                    }
                    isLoadingDefaults = false;
                  });
                } catch (e) {
                  setDialogState(() => isLoadingDefaults = false);
                }
              }

              if (isLoadingDefaults) {
                loadDefaults();
              }

              return AlertDialog(
                title: const Text('Zarejestruj obecność'),
                content: SizedBox(
                  width: 340,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Date Picker (Polish locale, Monday start)
                        ListTile(
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(Icons.calendar_today),
                          title: Text(
                            DateFormat(
                              'EEEE, d MMMM yyyy',
                              'pl_PL',
                            ).format(selectedDate),
                          ),
                          trailing: const Icon(Icons.arrow_drop_down),
                          onTap: () async {
                            final picked = await showDatePicker(
                              context: context,
                              locale: const Locale('pl', 'PL'),
                              initialDate: selectedDate,
                              firstDate: DateTime.now().subtract(
                                const Duration(days: 60),
                              ),
                              lastDate: DateTime.now(),
                            );
                            if (picked != null) {
                              setDialogState(() {
                                selectedDate = picked;
                                validationError = null;
                                isLoadingDefaults = true;
                              });
                            }
                          },
                        ),

                        const SizedBox(height: 12),

                        if (isLoadingDefaults)
                          const Center(child: CircularProgressIndicator())
                        else ...[
                          // Schedule info
                          if (isScheduled)
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.green.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(color: Colors.green.shade200),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.check_circle,
                                    color: Colors.green.shade700,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Planowana zmiana: $shiftName',
                                      style: TextStyle(
                                        color: Colors.green.shade700,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            )
                          else
                            Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                color: Colors.orange.shade50,
                                borderRadius: BorderRadius.circular(8),
                                border: Border.all(
                                  color: Colors.orange.shade200,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.warning,
                                    color: Colors.orange.shade700,
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Text(
                                      'Nieplanowana obecność - wymaga zatwierdzenia managera',
                                      style: TextStyle(
                                        color: Colors.orange.shade700,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),

                          if (isScheduled) ...[
                            const SizedBox(height: 12),
                            CheckboxListTile(
                              contentPadding: EdgeInsets.zero,
                              controlAffinity: ListTileControlAffinity.leading,
                              value: isAbsent,
                              title: const Text(
                                'Nieobecny (nie przyszedłem na zmianę)',
                                style: TextStyle(fontSize: 14),
                              ),
                              onChanged: (v) {
                                setDialogState(() {
                                  isAbsent = v ?? false;
                                  validationError = null;
                                });
                              },
                            ),
                          ],

                          const SizedBox(height: 12),

                          if (isAbsent) ...[
                            TextField(
                              controller: absenceReasonCtrl,
                              maxLines: 2,
                              decoration: InputDecoration(
                                labelText: 'Powód nieobecności *',
                                hintText: 'np. Choroba, nagła sytuacja losowa',
                                prefixIcon: const Icon(Icons.info_outline),
                                border: const OutlineInputBorder(),
                                errorText: validationError,
                              ),
                            ),
                          ] else ...[
                            // Time inputs
                            Row(
                              children: [
                                Expanded(
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      labelText: 'Przyjście',
                                      prefixIcon: Icon(Icons.login),
                                      border: OutlineInputBorder(),
                                    ),
                                    controller: checkInCtrl,
                                  ),
                                ),
                                const SizedBox(width: 16),
                                Expanded(
                                  child: TextField(
                                    decoration: const InputDecoration(
                                      labelText: 'Wyjście',
                                      prefixIcon: Icon(Icons.logout),
                                      border: OutlineInputBorder(),
                                    ),
                                    controller: checkOutCtrl,
                                  ),
                                ),
                              ],
                            ),
                            if (validationError != null) ...[
                              const SizedBox(height: 8),
                              Text(
                                validationError!,
                                style: const TextStyle(
                                  color: Colors.red,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ],
                        ],
                      ],
                    ),
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Anuluj'),
                  ),
                  FilledButton(
                    onPressed:
                        isLoadingDefaults
                            ? null
                            : () async {
                              if (isAbsent) {
                                final reason = absenceReasonCtrl.text.trim();
                                if (reason.isEmpty) {
                                  setDialogState(() {
                                    validationError =
                                        'Podaj powód nieobecności';
                                  });
                                  return;
                                }
                                Navigator.pop(context);
                                await _registerAttendance(
                                  selectedDate,
                                  '00:00',
                                  '00:00',
                                  isAbsent: true,
                                  absenceReason: reason,
                                );
                              } else {
                                final inVal = checkInCtrl.text.trim();
                                final outVal = checkOutCtrl.text.trim();
                                if (inVal.isEmpty || outVal.isEmpty) {
                                  setDialogState(() {
                                    validationError =
                                        'Podaj godziny przyjścia i wyjścia';
                                  });
                                  return;
                                }
                                Navigator.pop(context);
                                await _registerAttendance(
                                  selectedDate,
                                  inVal,
                                  outVal,
                                );
                              }
                            },
                    child: Text(isAbsent ? 'Zgłoś nieobecność' : 'Zarejestruj'),
                  ),
                ],
              );
            },
          ),
    );
  }

  Future<void> _registerAttendance(
    DateTime date,
    String checkIn,
    String checkOut, {
    bool isAbsent = false,
    String? absenceReason,
  }) async {
    try {
      final api = ref.read(apiServiceProvider);
      String? skipReason;

      // Validate mandatory checklists before clock-out only when actually present
      if (!isAbsent) {
        try {
          final validation = await api.validateClockoutChecklists(date: date);
          if (!validation.allMandatoryCompleted && mounted) {
            final reasonCtrl = TextEditingController();
            final proceed = await showDialog<bool>(
              context: context,
              builder:
                  (ctx) => AlertDialog(
                    title: const Row(
                      children: [
                        Icon(
                          Icons.warning_amber_rounded,
                          color: Colors.orange,
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: Text('Niewykonane zadania z checklisty'),
                        ),
                      ],
                    ),
                    content: SizedBox(
                      width: 360,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Przed rejestracją wyjścia poniższe zadania obowiązkowe nie zostały odhaczone:',
                          ),
                          const SizedBox(height: 8),
                          ...validation.missingItems.map(
                            (item) => Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Row(
                                children: [
                                  const Icon(
                                    Icons.error_outline,
                                    size: 16,
                                    color: Colors.red,
                                  ),
                                  const SizedBox(width: 6),
                                  Expanded(
                                    child: Text(
                                      (item['title'] ?? item['label'] ?? '')
                                          .toString(),
                                      style: const TextStyle(fontSize: 13),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: reasonCtrl,
                            decoration: const InputDecoration(
                              labelText:
                                  'Powód pominięcia zadań obowiązkowych *',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ],
                      ),
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(ctx, false),
                        child: const Text('Wróć do checklisty'),
                      ),
                      FilledButton(
                        onPressed: () {
                          if (reasonCtrl.text.trim().isEmpty) return;
                          skipReason = reasonCtrl.text.trim();
                          Navigator.pop(ctx, true);
                        },
                        child: const Text('Zarejestruj mimo to'),
                      ),
                    ],
                  ),
            );
            if (proceed != true) return;
          }
        } catch (_) {}
      }

      final result = await api.registerAttendance(
        date,
        checkIn,
        checkOut,
        checklistSkipReason: skipReason,
        isAbsent: isAbsent,
        absenceReason: absenceReason,
      );

      if (mounted) {
        final requiresApproval = result['requires_approval'] == true;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              isAbsent
                  ? 'Zgłoszono nieobecność na zmianie'
                  : (requiresApproval
                      ? 'Obecność zarejestrowana - oczekuje na zatwierdzenie'
                      : 'Obecność zarejestrowana'),
            ),
            backgroundColor: requiresApproval ? Colors.orange : Colors.green,
          ),
        );
        _loadAttendances();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Błąd: $e')));
      }
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'CONFIRMED':
        return Colors.green;
      case 'PENDING':
        return Colors.orange;
      case 'REJECTED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'CONFIRMED':
        return 'Potwierdzone';
      case 'PENDING':
        return 'Oczekuje';
      case 'REJECTED':
        return 'Odrzucone';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Month selector
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(
                context,
              ).colorScheme.primaryContainer.withValues(alpha: 0.3),
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () {
                    setState(() {
                      _selectedMonth = DateTime(
                        _selectedMonth.year,
                        _selectedMonth.month - 1,
                      );
                    });
                    _loadAttendances();
                  },
                ),
                Text(
                  DateFormat('MMMM yyyy', 'pl_PL').format(_selectedMonth),
                  style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () {
                    setState(() {
                      _selectedMonth = DateTime(
                        _selectedMonth.year,
                        _selectedMonth.month + 1,
                      );
                    });
                    _loadAttendances();
                  },
                ),
              ],
            ),
          ),

          // Content
          Expanded(child: _buildContent()),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showRegisterDialog(),
        icon: const Icon(Icons.add),
        label: const Text('Zarejestruj'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
      ),
    );
  }

  double _calcHours(String checkIn, String checkOut) {
    try {
      final inParts = checkIn.split(':');
      final outParts = checkOut.split(':');
      final inMinutes = int.parse(inParts[0]) * 60 + int.parse(inParts[1]);
      var outMinutes = int.parse(outParts[0]) * 60 + int.parse(outParts[1]);
      if (outMinutes < inMinutes) outMinutes += 24 * 60; // overnight shift
      return (outMinutes - inMinutes) / 60.0;
    } catch (_) {
      return 0.0;
    }
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(child: Text('Błąd: $_error'));
    }

    if (_attendances == null || _attendances!.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.access_time, size: 64, color: Colors.grey.shade400),
            const SizedBox(height: 16),
            Text(
              'Brak zarejestrowanej obecności',
              style: GoogleFonts.inter(
                fontSize: 16,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Użyj przycisku poniżej aby zarejestrować',
              style: GoogleFonts.inter(
                fontSize: 14,
                color: Colors.grey.shade500,
              ),
            ),
          ],
        ),
      );
    }

    // Compute summary stats
    double totalHours = 0;
    int confirmedCount = 0;
    int pendingCount = 0;
    for (final a in _attendances!) {
      final absent = a['is_absent'] == true;
      if (a['status'] == 'CONFIRMED') {
        confirmedCount++;
        if (!absent) {
          totalHours += _calcHours(
            a['check_in'] as String,
            a['check_out'] as String,
          );
        }
      } else if (a['status'] == 'PENDING') {
        pendingCount++;
      }
    }

    final colorScheme = Theme.of(context).colorScheme;
    final tipPoolEnabled =
        ref.watch(tipPoolEnabledProvider).valueOrNull ?? true;

    return Column(
      children: [
        // Summary bar
        Container(
          margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: BoxDecoration(
            color: colorScheme.primaryContainer.withValues(alpha: 0.4),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _summaryChip(
                Icons.schedule,
                '${totalHours.toStringAsFixed(1)} godz.',
                'Przepracowane',
                colorScheme.primary,
              ),
              Container(
                width: 1,
                height: 32,
                color: colorScheme.outlineVariant,
              ),
              _summaryChip(
                Icons.check_circle_outline,
                '$confirmedCount',
                'Potwierdzone',
                Colors.green,
              ),
              if (pendingCount > 0) ...[
                Container(
                  width: 1,
                  height: 32,
                  color: colorScheme.outlineVariant,
                ),
                _summaryChip(
                  Icons.hourglass_empty,
                  '$pendingCount',
                  'Oczekuje',
                  Colors.orange,
                ),
              ],
            ],
          ),
        ),
        if (_earnings != null)
          Container(
            margin: const EdgeInsets.fromLTRB(16, 10, 16, 0),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.teal.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.teal.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Moje zarobki w tym miesiącu',
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Colors.teal.shade900,
                      ),
                    ),
                    Text(
                      tipPoolEnabled
                          ? 'Baza: ${_earnings!.basePay.toStringAsFixed(2)} PLN • Napiwki: ${_earnings!.allocatedTips.toStringAsFixed(2)} PLN'
                          : 'Stawka: ${_earnings!.hourlyRate.toStringAsFixed(2)} PLN/h • Wynagrodzenie bazowe',
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey.shade700,
                      ),
                    ),
                  ],
                ),
                Text(
                  '${(tipPoolEnabled ? _earnings!.totalPay : _earnings!.basePay).toStringAsFixed(2)} PLN',
                  style: GoogleFonts.outfit(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.teal.shade800,
                  ),
                ),
              ],
            ),
          ),
        // Attendance list
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: _attendances!.length,
            itemBuilder: (context, index) {
              final a = _attendances![index];
              final date = DateTime.parse(a['date']);
              final status = a['status'] as String;
              final isAbsent = a['is_absent'] == true;
              final absenceReason = a['absence_reason']?.toString() ?? '';

              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor:
                        isAbsent
                            ? Colors.deepOrange.withValues(alpha: 0.15)
                            : _getStatusColor(status).withValues(alpha: 0.2),
                    child: Icon(
                      isAbsent
                          ? Icons.person_off_outlined
                          : status == 'CONFIRMED'
                          ? Icons.check
                          : status == 'PENDING'
                          ? Icons.hourglass_empty
                          : Icons.close,
                      color:
                          isAbsent
                              ? Colors.deepOrange
                              : _getStatusColor(status),
                    ),
                  ),
                  title: Text(
                    DateFormat('EEEE, d MMMM', 'pl_PL').format(date),
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                  ),
                  subtitle:
                      isAbsent
                          ? Text(
                            absenceReason.isNotEmpty
                                ? 'Nieobecny — Powód: $absenceReason'
                                : 'Nieobecny na zmianie',
                            style: TextStyle(
                              color: Colors.deepOrange.shade800,
                              fontWeight: FontWeight.w500,
                            ),
                          )
                          : Text('${a['check_in']} - ${a['check_out']}'),
                  trailing: Chip(
                    label: Text(
                      isAbsent ? 'Nieobecny' : _getStatusLabel(status),
                      style: TextStyle(
                        color:
                            isAbsent
                                ? Colors.deepOrange.shade800
                                : _getStatusColor(status),
                        fontSize: 12,
                      ),
                    ),
                    backgroundColor:
                        isAbsent
                            ? Colors.deepOrange.withValues(alpha: 0.1)
                            : _getStatusColor(status).withValues(alpha: 0.1),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _summaryChip(IconData icon, String value, String label, Color color) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 18, color: color),
        const SizedBox(height: 2),
        Text(
          value,
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.bold,
            color: color,
          ),
        ),
        Text(
          label,
          style: GoogleFonts.inter(fontSize: 10, color: Colors.grey.shade600),
        ),
      ],
    );
  }
}
