import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class EmployeeOperationsTab extends StatefulWidget {
  const EmployeeOperationsTab({super.key});

  @override
  State<EmployeeOperationsTab> createState() => _EmployeeOperationsTabState();
}

class _EmployeeOperationsTabState extends State<EmployeeOperationsTab>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: colorScheme.primary,
            unselectedLabelColor: colorScheme.onSurfaceVariant,
            indicatorColor: colorScheme.primary,
            tabs: const [
              Tab(
                text: 'Checklisty i HACCP',
                icon: Icon(Icons.assignment_turned_in_outlined),
              ),
              Tab(text: 'Tablica Ogłoszeń', icon: Icon(Icons.campaign_outlined)),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [
              _EmployeeChecklistsHaccpSubTab(),
              _EmployeeAnnouncementsSubTab(),
            ],
          ),
        ),
      ],
    );
  }
}

// ============================================================================
// SUB-TAB 1: EMPLOYEE CHECKLISTS & HACCP LOGGING
// ============================================================================

class _EmployeeChecklistsHaccpSubTab extends ConsumerStatefulWidget {
  const _EmployeeChecklistsHaccpSubTab();

  @override
  ConsumerState<_EmployeeChecklistsHaccpSubTab> createState() =>
      _EmployeeChecklistsHaccpSubTabState();
}

class _EmployeeChecklistsHaccpSubTabState
    extends ConsumerState<_EmployeeChecklistsHaccpSubTab> {
  List<ChecklistTemplateModel> _checklists = [];
  List<HaccpDeviceModel> _devices = [];
  List<HaccpLogModel> _logs = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiServiceProvider);
      final results = await Future.wait([
        api.getEmployeeChecklists(date: DateTime.now()),
        api.getHaccpDevices(isManager: false),
        api.getHaccpLogs(
          isManager: false,
          startDate: DateTime.now().subtract(const Duration(days: 7)),
          endDate: DateTime.now(),
        ),
      ]);
      if (mounted) {
        setState(() {
          _checklists = results[0] as List<ChecklistTemplateModel>;
          _devices = results[1] as List<HaccpDeviceModel>;
          _logs = results[2] as List<HaccpLogModel>;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showAddTemperatureDialog() {
    if (_devices.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Brak zdefiniowanych urządzeń chłodniczych HACCP.'),
        ),
      );
      return;
    }
    HaccpDeviceModel selectedDevice = _devices.first;
    final tempCtrl = TextEditingController();
    final correctiveCtrl = TextEditingController();

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder: (ctx, setDialogState) {
              final tempVal = double.tryParse(
                tempCtrl.text.replaceAll(',', '.'),
              );
              final isOut =
                  tempVal != null &&
                  (tempVal < selectedDevice.minTemp ||
                      tempVal > selectedDevice.maxTemp);

              return AlertDialog(
                title: const Text('Pomiar temperatury (HACCP)'),
                content: SizedBox(
                  width: 360,
                  child: SingleChildScrollView(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        DropdownButtonFormField<HaccpDeviceModel>(
                          value: selectedDevice,
                          decoration: const InputDecoration(
                            labelText: 'Urządzenie chłodnicze',
                            border: OutlineInputBorder(),
                          ),
                          items:
                              _devices
                                  .map(
                                    (d) => DropdownMenuItem(
                                      value: d,
                                      child: Text(
                                        '${d.name} (${d.minTemp}..${d.maxTemp} °C)',
                                      ),
                                    ),
                                  )
                                  .toList(),
                          onChanged:
                              (v) => setDialogState(() => selectedDevice = v!),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: tempCtrl,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          decoration: const InputDecoration(
                            labelText: 'Odczyt temperatury (°C)',
                            prefixIcon: Icon(Icons.thermostat),
                            border: OutlineInputBorder(),
                          ),
                          onChanged: (_) => setDialogState(() {}),
                        ),
                        if (isOut) ...[
                          const SizedBox(height: 12),
                          Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: Colors.red.shade50,
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.red.shade300),
                            ),
                            child: Text(
                              'UWAGA: Temperatura poza normą (${selectedDevice.minTemp}..${selectedDevice.maxTemp} °C)! Wymagane jest działanie korygujące – manager zostanie automatycznie powiadomiony.',
                              style: TextStyle(
                                color: Colors.red.shade800,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                          const SizedBox(height: 12),
                          TextField(
                            controller: correctiveCtrl,
                            onChanged: (_) => setDialogState(() {}),
                            decoration: InputDecoration(
                              labelText: 'Działanie korygujące *',
                              hintText: 'np. Regulacja termostatu / serwis',
                              border: const OutlineInputBorder(),
                              errorText:
                                  correctiveCtrl.text.trim().isEmpty
                                      ? 'Wymagane przy przekroczeniu normy'
                                      : null,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: const Text('Anuluj'),
                  ),
                  FilledButton(
                    onPressed: () async {
                      if (tempVal == null) return;
                      if (isOut && correctiveCtrl.text.trim().isEmpty) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(
                            content: Text(
                              'Przekroczono bezpieczny zakres temperatury! Podaj działanie korygujące.',
                            ),
                            backgroundColor: Colors.red,
                          ),
                        );
                        return;
                      }
                      await ref
                          .read(apiServiceProvider)
                          .createHaccpLog(
                            isManager: false,
                            logType: 'TEMPERATURE',
                            deviceId: selectedDevice.id,
                            deviceName: selectedDevice.name,
                            measuredTemp: tempVal,
                            correctiveAction:
                                correctiveCtrl.text.trim().isEmpty
                                    ? null
                                    : correctiveCtrl.text.trim(),
                          );
                      if (ctx.mounted) {
                        Navigator.pop(ctx);
                        _loadData();
                      }
                    },
                    child: const Text('Zapisz i podpisz'),
                  ),
                ],
              );
            },
          ),
    );
  }

  void _showAddSanitationDialog() {
    final areaCtrl = TextEditingController();
    final notesCtrl = TextEditingController();

    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Karta Higieny i Mycia (HACCP)'),
            content: SizedBox(
              width: 360,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: areaCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Strefa / urządzenie (np. Krajalnica, Bar)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: notesCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Zastosowany środek / uwagi',
                      border: OutlineInputBorder(),
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: () async {
                  if (areaCtrl.text.trim().isEmpty) return;
                  await ref
                      .read(apiServiceProvider)
                      .createHaccpLog(
                        isManager: false,
                        logType: 'SANITATION',
                        deviceName: areaCtrl.text.trim(),
                        correctiveAction:
                            notesCtrl.text.trim().isEmpty
                                ? null
                                : notesCtrl.text.trim(),
                      );
                  if (ctx.mounted) {
                    Navigator.pop(ctx);
                    _loadData();
                  }
                },
                child: const Text('Zapisz i podpisz'),
              ),
            ],
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    return RefreshIndicator(
      onRefresh: _loadData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Checklisty zmiany (Dzisiaj)',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          if (_checklists.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('Brak aktywnych checklist na dzisiaj.'),
              ),
            )
          else
            ..._checklists.map(
              (tpl) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ExpansionTile(
                  initiallyExpanded: true,
                  title: Text(
                    '${tpl.title} (${tpl.shiftPeriod == 'OPENING' ? 'Otwarcie zmiany' : 'Zamknięcie zmiany'})',
                    style: GoogleFonts.inter(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text(
                    'Ukończono: ${tpl.items.where((i) => i.isCompleted).length} / ${tpl.items.length}',
                  ),
                  children:
                      tpl.items
                          .map(
                            (item) => CheckboxListTile(
                              value: item.isCompleted,
                              title: Text(
                                item.title,
                                style: TextStyle(
                                  decoration:
                                      item.isCompleted
                                          ? TextDecoration.lineThrough
                                          : null,
                                ),
                              ),
                              subtitle:
                                  item.isCompleted
                                      ? Text(
                                        'Wykonał(a): ${item.completedByUserName ?? ''}',
                                        style: const TextStyle(
                                          color: Colors.green,
                                          fontSize: 11,
                                        ),
                                      )
                                      : (item.isMandatory
                                          ? const Text(
                                            'Wymagane przed wyjściem (Clock-out)',
                                            style: TextStyle(
                                              color: Colors.orange,
                                              fontSize: 11,
                                            ),
                                          )
                                          : null),
                              onChanged: (val) async {
                                await ref
                                    .read(apiServiceProvider)
                                    .toggleChecklistItem(
                                      item.id,
                                      date: DateTime.now(),
                                      isCompleted: val ?? false,
                                    );
                                _loadData();
                              },
                            ),
                          )
                          .toList(),
                ),
              ),
            ),

          const SizedBox(height: 24),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            alignment: WrapAlignment.spaceBetween,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                'Karty Kontroli HACCP',
                style: GoogleFonts.outfit(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Wrap(
                spacing: 8,
                children: [
                  FilledButton.tonalIcon(
                    onPressed: _showAddTemperatureDialog,
                    icon: const Icon(Icons.thermostat, size: 18),
                    label: const Text('+ Temperatura'),
                  ),
                  OutlinedButton.icon(
                    onPressed: _showAddSanitationDialog,
                    icon: const Icon(Icons.cleaning_services, size: 18),
                    label: const Text('+ Higiena'),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_logs.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('Brak ostatnich wpisów HACCP.'),
              ),
            )
          else
            ..._logs.take(15).map((log) {
              final violated = !log.isWithinNorm;
              return Card(
                color: violated ? Colors.red.shade50 : null,
                margin: const EdgeInsets.only(bottom: 8),
                child: ListTile(
                  leading: Icon(
                    violated
                        ? Icons.warning_amber_rounded
                        : Icons.verified_user_outlined,
                    color: violated ? Colors.red.shade800 : Colors.green,
                  ),
                  title: Text(
                    log.logType == 'TEMPERATURE'
                        ? '${log.deviceName}: ${log.measuredTemp?.toStringAsFixed(1) ?? '-'} °C'
                        : 'Higiena: ${log.deviceName}',
                    style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    'Podpis: ${log.userName} • ${DateFormat('dd.MM HH:mm').format(log.createdAt.toLocal())}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}

// ============================================================================
// SUB-TAB 2: EMPLOYEE ANNOUNCEMENT BOARD WITH READ CONFIRMATION
// ============================================================================

class _EmployeeAnnouncementsSubTab extends ConsumerStatefulWidget {
  const _EmployeeAnnouncementsSubTab();

  @override
  ConsumerState<_EmployeeAnnouncementsSubTab> createState() =>
      _EmployeeAnnouncementsSubTabState();
}

class _EmployeeAnnouncementsSubTabState
    extends ConsumerState<_EmployeeAnnouncementsSubTab> {
  List<AnnouncementModel> _announcements = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadAnnouncements();
  }

  Future<void> _loadAnnouncements() async {
    setState(() => _loading = true);
    try {
      final list =
          await ref.read(apiServiceProvider).getEmployeeAnnouncements();
      if (mounted) {
        list.sort((a, b) {
          if (a.isRead != b.isRead) {
            return a.isRead ? 1 : -1;
          }
          if (a.isPinned != b.isPinned) {
            return a.isPinned ? -1 : 1;
          }
          return b.createdAt.compareTo(a.createdAt);
        });
        setState(() {
          _announcements = list;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    return RefreshIndicator(
      onRefresh: _loadAnnouncements,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(
            'Komunikaty i Ogłoszenia',
            style: GoogleFonts.outfit(
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          if (_announcements.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: Text('Brak ogłoszeń na tablicy.')),
              ),
            )
          else
            ..._announcements.map((ann) {
              final unread = !ann.isRead;
              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                  side:
                      unread
                          ? BorderSide(color: colorScheme.primary, width: 1.8)
                          : BorderSide.none,
                ),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (unread)
                            Container(
                              margin: const EdgeInsets.only(right: 8),
                              padding: const EdgeInsets.symmetric(
                                horizontal: 8,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: colorScheme.primary,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: const Text(
                                'NOWE',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                            ),
                          Expanded(
                            child: Text(
                              ann.title,
                              style: GoogleFonts.outfit(
                                fontSize: 17,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(ann.content),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '${ann.authorName} • ${DateFormat('dd.MM.yyyy HH:mm').format(ann.createdAt.toLocal())}',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade600,
                            ),
                          ),
                          if (unread)
                            FilledButton.icon(
                              onPressed: () async {
                                await ref
                                    .read(apiServiceProvider)
                                    .markAnnouncementRead(ann.id);
                                _loadAnnouncements();
                              },
                              icon: const Icon(Icons.done_all, size: 16),
                              label: const Text('Zapoznałem się'),
                            )
                          else
                            Chip(
                              visualDensity: VisualDensity.compact,
                              avatar: const Icon(
                                Icons.check_circle,
                                color: Colors.green,
                                size: 16,
                              ),
                              label: const Text(
                                'Zapoznano się',
                                style: TextStyle(fontSize: 11),
                              ),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }
}
