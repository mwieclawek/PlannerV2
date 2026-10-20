import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../models/models.dart';
import '../../providers/providers.dart';

class OperationsHubTab extends ConsumerStatefulWidget {
  const OperationsHubTab({super.key});

  @override
  ConsumerState<OperationsHubTab> createState() => _OperationsHubTabState();
}

class _OperationsHubTabState extends ConsumerState<OperationsHubTab>
    with SingleTickerProviderStateMixin {
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
    final colorScheme = Theme.of(context).colorScheme;
    final tipPoolEnabled =
        ref.watch(tipPoolEnabledProvider).valueOrNull ?? true;
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: colorScheme.primary,
            unselectedLabelColor: colorScheme.onSurfaceVariant,
            indicatorColor: colorScheme.primary,
            tabs: [
              Tab(
                text: tipPoolEnabled ? 'Płace i Tip Pool' : 'Płace i Koszty',
                icon: const Icon(Icons.payments_outlined),
              ),
              const Tab(
                text: 'Checklisty i HACCP',
                icon: Icon(Icons.assignment_turned_in_outlined),
              ),
              const Tab(
                text: 'Ogłoszenia',
                icon: Icon(Icons.campaign_outlined),
              ),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            children: const [
              _PayrollSubTab(),
              _ChecklistsAndHaccpSubTab(),
              _ManagerAnnouncementsSubTab(),
            ],
          ),
        ),
      ],
    );
  }
}

// ============================================================================
// SUB-TAB 1: PAYROLL, LABOR COST & TIP POOL
// ============================================================================

class _PayrollSubTab extends ConsumerStatefulWidget {
  const _PayrollSubTab();

  @override
  ConsumerState<_PayrollSubTab> createState() => _PayrollSubTabState();
}

class _PayrollSubTabState extends ConsumerState<_PayrollSubTab> {
  DateTime _selectedMonth = DateTime(DateTime.now().year, DateTime.now().month);
  MonthlyPayrollSummary? _summary;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadPayroll();
  }

  Future<void> _loadPayroll() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ref
          .read(apiServiceProvider)
          .getMonthlyPayroll(_selectedMonth.year, _selectedMonth.month);
      if (mounted) {
        setState(() {
          _summary = data;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _loading = false;
        });
      }
    }
  }

  Future<void> _exportCsv() async {
    final api = ref.read(apiServiceProvider);
    final token = await api.getToken();
    final url = api.getPayrollExportCsvUrl(
      _selectedMonth.year,
      _selectedMonth.month,
      token: token,
    );
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  Future<void> _exportPdf() async {
    final api = ref.read(apiServiceProvider);
    final token = await api.getToken();
    final url = api.getPayrollExportPdfUrl(
      _selectedMonth.year,
      _selectedMonth.month,
      token: token,
    );
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  void _showEditHourlyRateDialog(PayrollEmployeeItem item) {
    final controller = TextEditingController(
      text: item.hourlyRate > 0 ? item.hourlyRate.toStringAsFixed(2) : '',
    );
    bool saving = false;

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder:
                (ctx, setDialogState) => AlertDialog(
                  title: Text('Stawka godzinowa: ${item.userName}'),
                  content: SizedBox(
                    width: 340,
                    child: TextField(
                      controller: controller,
                      autofocus: true,
                      keyboardType: const TextInputType.numberWithOptions(
                        decimal: true,
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Stawka godzinowa (PLN/h)',
                        hintText: 'np. 30.50',
                        prefixIcon: Icon(Icons.payments_outlined),
                        border: OutlineInputBorder(),
                      ),
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: saving ? null : () => Navigator.pop(ctx),
                      child: const Text('Anuluj'),
                    ),
                    FilledButton(
                      onPressed:
                          saving
                              ? null
                              : () async {
                                final raw =
                                    controller.text
                                        .replaceAll(',', '.')
                                        .trim();
                                final parsed = double.tryParse(raw);
                                setDialogState(() => saving = true);
                                try {
                                  await ref
                                      .read(apiServiceProvider)
                                      .updateUser(
                                        item.userId,
                                        hourlyRate: parsed,
                                        clearHourlyRate: raw.isEmpty,
                                      );
                                  if (ctx.mounted) {
                                    Navigator.pop(ctx);
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text(
                                          'Zaktualizowano stawkę dla ${item.userName}',
                                        ),
                                        backgroundColor: Colors.green,
                                      ),
                                    );
                                    _loadPayroll();
                                  }
                                } catch (e) {
                                  setDialogState(() => saving = false);
                                  if (ctx.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('Błąd: $e'),
                                        backgroundColor: Colors.red,
                                      ),
                                    );
                                  }
                                }
                              },
                      child: const Text('Zapisz'),
                    ),
                  ],
                ),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = Theme.of(context).colorScheme;
    final tipPoolEnabled =
        ref.watch(tipPoolEnabledProvider).valueOrNull ?? true;
    return RefreshIndicator(
      onRefresh: _loadPayroll,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.chevron_left),
                      onPressed: () {
                        setState(() {
                          _selectedMonth = DateTime(
                            _selectedMonth.year,
                            _selectedMonth.month - 1,
                          );
                        });
                        _loadPayroll();
                      },
                    ),
                    Text(
                      DateFormat('MMMM yyyy', 'pl_PL').format(_selectedMonth),
                      style: GoogleFonts.outfit(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.chevron_right),
                      onPressed: () {
                        setState(() {
                          _selectedMonth = DateTime(
                            _selectedMonth.year,
                            _selectedMonth.month + 1,
                          );
                        });
                        _loadPayroll();
                      },
                    ),
                  ],
                ),
                Wrap(
                  spacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: _exportCsv,
                      icon: const Icon(Icons.table_view, size: 18),
                      label: const Text('Eksport CSV'),
                    ),
                    FilledButton.icon(
                      onPressed: _exportPdf,
                      icon: const Icon(Icons.picture_as_pdf, size: 18),
                      label: const Text('Eksport PDF'),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 16),
            if (_loading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (_error != null)
              Center(child: Text('Błąd: $_error'))
            else if (_summary != null) ...[
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _kpiCard(
                    title: 'Koszt pracy (baza)',
                    value: '${_summary!.totalBasePay.toStringAsFixed(2)} PLN',
                    icon: Icons.badge_outlined,
                    color: colorScheme.primary,
                  ),
                  if (tipPoolEnabled)
                    _kpiCard(
                      title: 'Pula napiwków (Tip Pool)',
                      value: '${_summary!.totalTips.toStringAsFixed(2)} PLN',
                      icon: Icons.volunteer_activism_outlined,
                      color: Colors.teal,
                    ),
                  _kpiCard(
                    title: 'Utarg miesięczny',
                    value:
                        '${_summary!.totalMonthlyRevenue.toStringAsFixed(2)} PLN',
                    icon: Icons.point_of_sale_outlined,
                    color: Colors.indigo,
                  ),
                  _kpiCard(
                    title: 'Labor Cost %',
                    value:
                        _summary!.totalMonthlyRevenue > 0
                            ? '${_summary!.monthlyLaborCostPct.toStringAsFixed(1)}%'
                            : 'Brak utargu',
                    icon: Icons.pie_chart_outline,
                    color:
                        _summary!.monthlyLaborCostPct > 35
                            ? Colors.red
                            : Colors.green,
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text(
                'Zestawienie płacowe zespołu',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 8),
              ..._summary!.items.map(
                (item) => Card(
                  margin: const EdgeInsets.only(bottom: 10),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor: colorScheme.primaryContainer,
                      child: Text(
                        item.userName.isNotEmpty
                            ? item.userName[0].toUpperCase()
                            : '?',
                        style: TextStyle(
                          color: colorScheme.onPrimaryContainer,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                    title: Text(
                      item.userName,
                      style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Wrap(
                      crossAxisAlignment: WrapCrossAlignment.center,
                      spacing: 8,
                      runSpacing: 4,
                      children: [
                        Text(
                          'Zatwierdzone: ${item.confirmedHours.toStringAsFixed(2)}h • Oczekujące: ${item.pendingHours.toStringAsFixed(2)}h • Stawka: ${item.hourlyRate.toStringAsFixed(2)} PLN/h',
                          style: const TextStyle(fontSize: 12),
                        ),
                        InkWell(
                          onTap: () => _showEditHourlyRateDialog(item),
                          borderRadius: BorderRadius.circular(6),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.edit_outlined,
                                  size: 14,
                                  color: colorScheme.primary,
                                ),
                                const SizedBox(width: 4),
                                Text(
                                  item.hourlyRate > 0
                                      ? 'Zmień stawkę'
                                      : 'Ustaw stawkę',
                                  style: TextStyle(
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                    color: colorScheme.primary,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                    trailing: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          '${(tipPoolEnabled ? item.totalPay : item.basePay).toStringAsFixed(2)} PLN',
                          style: GoogleFonts.outfit(
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                            color: colorScheme.primary,
                          ),
                        ),
                        if (tipPoolEnabled)
                          Text(
                            'Baza: ${item.basePay.toStringAsFixed(2)} + Tip: ${item.allocatedTips.toStringAsFixed(2)}',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade600,
                            ),
                          )
                        else
                          Text(
                            'Wynagrodzenie bazowe',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey.shade600,
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _kpiCard({
    required String title,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return SizedBox(
      width: 210,
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: color.withValues(alpha: 0.12),
                child: Icon(icon, color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: TextStyle(
                        fontSize: 11,
                        color: Colors.grey.shade600,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      value,
                      style: GoogleFonts.outfit(
                        fontSize: 15,
                        fontWeight: FontWeight.bold,
                        color: color,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// SUB-TAB 2: CHECKLISTS & DIGITAL HACCP CARDS
// ============================================================================

class _ChecklistsAndHaccpSubTab extends ConsumerStatefulWidget {
  const _ChecklistsAndHaccpSubTab();

  @override
  ConsumerState<_ChecklistsAndHaccpSubTab> createState() =>
      _ChecklistsAndHaccpSubTabState();
}

class _ChecklistsAndHaccpSubTabState
    extends ConsumerState<_ChecklistsAndHaccpSubTab> {
  List<ChecklistTemplateModel> _dailyChecklists = [];
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
        api.getManagerDailyChecklists(DateTime.now()),
        api.getHaccpDevices(isManager: true),
        api.getHaccpLogs(
          isManager: true,
          startDate: DateTime.now().subtract(const Duration(days: 30)),
          endDate: DateTime.now(),
        ),
      ]);
      if (mounted) {
        setState(() {
          _dailyChecklists = results[0] as List<ChecklistTemplateModel>;
          _devices = results[1] as List<HaccpDeviceModel>;
          _logs = results[2] as List<HaccpLogModel>;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _exportSanepidPdf() async {
    final now = DateTime.now();
    final start = DateTime(now.year, now.month, 1);
    final api = ref.read(apiServiceProvider);
    final token = await api.getToken();
    final url = api.getHaccpExportPdfUrl(start, now, token: token);
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  void _showCreateTemplateDialog() {
    final titleCtrl = TextEditingController();
    String shiftPeriod = 'OPENING';
    bool isMandatory = true;
    final List<Map<String, dynamic>> items = [
      {'title': '', 'is_mandatory': true, 'sort_order': 0},
    ];

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder:
                (ctx, setDialogState) => AlertDialog(
                  title: const Text('Nowy szablon checklisty'),
                  content: SizedBox(
                    width: 420,
                    child: SingleChildScrollView(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          TextField(
                            controller: titleCtrl,
                            decoration: const InputDecoration(
                              labelText: 'Nazwa checklisty',
                              border: OutlineInputBorder(),
                            ),
                          ),
                          const SizedBox(height: 12),
                          DropdownButtonFormField<String>(
                            value: shiftPeriod,
                            decoration: const InputDecoration(
                              labelText: 'Typ zmiany',
                              border: OutlineInputBorder(),
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'OPENING',
                                child: Text('Otwarcie zmiany (OPENING)'),
                              ),
                              DropdownMenuItem(
                                value: 'CLOSING',
                                child: Text('Zamknięcie zmiany (CLOSING)'),
                              ),
                            ],
                            onChanged:
                                (v) => setDialogState(() => shiftPeriod = v!),
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            title: const Text(
                              'Obowiązkowa przed zakończeniem zmiany',
                            ),
                            value: isMandatory,
                            onChanged:
                                (v) => setDialogState(() => isMandatory = v),
                          ),
                          const SizedBox(height: 8),
                          ...items.asMap().entries.map((entry) {
                            final idx = entry.key;
                            final item = entry.value;
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: TextFormField(
                                      initialValue: item['title'] as String,
                                      decoration: InputDecoration(
                                        labelText: 'Zadanie #${idx + 1}',
                                        border: const OutlineInputBorder(),
                                      ),
                                      onChanged: (v) => item['title'] = v,
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Tooltip(
                                    message: 'Obowiązkowe przy wyjściu',
                                    child: Checkbox(
                                      value: item['is_mandatory'] as bool,
                                      onChanged:
                                          (v) => setDialogState(
                                            () =>
                                                item['is_mandatory'] =
                                                    v ?? true,
                                          ),
                                    ),
                                  ),
                                  if (items.length > 1)
                                    IconButton(
                                      icon: const Icon(
                                        Icons.remove_circle_outline,
                                        color: Colors.red,
                                      ),
                                      onPressed:
                                          () => setDialogState(
                                            () => items.removeAt(idx),
                                          ),
                                    ),
                                ],
                              ),
                            );
                          }),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: TextButton.icon(
                              onPressed:
                                  () => setDialogState(
                                    () => items.add({
                                      'title': '',
                                      'is_mandatory': true,
                                      'sort_order': items.length,
                                    }),
                                  ),
                              icon: const Icon(Icons.add),
                              label: const Text('Dodaj pozycję'),
                            ),
                          ),
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
                        final validItems =
                            items
                                .where(
                                  (i) =>
                                      (i['title'] as String).trim().isNotEmpty,
                                )
                                .toList();
                        if (titleCtrl.text.trim().isEmpty ||
                            validItems.isEmpty) {
                          return;
                        }
                        await ref
                            .read(apiServiceProvider)
                            .createChecklistTemplate(
                              title: titleCtrl.text.trim(),
                              shiftPeriod: shiftPeriod,
                              isMandatory: isMandatory,
                              items: validItems,
                            );
                        if (ctx.mounted) {
                          Navigator.pop(ctx);
                          _loadData();
                        }
                      },
                      child: const Text('Utwórz'),
                    ),
                  ],
                ),
          ),
    );
  }

  void _showAddDeviceDialog() {
    final nameCtrl = TextEditingController();
    final minCtrl = TextEditingController(text: '0');
    final maxCtrl = TextEditingController(text: '4');

    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Dodaj urządzenie chłodnicze / punkt HACCP'),
            content: SizedBox(
              width: 360,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: nameCtrl,
                    decoration: const InputDecoration(
                      labelText: 'Nazwa urządzenia (np. Chłodnia 1 - Mięso)',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: minCtrl,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          decoration: const InputDecoration(
                            labelText: 'Min °C',
                            border: OutlineInputBorder(),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: TextField(
                          controller: maxCtrl,
                          keyboardType: const TextInputType.numberWithOptions(
                            decimal: true,
                            signed: true,
                          ),
                          decoration: const InputDecoration(
                            labelText: 'Max °C',
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
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: () async {
                  if (nameCtrl.text.trim().isEmpty) return;
                  await ref
                      .read(apiServiceProvider)
                      .createHaccpDevice(
                        name: nameCtrl.text.trim(),
                        minTemp:
                            double.tryParse(
                              minCtrl.text.replaceAll(',', '.'),
                            ) ??
                            0.0,
                        maxTemp:
                            double.tryParse(
                              maxCtrl.text.replaceAll(',', '.'),
                            ) ??
                            4.0,
                      );
                  if (ctx.mounted) {
                    Navigator.pop(ctx);
                    _loadData();
                  }
                },
                child: const Text('Dodaj'),
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
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'Checklisty operacyjne (Dzisiaj)',
                  style: GoogleFonts.outfit(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                FilledButton.tonalIcon(
                  onPressed: _showCreateTemplateDialog,
                  icon: const Icon(Icons.add_task, size: 18),
                  label: const Text('Nowy szablon'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_dailyChecklists.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Brak zdefiniowanych szablonów checklist.'),
                ),
              )
            else
              ..._dailyChecklists.map(
                (tpl) => Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ExpansionTile(
                    initiallyExpanded: true,
                    title: Text(
                      '${tpl.title} (${tpl.shiftPeriod == 'OPENING' ? 'Otwarcie' : 'Zamknięcie'})',
                      style: GoogleFonts.inter(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Text(
                      'Wykonano: ${tpl.items.where((i) => i.isCompleted).length} / ${tpl.items.length}',
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline, color: Colors.red),
                      onPressed: () async {
                        await ref
                            .read(apiServiceProvider)
                            .deleteChecklistTemplate(tpl.id);
                        _loadData();
                      },
                    ),
                    children:
                        tpl.items
                            .map(
                              (item) => ListTile(
                                dense: true,
                                leading: Icon(
                                  item.isCompleted
                                      ? Icons.check_circle
                                      : Icons.radio_button_unchecked,
                                  color:
                                      item.isCompleted
                                          ? Colors.green
                                          : (item.isMandatory
                                              ? Colors.orange
                                              : Colors.grey),
                                ),
                                title: Text(item.title),
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
                                              'Obowiązkowe przed zakończeniem zmiany',
                                              style: TextStyle(
                                                color: Colors.orange,
                                                fontSize: 11,
                                              ),
                                            )
                                            : null),
                              ),
                            )
                            .toList(),
                  ),
                ),
              ),

            const SizedBox(height: 28),
            Wrap(
              spacing: 12,
              runSpacing: 12,
              alignment: WrapAlignment.spaceBetween,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(
                  'Cyfrowe Karty Kontroli HACCP',
                  style: GoogleFonts.outfit(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Wrap(
                  spacing: 8,
                  children: [
                    OutlinedButton.icon(
                      onPressed: _showAddDeviceDialog,
                      icon: const Icon(Icons.kitchen, size: 18),
                      label: const Text('Dodaj chłodnię / punkt'),
                    ),
                    FilledButton.icon(
                      onPressed: _exportSanepidPdf,
                      icon: const Icon(Icons.picture_as_pdf, size: 18),
                      label: const Text('Raport PDF dla Sanepidu'),
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),
            if (_devices.isNotEmpty)
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children:
                    _devices
                        .map(
                          (d) => Chip(
                            avatar: const Icon(Icons.thermostat, size: 16),
                            label: Text(
                              '${d.name} (${d.minTemp.toStringAsFixed(1)}..${d.maxTemp.toStringAsFixed(1)} °C)',
                            ),
                            onDeleted: () async {
                              await ref
                                  .read(apiServiceProvider)
                                  .deleteHaccpDevice(d.id);
                              _loadData();
                            },
                          ),
                        )
                        .toList(),
              ),
            const SizedBox(height: 12),
            if (_logs.isEmpty)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text('Brak wpisów w rejestrze HACCP.'),
                ),
              )
            else
              ..._logs.map((log) {
                final violated = !log.isWithinNorm;
                return Card(
                  color: violated ? Colors.red.shade50 : null,
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    leading: CircleAvatar(
                      backgroundColor:
                          violated
                              ? Colors.red.shade100
                              : Colors.green.shade100,
                      child: Icon(
                        violated
                            ? Icons.warning_amber_rounded
                            : Icons.verified_outlined,
                        color: violated ? Colors.red.shade800 : Colors.green,
                      ),
                    ),
                    title: Text(
                      log.logType == 'TEMPERATURE'
                          ? '${log.deviceName}: ${log.measuredTemp?.toStringAsFixed(1) ?? '-'} °C'
                          : 'Higiena / Mycie: ${log.deviceName}',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.bold,
                        color: violated ? Colors.red.shade900 : null,
                      ),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Wykonał(a): ${log.userName} • ${DateFormat('dd.MM.yyyy HH:mm').format(log.createdAt.toLocal())}',
                          style: const TextStyle(fontSize: 12),
                        ),
                        if (violated)
                          Text(
                            'PRZEKROCZENIE NORMY! Działanie korygujące: ${log.correctiveAction ?? 'Brak opisu'}',
                            style: TextStyle(
                              color: Colors.red.shade800,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

// ============================================================================
// SUB-TAB 3: ANNOUNCEMENT BOARD WITH READ RECEIPTS
// ============================================================================

class _ManagerAnnouncementsSubTab extends ConsumerStatefulWidget {
  const _ManagerAnnouncementsSubTab();

  @override
  ConsumerState<_ManagerAnnouncementsSubTab> createState() =>
      _ManagerAnnouncementsSubTabState();
}

class _ManagerAnnouncementsSubTabState
    extends ConsumerState<_ManagerAnnouncementsSubTab> {
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
          await ref.read(apiServiceProvider).getManagerAnnouncements();
      if (mounted) {
        setState(() {
          _announcements = list;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showCreateAnnouncementDialog() {
    final titleCtrl = TextEditingController();
    final contentCtrl = TextEditingController();
    bool isPinned = true;

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder:
                (ctx, setDialogState) => AlertDialog(
                  title: const Text('Nowe ogłoszenie dla zespołu'),
                  content: SizedBox(
                    width: 400,
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        TextField(
                          controller: titleCtrl,
                          decoration: const InputDecoration(
                            labelText: 'Tytuł ogłoszenia',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: contentCtrl,
                          maxLines: 4,
                          decoration: const InputDecoration(
                            labelText: 'Treść komunikatu',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SwitchListTile(
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Przypnij na górze tablicy'),
                          value: isPinned,
                          onChanged:
                              (v) => setDialogState(() => isPinned = v),
                        ),
                      ],
                    ),
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Anuluj'),
                    ),
                    FilledButton.icon(
                      onPressed: () async {
                        if (titleCtrl.text.trim().isEmpty ||
                            contentCtrl.text.trim().isEmpty) {
                          return;
                        }
                        await ref
                            .read(apiServiceProvider)
                            .createAnnouncement(
                              title: titleCtrl.text.trim(),
                              content: contentCtrl.text.trim(),
                              isPinned: isPinned,
                            );
                        if (ctx.mounted) {
                          Navigator.pop(ctx);
                          _loadAnnouncements();
                        }
                      },
                      icon: const Icon(Icons.send, size: 18),
                      label: const Text('Opublikuj i wyślij Push'),
                    ),
                  ],
                ),
          ),
    );
  }

  Future<void> _showReceiptsDialog(AnnouncementModel ann) async {
    AnnouncementModel details = ann;
    try {
      details = await ref
          .read(apiServiceProvider)
          .getAnnouncementReceipts(ann.id);
    } catch (_) {}

    if (!mounted) return;
    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: Text('Potwierdzenia: ${details.title}'),
            content: SizedBox(
              width: 380,
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      'Zapoznali się (${details.readCount}):',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.bold,
                        color: Colors.green.shade700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    if (details.readBy.isEmpty)
                      const Text('Nikt jeszcze nie potwierdził.')
                    else
                      ...details.readBy.map(
                        (r) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(
                            Icons.check_circle,
                            color: Colors.green,
                            size: 18,
                          ),
                          title: Text(r.userName),
                          trailing:
                              r.readAt != null
                                  ? Text(
                                    DateFormat(
                                      'dd.MM HH:mm',
                                    ).format(r.readAt!.toLocal()),
                                    style: const TextStyle(fontSize: 11),
                                  )
                                  : null,
                        ),
                      ),
                    const Divider(height: 24),
                    Text(
                      'Oczekujący na przeczytanie (${details.unreadBy.length}):',
                      style: GoogleFonts.inter(
                        fontWeight: FontWeight.bold,
                        color: Colors.orange.shade800,
                      ),
                    ),
                    const SizedBox(height: 6),
                    if (details.unreadBy.isEmpty)
                      const Text('Wszyscy pracownicy zapoznali się!')
                    else
                      ...details.unreadBy.map(
                        (r) => ListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          leading: const Icon(
                            Icons.schedule,
                            color: Colors.orange,
                            size: 18,
                          ),
                          title: Text(r.userName),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Zamknij'),
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
      onRefresh: _loadAnnouncements,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Tablica Ogłoszeń i Read Receipts',
                style: GoogleFonts.outfit(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              FilledButton.icon(
                onPressed: _showCreateAnnouncementDialog,
                icon: const Icon(Icons.campaign, size: 18),
                label: const Text('Nowe ogłoszenie'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_announcements.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Center(child: Text('Brak opublikowanych ogłoszeń.')),
              ),
            )
          else
            ..._announcements.map(
              (ann) => Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          if (ann.isPinned)
                            const Padding(
                              padding: EdgeInsets.only(right: 6),
                              child: Icon(
                                Icons.push_pin,
                                size: 18,
                                color: Colors.amber,
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
                          ActionChip(
                            avatar: const Icon(Icons.visibility, size: 16),
                            label: Text(
                              '${ann.readCount}/${ann.totalTargetCount} przeczytało',
                              style: const TextStyle(fontSize: 12),
                            ),
                            onPressed: () => _showReceiptsDialog(ann),
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.delete_outline,
                              color: Colors.red,
                            ),
                            onPressed: () async {
                              await ref
                                  .read(apiServiceProvider)
                                  .deleteAnnouncement(ann.id);
                              _loadAnnouncements();
                            },
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(ann.content),
                      const SizedBox(height: 8),
                      Text(
                        'Autor: ${ann.authorName} • ${DateFormat('dd.MM.yyyy HH:mm').format(ann.createdAt.toLocal())}',
                        style: TextStyle(
                          fontSize: 11,
                          color: Colors.grey.shade600,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
