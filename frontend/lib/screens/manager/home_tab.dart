
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';
import 'package:calendar_view/calendar_view.dart';

class HomeTab extends ConsumerStatefulWidget {
  const HomeTab({super.key});

  @override
  ConsumerState<HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends ConsumerState<HomeTab> {
  late Future<DashboardHome> _dashboardFuture;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    setState(() {
      _dashboardFuture = ref.read(apiServiceProvider).getDashboardHome(
        date: DateTime.now(),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async => _refresh(),
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Dzień dobry!',
              style: GoogleFonts.outfit(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: Colors.indigo.shade900,
              ),
            ),
            Text(
              DateFormat('EEEE, d MMMM yyyy', 'pl_PL').format(DateTime.now()),
              style: GoogleFonts.inter(
                fontSize: 16,
                color: Colors.grey.shade600,
              ),
            ),
            const SizedBox(height: 24),
            
            FutureBuilder<DashboardHome>(
              future: _dashboardFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(child: Text('Błąd: ${snapshot.error}'));
                }
                if (!snapshot.hasData) {
                  return const Center(child: Text('Brak danych'));
                }

                final data = snapshot.data!;
                
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _buildSectionTitle('Dzisiaj w pracy', Icons.work),
                    const SizedBox(height: 12),
                    _buildWorkingTodayList(data.workingToday),
                    
                    const SizedBox(height: 32),
                    
                    _buildSectionTitle('Zaległe potwierdzenia', Icons.warning_amber),
                     const SizedBox(height: 12),
                    _buildMissingConfirmationsList(data.missingConfirmations),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: Colors.indigo.shade700, size: 24),
        const SizedBox(width: 8),
        Text(
          title,
          style: GoogleFonts.outfit(
            fontSize: 20,
            fontWeight: FontWeight.bold,
            color: Colors.black87,
          ),
        ),
      ],
    );
  }


  Widget _buildWorkingTodayList(List<ScheduleEntry> entries) {
    if (entries.isEmpty) {
      return Card(
        color: Colors.grey.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(Icons.person_off, color: Colors.grey.shade400),
              const SizedBox(width: 12),
              Text(
                'Nikogo dzisiaj nie ma w grafiku',
                style: TextStyle(color: Colors.grey.shade600),
              ),
            ],
          ),
        ),
      );
    }

    // Convert entries to CalendarEventData
    final events = entries.map((e) {
      // Parse time strings "HH:MM" or "HH:MM:SS"
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      
      final startParts = e.startTime.split(':');
      final endParts = e.endTime.split(':');
      
      final start = DateTime(
        now.year, now.month, now.day, 
        int.parse(startParts[0]), int.parse(startParts[1])
      );
      
      var end = DateTime(
        now.year, now.month, now.day, 
        int.parse(endParts[0]), int.parse(endParts[1])
      );
      
      if (end.isBefore(start)) {
        end = end.add(const Duration(days: 1));
      }

      print('DEBUG: Event processed: ${e.userName} ${start.toString()} - ${end.toString()}');

      return CalendarEventData(
        date: today,
        startTime: start,
        endTime: end,
        title: e.userName,
        description: "${e.shiftName} • ${e.roleName}",
        color: Colors.indigo.shade100, // You might want role-specific colors here
        event: e, // Store full object
      );
    }).toList();

    print('DEBUG: Total events to convert: ${entries.length}');
    print('DEBUG: Total events converted: ${events.length}');

    // We can't use DayView directly inside a SingleChildScrollView safely if it scrolls itself.
    // DayView usually takes full height.
    // Option 1: Fixed height container
    final now = DateTime.now();
    final todayStart = DateTime(now.year, now.month, now.day);
    
    return SizedBox(
      height: 600, // Adjust as needed
      child: DayView(
        key: UniqueKey(), // Force rebuild when data changes
        controller: EventController<ScheduleEntry>()..addAll(events),
        minDay: todayStart,
        maxDay: todayStart.add(const Duration(days: 1)),
        initialDay: todayStart,
        showVerticalLine: true,
        showLiveTimeLineInAllDays: true,
        heightPerMinute: 0.8, // Slightly more compact
        eventTileBuilder: (date, events, boundary, start, end) {
          if (events.isEmpty) return Container();
          final event = events.first;
          final entry = event.event as ScheduleEntry?;
          
          return Container(
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border(
                left: BorderSide(color: event.color ?? Colors.indigo, width: 4),
                top: BorderSide(color: Colors.grey.shade200),
                right: BorderSide(color: Colors.grey.shade200),
                bottom: BorderSide(color: Colors.grey.shade200),
              ),
            ),
            padding: const EdgeInsets.all(8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 10,
                      backgroundColor: event.color?.withOpacity(0.2) ?? Colors.indigo.shade50,
                      child: Text(
                        event.title.isNotEmpty ? event.title[0].toUpperCase() : '?',
                        style: TextStyle(
                          fontSize: 10, 
                          color: event.color ?? Colors.indigo,
                          fontWeight: FontWeight.bold
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        event.title,
                        style: GoogleFonts.inter(fontWeight: FontWeight.w600, fontSize: 12),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                if (entry != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: event.color?.withOpacity(0.1) ?? Colors.grey.shade100,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      entry.roleName,
                      style: TextStyle(
                        fontSize: 10, 
                        color: event.color?.withOpacity(0.8) ?? Colors.grey.shade700,
                        fontWeight: FontWeight.w500
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                 const Spacer(),
                 Text(
                  "${start.hour}:${start.minute.toString().padLeft(2,'0')} - ${end.hour}:${end.minute.toString().padLeft(2,'0')}",
                  style: TextStyle(fontSize: 10, color: Colors.grey.shade500),
                 ),
              ],
            ),
          );
        },
        dayTitleBuilder: (date) => Container(), // Hide header
      ),
    );
  }

  Widget _buildMissingConfirmationsList(List<Map<String, dynamic>> items) {
    if (items.isEmpty) {
      return Card(
        color: Colors.green.shade50,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Row(
            children: [
              Icon(Icons.check_circle_outline, color: Colors.green.shade600),
              const SizedBox(width: 12),
              Text(
                'Wszystkie obecności potwierdzone',
                style: TextStyle(color: Colors.green.shade800),
              ),
            ],
          ),
        ),
      );
    }

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        final userName = item['user_name'] ?? 'Nieznany';
        final dateStr = item['date'] ?? '';
        
        return Card(
          elevation: 1,
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Colors.orange.shade100,
              child: Icon(Icons.warning, color: Colors.orange.shade700, size: 20),
            ),
            title: Text(userName, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text('Brak potwierdzenia obecności z dnia $dateStr'),
            trailing: OutlinedButton(
              onPressed: () {
                // Navigate to attendance approval tab
                // This requires a way to change tab in parent
                // For now, just show info
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Przejdź do zakładki "Obecności", aby zarządzać')),
                );
              },
              child: const Text('Sprawdź'),
            ),
          ),
        );
      },
    );
  }
}
