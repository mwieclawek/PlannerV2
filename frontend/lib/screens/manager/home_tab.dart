
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';

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
      _dashboardFuture = ref.read(apiServiceProvider).getDashboardHome();
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

    // Sort by start time
    entries.sort((a, b) => a.shiftName.compareTo(b.shiftName)); // Rough sort, better by time if available in entry details

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        final entry = entries[index];
        return Card(
          elevation: 1,
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            leading: CircleAvatar(
              backgroundColor: Colors.indigo.shade100,
              child: Text(
                entry.userName.isNotEmpty ? entry.userName[0].toUpperCase() : '?',
                style: TextStyle(color: Colors.indigo.shade700, fontWeight: FontWeight.bold),
              ),
            ),
            title: Text(entry.userName, style: const TextStyle(fontWeight: FontWeight.w600)),
            subtitle: Text('${entry.shiftName} • ${entry.roleName}'),
            trailing: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.green.shade200),
              ),
              child: Text(
                'W pracy', // Or show time range if available in entry
                style: TextStyle(color: Colors.green.shade700, fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ),
        );
      },
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
