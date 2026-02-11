import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class RequirementsTab extends ConsumerStatefulWidget {
  const RequirementsTab({super.key});

  @override
  ConsumerState<RequirementsTab> createState() => _RequirementsTabState();
}

class _RequirementsTabState extends ConsumerState<RequirementsTab> {
  DateTime _selectedWeekStart = _getMonday(DateTime.now());
  bool _isRequirementsLoading = false;
  bool _isSaving = false;
  bool _isWeeklyMode = false; // Toggle between weekly defaults and specific dates
  
  // Map to store requirement counts: 
  // Specific: "YYYY-MM-DD_shiftId_roleId" -> count
  // Weekly: "dow_shiftId_roleId" -> count
  final Map<String, int> _requirementCounts = {};

  static DateTime _getMonday(DateTime date) {
    return date.subtract(Duration(days: date.weekday - 1));
  }

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadRequirements();
    });
  }

  Future<void> _loadRequirements() async {
    setState(() => _isRequirementsLoading = true);
    
    try {
      final api = ref.read(apiServiceProvider);
      
      // Load requirements. 
      // If weekly mode, we fetch a wide range or handle specially? 
      // Actually, the backend returns both in the range if we ask.
      // But for weekly mode, we might want to fetch all global reqs.
      // For now, let's fetch the current week and extract global ones if needed,
      // OR better: always fetch both?
      
      final requirements = await api.getRequirements(_selectedWeekStart, _selectedWeekEnd);
      
      setState(() {
        _requirementCounts.clear();
        for (var req in requirements) {
          if (req.date != null) {
            final key = _makeDateKey(req.date!, req.shiftDefId, req.roleId);
            _requirementCounts[key] = req.minCount;
          }
          if (req.dayOfWeek != null) {
            final key = _makeWeeklyKey(req.dayOfWeek!, req.shiftDefId, req.roleId);
            _requirementCounts[key] = req.minCount;
          }
        }
        
        _isRequirementsLoading = false;
      });
    } catch (e) {
      setState(() => _isRequirementsLoading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd ładowania wymagań: $e')),
        );
      }
    }
  }

  String _makeDateKey(DateTime date, int shiftId, int roleId) {
    return '${date.toIso8601String().split('T')[0]}_${shiftId}_$roleId';
  }

  String _makeWeeklyKey(int dow, int shiftId, int roleId) {
    return 'dow_${dow}_${shiftId}_$roleId';
  }

  int _getCount(DateTime? date, int? dow, int shiftId, int roleId) {
    final key = date != null 
        ? _makeDateKey(date, shiftId, roleId)
        : _makeWeeklyKey(dow!, shiftId, roleId);
    return _requirementCounts[key] ?? 0;
  }

  void _setCount(DateTime? date, int? dow, int shiftId, int roleId, int count) {
    final key = date != null 
        ? _makeDateKey(date, shiftId, roleId)
        : _makeWeeklyKey(dow!, shiftId, roleId);
    setState(() {
      if (count > 0) {
        _requirementCounts[key] = count;
      } else {
        _requirementCounts.remove(key);
      }
    });
  }

  Future<void> _saveRequirements() async {
    setState(() => _isSaving = true);
    
    try {
      final updates = <RequirementUpdate>[];
      
      _requirementCounts.forEach((key, count) {
        final parts = key.split('_');
        if (key.startsWith('dow_')) {
          // Weekly: "dow_X_shiftId_roleId"
          final dow = int.parse(parts[1]);
          final shiftId = int.parse(parts[2]);
          final roleId = int.parse(parts[3]);
          updates.add(RequirementUpdate(
            dayOfWeek: dow,
            shiftDefId: shiftId,
            roleId: roleId,
            minCount: count,
          ));
        } else {
          // Specific: "YYYY-MM-DD_shiftId_roleId"
          final date = DateTime.parse(parts[0]);
          final shiftId = int.parse(parts[1]);
          final roleId = int.parse(parts[2]);
          
          updates.add(RequirementUpdate(
            date: date,
            shiftDefId: shiftId,
            roleId: roleId,
            minCount: count,
          ));
        }
      });
      
      await ref.read(apiServiceProvider).setRequirements(updates);
      
      setState(() => _isSaving = false);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✓ Wymagania zapisane'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      setState(() => _isSaving = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd zapisu: $e')),
        );
      }
    }
  }

  void _previousWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7));
    });
    _loadRequirements();
  }

  void _nextWeek() {
    setState(() {
      _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7));
    });
    _loadRequirements();
  }

  List<DateTime> _getWeekDays() {
    return List.generate(7, (i) => _selectedWeekStart.add(Duration(days: i)));
  }

  @override
  Widget build(BuildContext context) {
    final rolesAsync = ref.watch(rolesProvider);
    final shiftsAsync = ref.watch(shiftsProvider);

    return rolesAsync.when(
      data: (roles) => shiftsAsync.when(
        data: (shifts) => _buildContent(roles, shifts),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, s) => Center(child: Text('Błąd ładowania zmian: $e')),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, s) => Center(child: Text('Błąd ładowania ról: $e')),
    );
  }

  Widget _buildContent(List<JobRole> roles, List<ShiftDefinition> shifts) {
    if (roles.isEmpty || shifts.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(Icons.warning_amber, size: 64, color: Colors.orange.shade400),
              const SizedBox(height: 16),
              Text(
                'Najpierw zdefiniuj role i zmiany',
                style: GoogleFonts.outfit(fontSize: 18, fontWeight: FontWeight.w600),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                'Przejdź do zakładki "Konfiguracja"',
                style: GoogleFonts.inter(fontSize: 14, color: Colors.grey.shade600),
              ),
            ],
          ),
        ),
      );
    }

    final weekDays = _getWeekDays();
    final isLoading = _isRequirementsLoading;

    return Stack(
      children: [
        SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Wymagania Obsadowe',
                style: GoogleFonts.outfit(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Określ ile pracowników potrzebujesz na każdej zmianie',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: Colors.grey.shade600,
                ),
              ),
              const SizedBox(height: 16),
              
              // Mode Selector
              Center(
                child: SegmentedButton<bool>(
                  segments: const [
                    ButtonSegment<bool>(
                      value: false,
                      label: Text('Konkretne Daty'),
                      icon: Icon(Icons.calendar_month),
                    ),
                    ButtonSegment<bool>(
                      value: true,
                      label: Text('Stałe Tygodniowe'),
                      icon: Icon(Icons.repeat),
                    ),
                  ],
                  selected: {_isWeeklyMode},
                  onSelectionChanged: (Set<bool> newSelection) {
                    setState(() {
                      _isWeeklyMode = newSelection.first;
                    });
                  },
                ),
              ),
              const SizedBox(height: 16),
              
              // Week Selector (only in Specific mode)
              if (!_isWeeklyMode)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.chevron_left),
                          onPressed: _previousWeek,
                        ),
                        Text(
                          '${DateFormat('d MMM', 'pl_PL').format(_selectedWeekStart)} - ${DateFormat('d MMM yyyy', 'pl_PL').format(_selectedWeekEnd)}',
                          style: GoogleFonts.inter(
                            fontSize: 18,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.chevron_right),
                          onPressed: _nextWeek,
                        ),
                      ],
                    ),
                  ),
                ),
              
              if (_isWeeklyMode)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Text(
                    'Podstawowe wymagania powtarzane co tydzień',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      color: Colors.blue.shade700,
                      fontWeight: FontWeight.w500,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ),

              const SizedBox(height: 16),
              
              const SizedBox(height: 16),
              
              // Requirements Grid
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Header row with days
                        Row(
                          children: [
                            SizedBox(
                              width: 120,
                              child: Text(
                                'Zmiana',
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.bold,
                                  fontSize: 14,
                                ),
                              ),
                            ),
                            ...(_isWeeklyMode 
                                ? List.generate(7, (i) => i) 
                                : weekDays).map((item) => SizedBox(
                              width: 100,
                              child: Center(
                                child: _isWeeklyMode
                                  ? Text(
                                      ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'][item as int],
                                      style: GoogleFonts.inter(
                                        fontWeight: FontWeight.bold,
                                        fontSize: 14,
                                      ),
                                    )
                                  : Column(
                                      children: [
                                        Text(
                                          DateFormat('EEE', 'pl_PL').format(item as DateTime),
                                          style: GoogleFonts.inter(
                                            fontWeight: FontWeight.bold,
                                            fontSize: 12,
                                          ),
                                        ),
                                        Text(
                                          DateFormat('d MMM', 'pl_PL').format(item),
                                          style: GoogleFonts.inter(
                                            fontSize: 11,
                                            color: Colors.grey.shade600,
                                          ),
                                        ),
                                      ],
                                    ),
                              ),
                            )),
                          ],
                        ),
                        
                        const Divider(height: 24),
                        
                        // Rows for each shift
                        ...(shifts.map((shift) => Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Shift name
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 8),
                              child: Text(
                                shift.name,
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 15,
                                ),
                              ),
                            ),
                            
                            // Rows for each role within this shift
                            ...(roles.map((role) => Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  SizedBox(
                                    width: 120,
                                    child: Row(
                                      children: [
                                        Container(
                                          width: 12,
                                          height: 12,
                                          decoration: BoxDecoration(
                                            color: Color(int.parse(role.colorHex.replaceFirst('#', '0xFF'))),
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                        const SizedBox(width: 8),
                                        Expanded(
                                          child: Text(
                                            role.name,
                                            style: GoogleFonts.inter(fontSize: 13),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  
                                  // Counter for each day
                                  ...(_isWeeklyMode 
                                      ? List.generate(7, (i) => i) 
                                      : weekDays).map((item) => SizedBox(
                                    width: 100,
                                    child: Center(
                                      child: _isWeeklyMode
                                        ? _buildCounter(null, item as int, shift.id, role.id)
                                        : _buildCounter(item as DateTime, null, shift.id, role.id),
                                    ),
                                  )),
                                ],
                              ),
                            ))),
                            
                            const Divider(height: 16),
                          ],
                        ))),
                      ],
                    ),
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              // Save Button
              SizedBox(
                width: double.infinity,
                height: 50,
                child: ElevatedButton.icon(
                  onPressed: _isSaving ? null : _saveRequirements,
                  icon: _isSaving
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            color: Colors.white,
                          ),
                        )
                      : const Icon(Icons.save),
                  label: Text(
                    _isSaving ? 'Zapisywanie...' : 'Zapisz Wymagania',
                    style: const TextStyle(fontSize: 16),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.indigo.shade700,
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              // Info Card
              Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.info_outline, color: Colors.blue.shade700),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Text(
                          'Ustaw liczbę pracowników potrzebnych dla każdej roli na każdej zmianie. Te wymagania będą użyte przez generator grafiku.',
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            color: Colors.blue.shade900,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
        if (isLoading)
          Container(
            color: Colors.black.withOpacity(0.1),
            child: const Center(child: CircularProgressIndicator()),
          ),
      ],
    );
  }

  Widget _buildCounter(DateTime? date, int? dow, int shiftId, int roleId) {
    final count = _getCount(date, dow, shiftId, roleId);
    
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          InkWell(
            onTap: () {
              if (count > 0) {
                _setCount(date, dow, shiftId, roleId, count - 1);
              }
            },
            child: Container(
              padding: const EdgeInsets.all(4),
              child: Icon(
                Icons.remove,
                size: 16,
                color: count > 0 ? Colors.indigo : Colors.grey.shade400,
              ),
            ),
          ),
          SizedBox(
            width: 30,
            child: Text(
              count.toString(),
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          InkWell(
            onTap: () {
              _setCount(date, dow, shiftId, roleId, count + 1);
            },
            child: Container(
              padding: const EdgeInsets.all(4),
              child: Icon(
                Icons.add,
                size: 16,
                color: Colors.indigo,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
