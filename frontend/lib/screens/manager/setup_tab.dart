import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';
import '../../services/api_service.dart';

class SetupTab extends StatefulWidget {
  const SetupTab({super.key});

  @override
  State<SetupTab> createState() => _SetupTabState();
}

class _SetupTabState extends State<SetupTab> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: Colors.indigo.shade700,
            unselectedLabelColor: Colors.grey.shade600,
            indicatorColor: Colors.indigo.shade700,
            tabs: const [
              Tab(text: 'Restauracja', icon: Icon(Icons.store)),
              Tab(text: 'Role i Zmiany', icon: Icon(Icons.people_alt)),
              Tab(text: 'Wymagania', icon: Icon(Icons.assignment)),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [
              _RestaurantConfigTab(),
              _RolesShiftsTab(),
              _RequirementsTab(),
            ],
          ),
        ),
      ],
    );
  }
}

// --- TAB 1: Restaurant Config ---

class _RestaurantConfigTab extends ConsumerStatefulWidget {
  const _RestaurantConfigTab();

  @override
  ConsumerState<_RestaurantConfigTab> createState() => _RestaurantConfigTabState();
}

class _RestaurantConfigTabState extends ConsumerState<_RestaurantConfigTab> {
  final _restaurantNameController = TextEditingController();
  final _openingHoursController = TextEditingController();
  final _closingHoursController = TextEditingController();
  final _addressController = TextEditingController();
  bool _isLoadingConfig = true;
  bool _isSavingConfig = false;

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  @override
  void dispose() {
    _restaurantNameController.dispose();
    _openingHoursController.dispose();
    _closingHoursController.dispose();
    _addressController.dispose();
    super.dispose();
  }

  Future<void> _loadConfig() async {
    try {
      final config = await ref.read(apiServiceProvider).getConfig();
      if (mounted) {
        setState(() {
          _restaurantNameController.text = config['name'] ?? '';
          _addressController.text = config['address'] ?? '';
          final hours = config['opening_hours'] ?? '';
          if (hours.isNotEmpty && hours.contains('-')) {
            final parts = hours.split('-');
            if (parts.length == 2) {
              _openingHoursController.text = parts[0].trim();
              _closingHoursController.text = parts[1].trim();
            }
          }
          _isLoadingConfig = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _isLoadingConfig = false);
    }
  }

  Future<void> _saveConfig() async {
    setState(() => _isSavingConfig = true);
    try {
      final openingHours = '${_openingHoursController.text}-${_closingHoursController.text}';
      await ref.read(apiServiceProvider).saveConfig(
            _restaurantNameController.text,
            openingHours,
            _addressController.text.isNotEmpty ? _addressController.text : null,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('✓ Zapisano ustawienia restauracji'),
            backgroundColor: Colors.green.shade600,
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red.shade600),
        );
      }
    } finally {
      if (mounted) setState(() => _isSavingConfig = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Konfiguracja Restauracji',
            style: GoogleFonts.outfit(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: _isLoadingConfig
                  ? const Center(child: CircularProgressIndicator())
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        TextField(
                          controller: _restaurantNameController,
                          decoration: const InputDecoration(
                            labelText: 'Nazwa restauracji',
                            hintText: 'np. Kawiarnia Pod Lipą',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.restaurant),
                          ),
                        ),
                        const SizedBox(height: 16),
                        TextField(
                          controller: _addressController,
                          decoration: const InputDecoration(
                            labelText: 'Adres',
                            hintText: 'np. ul. Główna 15, Warszawa',
                            border: OutlineInputBorder(),
                            prefixIcon: Icon(Icons.location_on),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Row(
                          children: [
                            Expanded(
                              child: TextField(
                                controller: _openingHoursController,
                                decoration: const InputDecoration(
                                  labelText: 'Otwarcie (HH:MM)',
                                  hintText: '08:00',
                                  border: OutlineInputBorder(),
                                  prefixIcon: Icon(Icons.access_time),
                                ),
                              ),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: TextField(
                                controller: _closingHoursController,
                                decoration: const InputDecoration(
                                  labelText: 'Zamknięcie (HH:MM)',
                                  hintText: '22:00',
                                  border: OutlineInputBorder(),
                                  prefixIcon: Icon(Icons.access_time_filled),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          height: 50,
                          child: ElevatedButton.icon(
                            onPressed: _isSavingConfig ? null : _saveConfig,
                            icon: _isSavingConfig
                                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                                : const Icon(Icons.save),
                            label: Text(_isSavingConfig ? 'Zapisywanie...' : 'Zapisz ustawienia'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.indigo.shade700,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

// --- TAB 2: Roles & Shifts ---

class _RolesShiftsTab extends ConsumerStatefulWidget {
  const _RolesShiftsTab();

  @override
  ConsumerState<_RolesShiftsTab> createState() => _RolesShiftsTabState();
}

class _RolesShiftsTabState extends ConsumerState<_RolesShiftsTab> {
  final _roleNameController = TextEditingController();
  int _roleColorIndex = 0;
  final _shiftNameController = TextEditingController();
  final _shiftStartController = TextEditingController();
  final _shiftEndController = TextEditingController();
  List<int> _selectedDays = [0, 1, 2, 3, 4, 5, 6];

  @override
  void dispose() {
    _roleNameController.dispose();
    _shiftNameController.dispose();
    _shiftStartController.dispose();
    _shiftEndController.dispose();
    super.dispose();
  }

  String _generateRoleColor() {
    final hue = (_roleColorIndex * 137.508) % 360;
    final saturation = 0.65 + (_roleColorIndex % 3) * 0.1;
    final lightness = 0.50 + (_roleColorIndex % 2) * 0.05;
    
    final c = (1 - (2 * lightness - 1).abs()) * saturation;
    final x = c * (1 - ((hue / 60) % 2 - 1).abs());
    final m = lightness - c / 2;
    
    double r = 0, g = 0, b = 0;
    if (hue < 60) { r = c; g = x; }
    else if (hue < 120) { r = x; g = c; }
    else if (hue < 180) { g = c; b = x; }
    else if (hue < 240) { g = x; b = c; }
    else if (hue < 300) { r = x; b = c; }
    else { r = c; b = x; }
    
    final red = ((r + m) * 255).round();
    final green = ((g + m) * 255).round();
    final blue = ((b + m) * 255).round();
    
    _roleColorIndex++;
    return '#${red.toRadixString(16).padLeft(2, '0')}${green.toRadixString(16).padLeft(2, '0')}${blue.toRadixString(16).padLeft(2, '0')}'.toUpperCase();
  }

  Color _parseColor(String hex) {
    try {
      return Color(int.parse(hex.replaceFirst('#', 'FF'), radix: 16));
    } catch (e) {
      return Colors.grey;
    }
  }
  
  String _formatDays(List<int> days) {
    if (days.length == 7) return 'Codziennie';
    const names = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'];
    return days.map((d) => names[d]).join(', ');
  }

  Future<void> _addRole() async {
    if (_roleNameController.text.isEmpty) return;
    try {
      await ref.read(apiServiceProvider).createRole(
            _roleNameController.text,
            _generateRoleColor(),
          );
      _roleNameController.clear();
      ref.invalidate(rolesProvider);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('✓ Rola dodana')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e')));
    }
  }

  Future<void> _addShift() async {
    if (_shiftNameController.text.isEmpty) return;
    try {
      await ref.read(apiServiceProvider).createShift(
            _shiftNameController.text,
            _shiftStartController.text,
            _shiftEndController.text,
            applicableDays: _selectedDays,
          );
      _shiftNameController.clear();
      _shiftStartController.clear();
      _shiftEndController.clear();
      setState(() => _selectedDays = [0, 1, 2, 3, 4, 5, 6]);
      ref.invalidate(shiftsProvider);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('✓ Zmiana dodana')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e')));
    }
  }

  Future<void> _deleteRole(JobRole role) async {
    try {
        await ref.read(apiServiceProvider).deleteRole(role.id);
        ref.invalidate(rolesProvider);
    } catch (e) {
        if(mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e')));
    }
  }
  
  Future<void> _deleteShift(ShiftDefinition shift) async {
    try {
        await ref.read(apiServiceProvider).deleteShift(shift.id);
        ref.invalidate(shiftsProvider);
    } catch (e) {
        if(mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final rolesAsync = ref.watch(rolesProvider);
    final shiftsAsync = ref.watch(shiftsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Roles Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Role / Stanowiska', style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _roleNameController,
                          decoration: const InputDecoration(labelText: 'Nazwa roli', border: OutlineInputBorder()),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(onPressed: _addRole, child: const Text('Dodaj')),
                    ],
                  ),
                  const SizedBox(height: 16),
                  rolesAsync.when(
                    data: (roles) => Column(
                      children: roles.map((role) => ListTile(
                        leading: CircleAvatar(backgroundColor: _parseColor(role.colorHex), radius: 12),
                        title: Text(role.name),
                        trailing: IconButton(icon: const Icon(Icons.delete), onPressed: () => _deleteRole(role)),
                      )).toList(),
                    ),
                    loading: () => const CircularProgressIndicator(),
                    error: (e, s) => Text('Błąd: $e'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          // Shifts Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Zmiany', style: GoogleFonts.outfit(fontSize: 20, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 16),
                  TextField(controller: _shiftNameController, decoration: const InputDecoration(labelText: 'Nazwa zmiany', border: OutlineInputBorder())),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(child: TextField(controller: _shiftStartController, decoration: const InputDecoration(labelText: 'Start (HH:MM)', border: OutlineInputBorder()))),
                      const SizedBox(width: 8),
                      Expanded(child: TextField(controller: _shiftEndController, decoration: const InputDecoration(labelText: 'Koniec (HH:MM)', border: OutlineInputBorder()))),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 4,
                    children: List.generate(7, (i) => FilterChip(
                      label: Text(['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'][i]),
                      selected: _selectedDays.contains(i),
                      onSelected: (s) => setState(() => s ? _selectedDays.add(i) : _selectedDays.remove(i)),
                    )),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(width: double.infinity, child: ElevatedButton(onPressed: _addShift, child: const Text('Dodaj Zmianę'))),
                  const SizedBox(height: 16),
                  shiftsAsync.when(
                    data: (shifts) => Column(
                      children: shifts.map((shift) => ListTile(
                        title: Text(shift.name),
                        subtitle: Text('${shift.startTime} - ${shift.endTime} (${_formatDays(shift.applicableDays)})'),
                        trailing: IconButton(icon: const Icon(Icons.delete), onPressed: () => _deleteShift(shift)),
                      )).toList(),
                    ),
                    loading: () => const CircularProgressIndicator(),
                    error: (e, s) => Text('Błąd: $e'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// --- TAB 3: Requirements ---

class _RequirementsTab extends ConsumerStatefulWidget {
  const _RequirementsTab();

  @override
  ConsumerState<_RequirementsTab> createState() => _RequirementsTabState();
}

class _RequirementsTabState extends ConsumerState<_RequirementsTab> {
  DateTime _selectedWeekStart = DateTime.now().subtract(Duration(days: DateTime.now().weekday - 1));
  bool _isRequirementsLoading = false;
  bool _isSaving = false;
  bool _isWeeklyMode = false;
  final Map<String, int> _requirementCounts = {};

  DateTime get _selectedWeekEnd => _selectedWeekStart.add(const Duration(days: 6));

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _loadRequirements());
  }

  void _loadRequirements() async {
    setState(() => _isRequirementsLoading = true);
    try {
      final requirements = await ref.read(apiServiceProvider).getRequirements(_selectedWeekStart, _selectedWeekEnd);
      setState(() {
        _requirementCounts.clear();
        for (var req in requirements) {
          if (req.date != null) {
            _requirementCounts['${req.date!.toIso8601String().split('T')[0]}_${req.shiftDefId}_${req.roleId}'] = req.minCount;
          }
          if (req.dayOfWeek != null) {
            _requirementCounts['dow_${req.dayOfWeek}_${req.shiftDefId}_${req.roleId}'] = req.minCount;
          }
        }
        _isRequirementsLoading = false;
      });
    } catch (e) {
      setState(() => _isRequirementsLoading = false);
    }
  }

  void _saveRequirements() async {
    setState(() => _isSaving = true);
    try {
      final updates = <RequirementUpdate>[];
      _requirementCounts.forEach((key, count) {
        final parts = key.split('_');
        if (key.startsWith('dow_')) {
          updates.add(RequirementUpdate(
            dayOfWeek: int.parse(parts[1]),
            shiftDefId: int.parse(parts[2]),
            roleId: int.parse(parts[3]),
            minCount: count,
          ));
        } else {
          updates.add(RequirementUpdate(
            date: DateTime.parse(parts[0]),
            shiftDefId: int.parse(parts[1]),
            roleId: int.parse(parts[2]),
            minCount: count,
          ));
        }
      });
      await ref.read(apiServiceProvider).setRequirements(updates);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('✓ Zapisano wymagania')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Błąd: $e')));
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  int _getCount(DateTime? date, int? dow, int shiftId, int roleId) {
    final key = date != null ? '${date.toIso8601String().split('T')[0]}_${shiftId}_$roleId' : 'dow_${dow}_${shiftId}_$roleId';
    return _requirementCounts[key] ?? 0;
  }

  void _setCount(DateTime? date, int? dow, int shiftId, int roleId, int count) {
    final key = date != null ? '${date.toIso8601String().split('T')[0]}_${shiftId}_$roleId' : 'dow_${dow}_${shiftId}_$roleId';
    setState(() {
      if (count > 0) _requirementCounts[key] = count;
      else _requirementCounts.remove(key);
    });
  }

  @override
  Widget build(BuildContext context) {
    final rolesAsync = ref.watch(rolesProvider);
    final shiftsAsync = ref.watch(shiftsProvider);
    final weekDays = List.generate(7, (i) => _selectedWeekStart.add(Duration(days: i)));

    return rolesAsync.when(
      data: (roles) => shiftsAsync.when(
        data: (shifts) => SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
               SegmentedButton<bool>(
                  segments: const [
                    ButtonSegment(value: false, label: Text('Daty'), icon: Icon(Icons.calendar_month)),
                    ButtonSegment(value: true, label: Text('Tygodniowe'), icon: Icon(Icons.repeat)),
                  ],
                  selected: {_isWeeklyMode},
                  onSelectionChanged: (s) => setState(() => _isWeeklyMode = s.first),
               ),
               const SizedBox(height: 16),
               if (!_isWeeklyMode)
                 Row(
                   mainAxisAlignment: MainAxisAlignment.spaceBetween,
                   children: [
                     IconButton(icon: const Icon(Icons.chevron_left), onPressed: () { setState(() => _selectedWeekStart = _selectedWeekStart.subtract(const Duration(days: 7))); _loadRequirements(); }),
                     Text('${DateFormat('d MMM').format(_selectedWeekStart)} - ${DateFormat('d MMM').format(_selectedWeekEnd)}', style: const TextStyle(fontWeight: FontWeight.bold)),
                     IconButton(icon: const Icon(Icons.chevron_right), onPressed: () { setState(() => _selectedWeekStart = _selectedWeekStart.add(const Duration(days: 7))); _loadRequirements(); }),
                   ],
                 ),
               const SizedBox(height: 16),
               Card(
                 child: SingleChildScrollView(
                   scrollDirection: Axis.horizontal,
                   padding: const EdgeInsets.all(16),
                   child: Column(
                     crossAxisAlignment: CrossAxisAlignment.start,
                     children: [
                       Row(
                         children: [
                           const SizedBox(width: 100, child: Text('Zmiana', style: TextStyle(fontWeight: FontWeight.bold))),
                           ...(_isWeeklyMode ? List.generate(7, (i) => i) : weekDays).map((d) => SizedBox(
                             width: 60,
                             child: Center(child: Text(_isWeeklyMode ? ['Pn','Wt','Śr','Cz','Pt','Sb','Nd'][d as int] : DateFormat('EE dd').format(d as DateTime), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                           )),
                         ],
                       ),
                       const Divider(),
                       ...shifts.map((shift) => Column(
                         crossAxisAlignment: CrossAxisAlignment.start,
                         children: [
                           Text(shift.name, style: const TextStyle(fontWeight: FontWeight.w600)),
                           ...roles.map((role) => Row(
                             children: [
                               SizedBox(width: 100, child: Text(role.name, style: const TextStyle(fontSize: 12), overflow: TextOverflow.ellipsis)),
                               ...(_isWeeklyMode ? List.generate(7, (i) => i) : weekDays).map((d) {
                                  final count = _isWeeklyMode ? _getCount(null, d as int, shift.id, role.id) : _getCount(d as DateTime, null, shift.id, role.id);
                                  return SizedBox(
                                    width: 60,
                                    child: Center(
                                      child: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          InkWell(onTap: () => _setCount(_isWeeklyMode ? null : d as DateTime, _isWeeklyMode ? d as int : null, shift.id, role.id, count - 1), child: const Icon(Icons.remove, size: 16)),
                                          Text('$count', style: const TextStyle(fontWeight: FontWeight.bold)),
                                          InkWell(onTap: () => _setCount(_isWeeklyMode ? null : d as DateTime, _isWeeklyMode ? d as int : null, shift.id, role.id, count + 1), child: const Icon(Icons.add, size: 16)),
                                        ],
                                      ),
                                    ),
                                  );
                               }),
                             ],
                           )),
                           const Divider(),
                         ],
                       )),
                     ],
                   ),
                 ),
               ),
               const SizedBox(height: 16),
               SizedBox(width: double.infinity, child: ElevatedButton.icon(onPressed: _saveRequirements, icon: const Icon(Icons.save), label: const Text('Zapisz wymagania'))),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, s) => Text('Błąd: $e'),
      ),
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, s) => Text('Błąd: $e'),
    );
  }
}
