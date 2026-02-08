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
  List<Map<String, dynamic>>? _pendingAttendances;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPending();
  }

  Future<void> _loadPending() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final api = ref.read(apiServiceProvider);
      final pending = await api.getPendingAttendance();
      setState(() {
        _pendingAttendances = pending;
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
      final api = ref.read(apiServiceProvider);
      await api.confirmAttendance(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Obecność potwierdzona'), backgroundColor: Colors.green),
        );
        _loadPending();
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
      final api = ref.read(apiServiceProvider);
      await api.rejectAttendance(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Obecność odrzucona'), backgroundColor: Colors.orange),
        );
        _loadPending();
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
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Błąd: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: _loadPending, child: const Text('Ponów')),
          ],
        ),
      );
    }

    if (_pendingAttendances == null || _pendingAttendances!.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.check_circle_outline, size: 64, color: Colors.green.shade400),
            const SizedBox(height: 16),
            Text(
              'Brak oczekujących zatwierdzeń',
              style: GoogleFonts.inter(fontSize: 16, color: Colors.grey.shade600),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadPending,
      child: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _pendingAttendances!.length,
        itemBuilder: (context, index) {
          final a = _pendingAttendances![index];
          final date = DateTime.parse(a['date']);
          
          return Card(
            margin: const EdgeInsets.only(bottom: 12),
            color: Colors.orange.shade50,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.warning_amber, color: Colors.orange.shade700),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          a['user_name'] ?? 'Nieznany',
                          style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(date),
                    style: GoogleFonts.inter(fontSize: 14),
                  ),
                  Text(
                    'Godziny: ${a['check_in']} - ${a['check_out']}',
                    style: GoogleFonts.inter(color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '⚠️ Nieplanowana obecność',
                    style: TextStyle(color: Colors.orange.shade700, fontSize: 12),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      OutlinedButton.icon(
                        onPressed: () => _rejectAttendance(a['id']),
                        icon: const Icon(Icons.close, size: 18),
                        label: const Text('Odrzuć'),
                        style: OutlinedButton.styleFrom(foregroundColor: Colors.red),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.icon(
                        onPressed: () => _confirmAttendance(a['id']),
                        icon: const Icon(Icons.check, size: 18),
                        label: const Text('Potwierdź'),
                        style: FilledButton.styleFrom(backgroundColor: Colors.green),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
