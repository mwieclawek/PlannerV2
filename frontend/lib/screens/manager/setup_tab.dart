import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import '../../models/models.dart';

class SetupTab extends ConsumerStatefulWidget {
  const SetupTab({super.key});

  @override
  ConsumerState<SetupTab> createState() => _SetupTabState();
}

class _SetupTabState extends ConsumerState<SetupTab> {
  final _roleNameController = TextEditingController();
  int _roleColorIndex = 0; // For auto-color generation
  final _shiftNameController = TextEditingController();
  final _shiftStartController = TextEditingController();
  final _shiftEndController = TextEditingController();
  
  // Restaurant config controllers
  final _restaurantNameController = TextEditingController();
  final _openingHoursController = TextEditingController();
  final _closingHoursController = TextEditingController();
  final _addressController = TextEditingController();
  bool _isLoadingConfig = true;
  bool _isSavingConfig = false;
  
  // Shift applicable days selector (0=Mon, 6=Sun)
  List<int> _selectedDays = [0, 1, 2, 3, 4, 5, 6]; // Default: all days

  @override
  void initState() {
    super.initState();
    _loadConfig();
  }

  Future<void> _loadConfig() async {
    try {
      final config = await ref.read(apiServiceProvider).getConfig();
      setState(() {
        _restaurantNameController.text = config['name'] ?? '';
        _addressController.text = config['address'] ?? '';
        // Parse opening_hours JSON if present
        final hours = config['opening_hours'] ?? '';
        if (hours.isNotEmpty) {
          // Simple format: "08:00-22:00"
          if (hours.contains('-')) {
            final parts = hours.split('-');
            if (parts.length == 2) {
              _openingHoursController.text = parts[0].trim();
              _closingHoursController.text = parts[1].trim();
            }
          }
        }
        _isLoadingConfig = false;
      });
    } catch (e) {
      setState(() => _isLoadingConfig = false);
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
      setState(() => _isSavingConfig = false);
    }
  }

  @override
  void dispose() {
    _roleNameController.dispose();
    _shiftNameController.dispose();
    _shiftStartController.dispose();
    _shiftEndController.dispose();
    _restaurantNameController.dispose();
    _openingHoursController.dispose();
    _closingHoursController.dispose();
    _addressController.dispose();
    super.dispose();
  }

 String _generateRoleColor() {
    // Generate pleasant colors using golden ratio
    final hue = (_roleColorIndex * 137.508) % 360; // Golden angle
    final saturation = 0.65 + (_roleColorIndex % 3) * 0.1; // Vary saturation
    final lightness = 0.50 + (_roleColorIndex % 2) * 0.05; // Vary lightness
    
    // Convert HSL to RGB
    final c = (1 - (2 * lightness - 1).abs()) * saturation;
    final x = c * (1 - ((hue / 60) % 2 - 1).abs());
    final m = lightness - c / 2;
    
    double r = 0, g = 0, b = 0;
    if (hue < 60) {
      r = c; g = x;
    } else if (hue < 120) {
      r = x; g = c;
    } else if (hue < 180) {
      g = c; b = x;
    } else if (hue < 240) {
      g = x; b = c;
    } else if (hue < 300) {
      r = x; b = c;
    } else {
      r = c; b = x;
    }
    
    final red = ((r + m) * 255).round();
    final green = ((g + m) * 255).round();
    final blue = ((b + m) * 255).round();
    
    _roleColorIndex++;
    return '#${red.toRadixString(16).padLeft(2, '0')}${green.toRadixString(16).padLeft(2, '0')}${blue.toRadixString(16).padLeft(2, '0')}'.toUpperCase();
  }

  Future<void> _addRole() async {
    if (_roleNameController.text.isEmpty) return;

    final autoColor = _generateRoleColor();

    try {
      await ref.read(apiServiceProvider).createRole(
            _roleNameController.text,
            autoColor,
          );
      
      _roleNameController.clear();
      ref.invalidate(rolesProvider);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✓ Rola dodana')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  Future<void> _addShift() async {
    if (_shiftNameController.text.isEmpty ||
        _shiftStartController.text.isEmpty ||
        _shiftEndController.text.isEmpty) return;

    // Validate for duplicate times
    final existingShifts = ref.read(shiftsProvider).value ?? [];
    final newStart = _shiftStartController.text.trim();
    final newEnd = _shiftEndController.text.trim();
    
    final duplicate = existingShifts.any((s) => 
      s.startTime == newStart && s.endTime == newEnd
    );
    
    if (duplicate) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: const Text('Taka zmiana już istnieje (te same godziny)'),
            backgroundColor: Colors.orange.shade600,
          ),
        );
      }
      return;
    }

    try {
      await ref.read(apiServiceProvider).createShift(
            _shiftNameController.text,
            newStart,
            newEnd,
            applicableDays: _selectedDays,
          );
      
      _shiftNameController.clear();
      _shiftStartController.clear();
      _shiftEndController.clear();
      setState(() => _selectedDays = [0, 1, 2, 3, 4, 5, 6]); // Reset to all days
      ref.invalidate(shiftsProvider);
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('✓ Zmiana dodana')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e')),
        );
      }
    }
  }

  Future<void> _showEditRoleDialog(JobRole role) async {
    final nameController = TextEditingController(text: role.name);
    final colorController = TextEditingController(text: role.colorHex);
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edytuj rolę'),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Nazwa roli',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: colorController,
                decoration: const InputDecoration(
                  labelText: 'Kolor (hex)',
                  border: OutlineInputBorder(),
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(apiServiceProvider).updateRole(
          role.id,
          nameController.text,
          colorController.text,
        );
        ref.invalidate(rolesProvider);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('✓ Zaktualizowano rolę "${nameController.text}"')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red.shade600),
          );
        }
      }
    }
  }

  Future<void> _confirmDeleteRole(JobRole role) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Usuń rolę'),
        content: Text('Czy na pewno chcesz usunąć rolę "${role.name}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Usuń'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(apiServiceProvider).deleteRole(role.id);
        ref.invalidate(rolesProvider);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Usunięto rolę "${role.name}"'), backgroundColor: Colors.orange.shade600),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red.shade600),
          );
        }
      }
    }
  }

  Future<void> _showEditShiftDialog(ShiftDefinition shift) async {
    final nameController = TextEditingController(text: shift.name);
    final startController = TextEditingController(text: shift.startTime);
    final endController = TextEditingController(text: shift.endTime);
    
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Edytuj zmianę'),
        content: SizedBox(
          width: 300,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: nameController,
                decoration: const InputDecoration(
                  labelText: 'Nazwa zmiany',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: startController,
                      decoration: const InputDecoration(
                        labelText: 'Start',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: endController,
                      decoration: const InputDecoration(
                        labelText: 'Koniec',
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Zapisz'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(apiServiceProvider).updateShift(
          shift.id,
          nameController.text,
          startController.text,
          endController.text,
        );
        ref.invalidate(shiftsProvider);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('✓ Zaktualizowano zmianę "${nameController.text}"')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red.shade600),
          );
        }
      }
    }
  }

  Future<void> _confirmDeleteShift(ShiftDefinition shift) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Usuń zmianę'),
        content: Text('Czy na pewno chcesz usunąć zmianę "${shift.name}"?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Anuluj')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Usuń'),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await ref.read(apiServiceProvider).deleteShift(shift.id);
        ref.invalidate(shiftsProvider);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Usunięto zmianę "${shift.name}"'), backgroundColor: Colors.orange.shade600),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red.shade600),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final rolesAsync = ref.watch(rolesProvider);
    final shiftsAsync = ref.watch(shiftsProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Restaurant Section
          Text(
            'Restauracja',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
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
                                  labelText: 'Godziny otwarcia (od)',
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
                                  labelText: 'Godziny otwarcia (do)',
                                  hintText: '22:00',
                                  border: OutlineInputBorder(),
                                  prefixIcon: Icon(Icons.access_time),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 16),
                        Align(
                          alignment: Alignment.centerRight,
                          child: ElevatedButton.icon(
                            onPressed: _isSavingConfig ? null : _saveConfig,
                            icon: _isSavingConfig
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.save),
                            label: Text(_isSavingConfig ? 'Zapisywanie...' : 'Zapisz'),
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
          
          const SizedBox(height: 32),
          
          // Roles Section
          Text(
            'Role / Stanowiska',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Dodaj nową rolę',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _roleNameController,
                          decoration: InputDecoration(
                            labelText: 'Nazwa roli',
                            hintText: 'np. Barista, Kucharz',
                            border: const OutlineInputBorder(),
                            helperText: 'Kolor zostanie przypisany automatycznie',
                            helperStyle: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton.icon(
                        onPressed: _addRole,
                        icon: const Icon(Icons.add),
                        label: const Text('Dodaj'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo.shade700,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 20,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  rolesAsync.when(
                    data: (roles) {
                      if (roles.isEmpty) {
                        return const Text('Brak zdefiniowanych ról');
                      }
                      return Column(
                        children: roles.map((role) {
                          return ListTile(
                            leading: Container(
                              width: 24,
                              height: 24,
                              decoration: BoxDecoration(
                                color: _parseColor(role.colorHex),
                                borderRadius: BorderRadius.circular(4),
                              ),
                            ),
                            title: Text(role.name),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: Icon(Icons.edit_outlined, color: Colors.blue.shade400),
                                  onPressed: () => _showEditRoleDialog(role),
                                  tooltip: 'Edytuj',
                                ),
                                IconButton(
                                  icon: Icon(Icons.delete_outline, color: Colors.red.shade400),
                                  onPressed: () => _confirmDeleteRole(role),
                                  tooltip: 'Usuń',
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      );
                    },
                    loading: () => const CircularProgressIndicator(),
                    error: (e, s) => Text('Błąd: $e'),
                  ),
                ],
              ),
            ),
          ),
          
          const SizedBox(height: 32),
          
          // Shifts Section
          Text(
            'Zmiany',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Dodaj nową zmianę',
                    style: GoogleFonts.inter(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Uwaga: Godziny zmiany muszą być unikalne (kluczem nie jest nazwa)',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        flex: 2,
                        child: TextField(
                          controller: _shiftNameController,
                          decoration: const InputDecoration(
                            labelText: 'Nazwa zmiany',
                            hintText: 'np. Poranna, Popołudniowa',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _shiftStartController,
                          decoration: const InputDecoration(
                            labelText: 'Start (HH:MM)',
                            hintText: '08:00',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: _shiftEndController,
                          decoration: const InputDecoration(
                            labelText: 'Koniec (HH:MM)',
                            hintText: '16:00',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton.icon(
                        onPressed: _addShift,
                        icon: const Icon(Icons.add),
                        label: const Text('Dodaj'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo.shade700,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 24,
                            vertical: 20,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  // Weekday selector
                  Row(
                    children: [
                      Text(
                        'Dni tygodnia: ',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Wrap(
                          spacing: 6,
                          runSpacing: 4,
                          children: [
                            for (int i = 0; i < 7; i++)
                              FilterChip(
                                label: Text(
                                  ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'][i],
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: _selectedDays.contains(i) ? Colors.white : Colors.grey.shade700,
                                  ),
                                ),
                                selected: _selectedDays.contains(i),
                                onSelected: (selected) {
                                  setState(() {
                                    if (selected) {
                                      _selectedDays.add(i);
                                      _selectedDays.sort();
                                    } else {
                                      _selectedDays.remove(i);
                                    }
                                  });
                                },
                                selectedColor: Colors.indigo.shade600,
                                checkmarkColor: Colors.white,
                                backgroundColor: Colors.grey.shade200,
                              ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  shiftsAsync.when(
                    data: (shifts) {
                      if (shifts.isEmpty) {
                        return const Text('Brak zdefiniowanych zmian');
                      }
                      return Column(
                        children: shifts.map((shift) {
                          return ListTile(
                            leading: const Icon(Icons.schedule),
                            title: Text(shift.name),
                            subtitle: Text(
                              '${shift.startTime} - ${shift.endTime}  •  ${_formatDays(shift.applicableDays)}'
                            ),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                IconButton(
                                  icon: Icon(Icons.edit_outlined, color: Colors.blue.shade400),
                                  onPressed: () => _showEditShiftDialog(shift),
                                  tooltip: 'Edytuj',
                                ),
                                IconButton(
                                  icon: Icon(Icons.delete_outline, color: Colors.red.shade400),
                                  onPressed: () => _confirmDeleteShift(shift),
                                  tooltip: 'Usuń',
                                ),
                              ],
                            ),
                          );
                        }).toList(),
                      );
                    },
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

  Color _parseColor(String hex) {
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (e) {
      return Colors.blue;
    }
  }

  String _formatDays(List<int> days) {
    if (days.length == 7) return 'Codziennie';
    if (days.isEmpty) return 'Brak dni';
    const dayNames = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'Sb', 'Nd'];
    return days.map((d) => dayNames[d]).join(', ');
  }
}
