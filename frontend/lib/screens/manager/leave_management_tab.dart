import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class LeaveManagementTab extends ConsumerStatefulWidget {
  const LeaveManagementTab({super.key});

  @override
  ConsumerState<LeaveManagementTab> createState() => _LeaveManagementTabState();
}

class _LeaveManagementTabState extends ConsumerState<LeaveManagementTab> {
  bool _isLoadingRequests = false;
  bool _isLoadingCalendar = false;
  List<LeaveRequest> _pendingRequests = [];
  List<LeaveCalendarEntry> _calendarEntries = [];
  
  DateTime _calendarMonth = DateTime(DateTime.now().year, DateTime.now().month, 1);

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    _loadPendingRequests();
    _loadCalendar();
  }

  Future<void> _loadPendingRequests() async {
    setState(() => _isLoadingRequests = true);
    try {
      final reqs = await ref.read(apiServiceProvider).getAllLeaveRequests(status: 'PENDING');
      setState(() {
        _pendingRequests = reqs;
        _isLoadingRequests = false;
      });
    } catch (e) {
      setState(() => _isLoadingRequests = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd ładowania wniosków: $e'), backgroundColor: Theme.of(context).colorScheme.error),
        );
      }
    }
  }

  Future<void> _loadCalendar() async {
    setState(() => _isLoadingCalendar = true);
    try {
      final entries = await ref.read(apiServiceProvider).getLeaveCalendar(_calendarMonth.year, _calendarMonth.month);
      setState(() {
        _calendarEntries = entries;
        _isLoadingCalendar = false;
      });
    } catch (e) {
      setState(() => _isLoadingCalendar = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd kalendarza urlopów: $e'), backgroundColor: Theme.of(context).colorScheme.error),
        );
      }
    }
  }

  void _previousMonth() {
    setState(() {
      _calendarMonth = DateTime(_calendarMonth.year, _calendarMonth.month - 1, 1);
    });
    _loadCalendar();
  }

  void _nextMonth() {
    setState(() {
      _calendarMonth = DateTime(_calendarMonth.year, _calendarMonth.month + 1, 1);
    });
    _loadCalendar();
  }

  Future<void> _approveRequest(String id) async {
    setState(() => _isLoadingRequests = true);
    try {
      await ref.read(apiServiceProvider).approveLeaveRequest(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Wniosek zaakceptowany'), backgroundColor: Colors.green));
      }
      _loadData(); // reload both to update calendar
    } catch (e) {
      setState(() => _isLoadingRequests = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e'), backgroundColor: Theme.of(context).colorScheme.error));
      }
    }
  }

  Future<void> _rejectRequest(String id) async {
    setState(() => _isLoadingRequests = true);
    try {
      await ref.read(apiServiceProvider).rejectLeaveRequest(id);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Wniosek odrzucony'), backgroundColor: Colors.orange));
      }
      _loadData();
    } catch (e) {
      setState(() => _isLoadingRequests = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e'), backgroundColor: Theme.of(context).colorScheme.error));
      }
    }
  }

  Color _getHeatColor(int count) {
    if (count == 0) return Colors.transparent;
    if (count == 1) return Colors.amber.shade100;
    if (count == 2) return Colors.orange.shade200;
    return Colors.red.shade200;
  }

  List<String> _getPeopleOnLeave(DateTime date) {
    final List<String> names = [];
    final dateStr = DateFormat('yyyy-MM-dd').format(date);
    for (var entry in _calendarEntries) {
      if (entry.status == 'APPROVED' &&
          entry.startDate.compareTo(dateStr) <= 0 &&
          entry.endDate.compareTo(dateStr) >= 0) {
        names.add(entry.userName);
      }
    }
    return names;
  }

  void _showDayTooltip(DateTime date, List<String> names) {
    showModalBottomSheet(
      context: context,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Urlopy - ${DateFormat('d MMMM yyyy', 'pl_PL').format(date)}',
                  style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                const Divider(),
                if (names.isEmpty)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 16.0),
                    child: Text('Brak urlopów w tym dniu'),
                  )
                else
                  ...names.map((n) => ListTile(
                    leading: const Icon(Icons.beach_access),
                    title: Text(n),
                  )),
              ],
            ),
          ),
        );
      }
    );
  }

  Widget _buildRequestsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0).copyWith(bottom: 8),
          child: Text(
            'Oczekujące wnioski (${_pendingRequests.length})',
            style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ),
        if (_isLoadingRequests && _pendingRequests.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (_pendingRequests.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16.0),
            child: Text('Brak oczekujących wniosków urlopowych.'),
          )
        else
          ListView.builder(
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            itemCount: _pendingRequests.length,
            itemBuilder: (context, index) {
              final req = _pendingRequests[index];
              final start = DateTime.parse(req.startDate);
              final end = DateTime.parse(req.endDate);
              final duration = end.difference(start).inDays + 1;

              return Card(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Padding(
                  padding: const EdgeInsets.all(12.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const Icon(Icons.person, size: 16),
                          const SizedBox(width: 8),
                          Text(req.userName, style: const TextStyle(fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.calendar_today, size: 16),
                          const SizedBox(width: 8),
                          Text(
                            '${DateFormat('dd.MM').format(start)} – ${DateFormat('dd.MM.yyyy').format(end)} ($duration dni)',
                            style: TextStyle(color: Colors.grey.shade700),
                          ),
                        ],
                      ),
                      if (req.reason != null && req.reason!.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text('Powód: ${req.reason}', style: TextStyle(color: Colors.grey.shade600, fontStyle: FontStyle.italic)),
                      ],
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton.icon(
                            onPressed: () => _rejectRequest(req.id),
                            icon: const Icon(Icons.close, color: Colors.red),
                            label: const Text('Odrzuć', style: TextStyle(color: Colors.red)),
                          ),
                          const SizedBox(width: 8),
                          FilledButton.icon(
                            onPressed: () => _approveRequest(req.id),
                            icon: const Icon(Icons.check),
                            label: const Text('Akceptuj'),
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
      ],
    );
  }

  Widget _buildCalendarSection() {
    final daysInMonth = DateTime(_calendarMonth.year, _calendarMonth.month + 1, 0).day;
    final firstDayOffset = (DateTime(_calendarMonth.year, _calendarMonth.month, 1).weekday - 1);
    final totalCells = daysInMonth + firstDayOffset;
    final weeks = (totalCells / 7).ceil();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0).copyWith(top: 24, bottom: 8),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Niedostępności',
                style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              Row(
                children: [
                  IconButton(icon: const Icon(Icons.chevron_left), onPressed: _previousMonth),
                  Text(
                    DateFormat('MMMM yyyy', 'pl_PL').format(_calendarMonth).toUpperCase(),
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  IconButton(icon: const Icon(Icons.chevron_right), onPressed: _nextMonth),
                ],
              ),
            ],
          ),
        ),
        if (_isLoadingCalendar)
          const Padding(
            padding: EdgeInsets.all(32.0),
            child: Center(child: CircularProgressIndicator()),
          )
        else
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd']
                      .map((d) => Expanded(
                            child: Center(child: Text(d, style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.grey))),
                          ))
                      .toList(),
                ),
                const SizedBox(height: 8),
                GridView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 7,
                    childAspectRatio: 1,
                    crossAxisSpacing: 4,
                    mainAxisSpacing: 4,
                  ),
                  itemCount: weeks * 7,
                  itemBuilder: (context, index) {
                    if (index < firstDayOffset || index >= firstDayOffset + daysInMonth) {
                      return const SizedBox.shrink();
                    }
                    
                    final day = index - firstDayOffset + 1;
                    final date = DateTime(_calendarMonth.year, _calendarMonth.month, day);
                    final isToday = date.year == DateTime.now().year && date.month == DateTime.now().month && date.day == DateTime.now().day;
                    
                    final namesOnLeave = _getPeopleOnLeave(date);
                    final heatColor = _getHeatColor(namesOnLeave.length);

                    return InkWell(
                      onTap: () => _showDayTooltip(date, namesOnLeave),
                      borderRadius: BorderRadius.circular(8),
                      child: Container(
                        decoration: BoxDecoration(
                          color: heatColor,
                          borderRadius: BorderRadius.circular(8),
                          border: isToday ? Border.all(color: Theme.of(context).colorScheme.primary, width: 2) : Border.all(color: Colors.grey.shade200),
                        ),
                        child: Stack(
                          children: [
                            Positioned(
                              top: 2,
                              left: 4,
                              child: Text(
                                '$day',
                                style: TextStyle(
                                  fontSize: 12,
                                  fontWeight: isToday ? FontWeight.bold : FontWeight.normal,
                                  color: isToday ? Theme.of(context).colorScheme.primary : Colors.black87,
                                ),
                              ),
                            ),
                            if (namesOnLeave.isNotEmpty)
                              Positioned(
                                bottom: 2,
                                right: 4,
                                child: Text(
                                  '${namesOnLeave.length}',
                                  style: TextStyle(
                                    fontSize: 10,
                                    fontWeight: FontWeight.bold,
                                    color: Colors.red.shade900,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildRequestsSection(),
          const Divider(height: 32),
          _buildCalendarSection(),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}
