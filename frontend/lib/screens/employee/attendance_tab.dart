import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';

class AttendanceTab extends ConsumerStatefulWidget {
  const AttendanceTab({super.key});

  @override
  ConsumerState<AttendanceTab> createState() => _AttendanceTabState();
}

class _AttendanceTabState extends ConsumerState<AttendanceTab> {
  List<Map<String, dynamic>>? _attendances;
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
      final endDate = DateTime(_selectedMonth.year, _selectedMonth.month + 1, 0);
      
      final attendances = await api.getMyAttendance(startDate, endDate);
      setState(() {
        _attendances = attendances;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  void _showRegisterDialog() {
    DateTime selectedDate = DateTime.now();
    String? checkIn;
    String? checkOut;
    bool isScheduled = false;
    String? shiftName;
    bool isLoadingDefaults = true;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) {
          // Load defaults when date changes
          void loadDefaults() async {
            setDialogState(() => isLoadingDefaults = true);
            try {
              final api = ref.read(apiServiceProvider);
              final defaults = await api.getAttendanceDefaults(selectedDate);
              setDialogState(() {
                isScheduled = defaults['scheduled'] ?? false;
                checkIn = defaults['check_in'];
                checkOut = defaults['check_out'];
                shiftName = defaults['shift_name'];
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
              width: 300,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Date Picker
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.calendar_today),
                    title: Text(DateFormat('d MMMM yyyy', 'pl_PL').format(selectedDate)),
                    trailing: const Icon(Icons.arrow_drop_down),
                    onTap: () async {
                      final picked = await showDatePicker(
                        context: context,
                        initialDate: selectedDate,
                        firstDate: DateTime.now().subtract(const Duration(days: 30)),
                        lastDate: DateTime.now(),
                      );
                      if (picked != null) {
                        setDialogState(() {
                          selectedDate = picked;
                          isLoadingDefaults = true;
                        });
                      }
                    },
                  ),
                  
                  const SizedBox(height: 16),
                  
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
                            Icon(Icons.check_circle, color: Colors.green.shade700),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Planowana zmiana: $shiftName',
                                style: TextStyle(color: Colors.green.shade700),
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
                          border: Border.all(color: Colors.orange.shade200),
                        ),
                        child: Row(
                          children: [
                            Icon(Icons.warning, color: Colors.orange.shade700),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                'Nieplanowana obecność - wymaga zatwierdzenia managera',
                                style: TextStyle(color: Colors.orange.shade700, fontSize: 12),
                              ),
                            ),
                          ],
                        ),
                      ),
                    
                    const SizedBox(height: 16),
                    
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
                            controller: TextEditingController(text: checkIn ?? ''),
                            onChanged: (v) => checkIn = v,
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
                            controller: TextEditingController(text: checkOut ?? ''),
                            onChanged: (v) => checkOut = v,
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: isLoadingDefaults ? null : () async {
                  Navigator.pop(context);
                  await _registerAttendance(selectedDate, checkIn!, checkOut!);
                },
                child: const Text('Zarejestruj'),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _registerAttendance(DateTime date, String checkIn, String checkOut) async {
    try {
      final api = ref.read(apiServiceProvider);
      final result = await api.registerAttendance(date, checkIn, checkOut);
      
      if (mounted) {
        final requiresApproval = result['requires_approval'] == true;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(requiresApproval 
              ? 'Obecność zarejestrowana - oczekuje na zatwierdzenie'
              : 'Obecność zarejestrowana'),
            backgroundColor: requiresApproval ? Colors.orange : Colors.green,
          ),
        );
        _loadAttendances();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
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
              color: Theme.of(context).colorScheme.primaryContainer.withOpacity(0.3),
              border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: () {
                    setState(() {
                      _selectedMonth = DateTime(_selectedMonth.year, _selectedMonth.month - 1);
                    });
                    _loadAttendances();
                  },
                ),
                Text(
                  DateFormat('MMMM yyyy', 'pl_PL').format(_selectedMonth),
                  style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: () {
                    setState(() {
                      _selectedMonth = DateTime(_selectedMonth.year, _selectedMonth.month + 1);
                    });
                    _loadAttendances();
                  },
                ),
              ],
            ),
          ),
          
          // Content
          Expanded(
            child: _buildContent(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showRegisterDialog,
        icon: const Icon(Icons.add),
        label: const Text('Zarejestruj'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Theme.of(context).colorScheme.onPrimary,
      ),
    );
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
              style: GoogleFonts.inter(fontSize: 16, color: Colors.grey.shade600),
            ),
            const SizedBox(height: 8),
            Text(
              'Użyj przycisku poniżej aby zarejestrować',
              style: GoogleFonts.inter(fontSize: 14, color: Colors.grey.shade500),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _attendances!.length,
      itemBuilder: (context, index) {
        final a = _attendances![index];
        final date = DateTime.parse(a['date']);
        final status = a['status'] as String;
        
        return Card(
          margin: const EdgeInsets.only(bottom: 12),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: _getStatusColor(status).withOpacity(0.2),
              child: Icon(
                status == 'CONFIRMED' ? Icons.check : 
                status == 'PENDING' ? Icons.hourglass_empty : Icons.close,
                color: _getStatusColor(status),
              ),
            ),
            title: Text(
              DateFormat('EEEE, d MMMM', 'pl_PL').format(date),
              style: GoogleFonts.inter(fontWeight: FontWeight.w600),
            ),
            subtitle: Text('${a['check_in']} - ${a['check_out']}'),
            trailing: Chip(
              label: Text(
                _getStatusLabel(status),
                style: TextStyle(color: _getStatusColor(status), fontSize: 12),
              ),
              backgroundColor: _getStatusColor(status).withOpacity(0.1),
            ),
          ),
        );
      },
    );
  }
}
