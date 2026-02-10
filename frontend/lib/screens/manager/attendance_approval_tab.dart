import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';

class AttendanceApprovalTab extends ConsumerStatefulWidget {
  const AttendanceApprovalTab({super.key});

  @override
  ConsumerState<AttendanceApprovalTab> createState() => _AttendanceApprovalTabState();
}

class _AttendanceApprovalTabState extends ConsumerState<AttendanceApprovalTab> {
  List<Map<String, dynamic>> _attendances = [];
  bool _isLoading = false;
  String? _error;
  DateTime _startDate = DateTime.now().subtract(const Duration(days: 30));
  DateTime _endDate = DateTime.now();
  String? _statusFilter; // null = all, or PENDING, CONFIRMED, REJECTED

  @override
  void initState() {
    super.initState();
    _loadAttendance();
  }

  Future<void> _loadAttendance() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(apiServiceProvider);
      final data = await api.getAllAttendance(
        _startDate,
        _endDate,
        status: _statusFilter,
      );
      setState(() {
        _attendances = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _confirmAttendance(String id) async {
    try {
      await ref.read(apiServiceProvider).confirmAttendance(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Obecność potwierdzona'), backgroundColor: Colors.green),
        );
        await _loadAttendance();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  Future<void> _rejectAttendance(String id) async {
    try {
      await ref.read(apiServiceProvider).rejectAttendance(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Obecność odrzucona'), backgroundColor: Colors.orange),
        );
        await _loadAttendance();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Obecności', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.indigo.shade700,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Filters
          Container(
            padding: const EdgeInsets.all(16),
            color: Colors.grey.shade100,
            child: Column(
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Zakres dat', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  icon: const Icon(Icons.calendar_today, size: 16),
                                  label: Text('${_startDate.day}/${_startDate.month}/${_startDate.year}'),
                                  onPressed: () async {
                                    final date = await showDatePicker(
                                      context: context,
                                      initialDate: _startDate,
                                      firstDate: DateTime(2020),
                                      lastDate: DateTime.now(),
                                    );
                                    if (date != null) {
                                      setState(() => _startDate = date);
                                      _loadAttendance();
                                    }
                                  },
                                ),
                              ),
                              const Padding(
                                padding: EdgeInsets.symmetric(horizontal: 8),
                                child: Text('-'),
                              ),
                              Expanded(
                                child: OutlinedButton.icon(
                                  icon: const Icon(Icons.calendar_today, size: 16),
                                  label: Text('${_endDate.day}/${_endDate.month}/${_endDate.year}'),
                                  onPressed: () async {
                                    final date = await showDatePicker(
                                      context: context,
                                      initialDate: _endDate,
                                      firstDate: _startDate,
                                      lastDate: DateTime.now().add(const Duration(days: 365)),
                                    );
                                    if (date != null) {
                                      setState(() => _endDate = date);
                                      _loadAttendance();
                                    }
                                  },
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Status', style: GoogleFonts.outfit(fontWeight: FontWeight.bold)),
                          const SizedBox(height: 8),
                          DropdownButtonFormField<String?>(
                            value: _statusFilter,
                            decoration: const InputDecoration(
                              border: OutlineInputBorder(),
                              contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            ),
                            items: const [
                              DropdownMenuItem(value: null, child: Text('Wszystkie')),
                              DropdownMenuItem(value: 'PENDING', child: Text('Oczekujące')),
                              DropdownMenuItem(value: 'CONFIRMED', child: Text('Potwierdzone')),
                              DropdownMenuItem(value: 'REJECTED', child: Text('Odrzucone')),
                            ],
                            onChanged: (value) {
                              setState(() => _statusFilter = value);
                              _loadAttendance();
                            },
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _error != null
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.error, size: 48, color: Colors.red),
                            const SizedBox(height: 16),
                            Text('Błąd: $_error'),
                            const SizedBox(height: 16),
                            ElevatedButton(
                              onPressed: _loadAttendance,
                              child: const Text('Spróbuj ponownie'),
                            ),
                          ],
                        ),
                      )
                    : _attendances.isEmpty
                        ? Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(Icons.inbox, size: 64, color: Colors.grey.shade400),
                                const SizedBox(height: 16),
                                Text(
                                  'Brak obecności w wybranym zakresie',
                                  style: GoogleFonts.outfit(fontSize: 16, color: Colors.grey),
                                ),
                              ],
                            ),
                          )
                        : ListView.builder(
                            padding: const EdgeInsets.all(16),
                            itemCount: _attendances.length,
                            itemBuilder: (context, index) {
                              final attendance = _attendances[index];
                              final status = attendance['status'] as String;
                              final isPending = status == 'PENDING';
                              final isConfirmed = status == 'CONFIRMED';
                              final isRejected = status == 'REJECTED';

                              return Card(
                                margin: const EdgeInsets.only(bottom: 12),
                                elevation: isPending ? 2 : 1,
                                color: isConfirmed
                                    ? Colors.green.shade50
                                    : isRejected
                                        ? Colors.red.shade50
                                        : null,
                                child: ListTile(
                                  leading: CircleAvatar(
                                    backgroundColor: isPending
                                        ? Colors.orange
                                        : isConfirmed
                                            ? Colors.green
                                            : Colors.red,
                                    child: Icon(
                                      isPending
                                          ? Icons.pending
                                          : isConfirmed
                                              ? Icons.check_circle
                                              : Icons.cancel,
                                      color: Colors.white,
                                    ),
                                  ),
                                  title: Text(
                                    attendance['user_name'] as String,
                                    style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
                                  ),
                                  subtitle: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text('Data: ${attendance['date']}'),
                                      Text('Godz: ${attendance['check_in']} - ${attendance['check_out']}'),
                                      if (!(attendance['was_scheduled'] as bool) && isPending)
                                        Text(
                                          '⚠️ Niezaplanowana obecność',
                                          style: TextStyle(color: Colors.orange.shade700, fontWeight: FontWeight.bold),
                                        ),
                                      Text(
                                        'Status: ${isPending ? "Oczekuje" : isConfirmed ? "Potwierdzone" : "Odrzucone"}',
                                        style: TextStyle(
                                          color: isPending
                                              ? Colors.orange.shade700
                                              : isConfirmed
                                                  ? Colors.green.shade700
                                                  : Colors.red.shade700,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ],
                                  ),
                                  trailing: isPending
                                      ? Row(
                                          mainAxisSize: MainAxisSize.min,
                                          children: [
                                            IconButton(
                                              icon: const Icon(Icons.check_circle, color: Colors.green),
                                              onPressed: () => _confirmAttendance(attendance['id'] as String),
                                              tooltip: 'Potwierdź',
                                            ),
                                            IconButton(
                                              icon: const Icon(Icons.cancel, color: Colors.red),
                                              onPressed: () => _rejectAttendance(attendance['id'] as String),
                                              tooltip: 'Odrzuć',
                                            ),
                                          ],
                                        )
                                      : Chip(
                                          label: Text(
                                            isConfirmed ? 'Zatwierdzone' : 'Odrzucone',
                                            style: const TextStyle(color: Colors.white, fontSize: 12),
                                          ),
                                          backgroundColor: isConfirmed ? Colors.green : Colors.red,
                                        ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
