import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import '../../providers/module_provider.dart';
import '../../providers/pos_providers.dart';
import '../../models/models.dart';

class ManagerSetupScreen extends ConsumerStatefulWidget {
  const ManagerSetupScreen({super.key});

  @override
  ConsumerState<ManagerSetupScreen> createState() => _ManagerSetupScreenState();
}

class _ManagerSetupScreenState extends ConsumerState<ManagerSetupScreen>
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
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Konfiguracja POS',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
        actions: [
          // Module switcher
          IconButton(
            icon: const Icon(Icons.calendar_month),
            tooltip: 'Przełącz na Grafik',
            onPressed: () {
              ref
                  .read(moduleProvider.notifier)
                  .switchModule(AppModule.planning);
            },
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          tabs: const [
            Tab(icon: Icon(Icons.table_restaurant), text: 'Stoliki'),
            Tab(icon: Icon(Icons.restaurant_menu), text: 'Karta Dań'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [_TablesTab(), _MenuTab()],
      ),
    );
  }
}

// ── Tables Tab ──────────────────────────────────────────────────────

class _TablesTab extends ConsumerWidget {
  const _TablesTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tablesAsync = ref.watch(posTablesProvider);

    return Scaffold(
      body: tablesAsync.when(
        data: (tables) {
          if (tables.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.table_restaurant,
                    size: 64,
                    color: Colors.grey[300],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Brak stolików',
                    style: TextStyle(fontSize: 18, color: Colors.grey[500]),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Dodaj pierwszy stolik klikając +',
                    style: TextStyle(color: Colors.grey[400]),
                  ),
                ],
              ),
            );
          }
          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.2,
            ),
            itemCount: tables.length,
            itemBuilder: (context, index) {
              final table = tables[index];
              return Card(
                elevation: 2,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                child: InkWell(
                  borderRadius: BorderRadius.circular(12),
                  onLongPress: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Usuwanie niezaimplementowane w v2')),
                    );
                  },
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.table_restaurant,
                        size: 36,
                        color: const Color(0xFFE65100),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        table.name,
                        style: GoogleFonts.inter(
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Błąd: $e')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddTableDialog(context, ref),
        icon: const Icon(Icons.add),
        label: const Text('Dodaj stolik'),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
      ),
    );
  }

  void _showAddTableDialog(BuildContext context, WidgetRef ref) {
    final controller = TextEditingController();
    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Nowy stolik'),
            content: TextField(
              controller: controller,
              decoration: const InputDecoration(
                labelText: 'Nazwa / numer stolika',
                hintText: 'np. Stolik 1, Taras A',
              ),
              autofocus: true,
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                onPressed: () async {
                  if (controller.text.trim().isEmpty) return;
                  final api = ref.read(apiServiceProvider);
                  await api.createTableV2(controller.text.trim());
                  ref.invalidate(posTablesProvider);
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                child: const Text('Dodaj'),
              ),
            ],
          ),
    );
  }
}

// ── Menu Tab ────────────────────────────────────────────────────────

class _MenuTab extends ConsumerStatefulWidget {
  const _MenuTab();

  @override
  ConsumerState<_MenuTab> createState() => _MenuTabState();
}

class _MenuTabState extends ConsumerState<_MenuTab> {
  int? _selectedCategoryId;

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(categoriesProvider);
    final menuAsync = ref.watch(posMenuProvider);

    return Scaffold(
      body: categoriesAsync.when(
        data: (categories) {
          if (categories.isEmpty) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Text('Brak kategorii.'),
                  ElevatedButton(
                    onPressed: () => _showAddCategoryDialog(context),
                    child: const Text('Dodaj kategorię'),
                  ),
                ],
              ),
            );
          }

          if (_selectedCategoryId == null && categories.isNotEmpty) {
            _selectedCategoryId = categories.first.id;
          }

          return Column(
            children: [
              // Category chips
              Padding(
                padding: const EdgeInsets.all(12),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: [
                      ...categories.map((cat) {
                        final isSelected = cat.id == _selectedCategoryId;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text(cat.name),
                            selected: isSelected,
                            selectedColor: const Color(0xFFE65100).withOpacity(0.15),
                            onSelected: (_) => setState(() => _selectedCategoryId = cat.id),
                          ),
                        );
                      }),
                      ActionChip(
                        avatar: const Icon(Icons.add, size: 16),
                        label: const Text('Nowa'),
                        onPressed: () => _showAddCategoryDialog(context),
                      ),
                    ],
                  ),
                ),
              ),

              // Menu items list
              Expanded(
                child: menuAsync.when(
                  data: (items) {
                    final filtered = items.where((i) => i.categoryId == _selectedCategoryId).toList();
                    if (filtered.isEmpty) {
                      return Center(
                        child: Text(
                          'Brak pozycji w tej kategorii',
                          style: TextStyle(color: Colors.grey[500]),
                        ),
                      );
                    }
                    return ListView.separated(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                      itemCount: filtered.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (context, index) {
                        final item = filtered[index];
                        return ListTile(
                          leading: CircleAvatar(
                            backgroundColor: const Color(0xFFE65100).withOpacity(0.1),
                            child: const Icon(
                              Icons.fastfood,
                              color: Color(0xFFE65100),
                            ),
                          ),
                          title: Text(
                            item.name,
                            style: GoogleFonts.inter(fontWeight: FontWeight.w500),
                          ),
                          subtitle: Text(
                            '${item.price.toStringAsFixed(2)} zł',
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w700,
                              color: const Color(0xFFE65100),
                            ),
                          ),
                          trailing: IconButton(
                            icon: const Icon(
                              Icons.delete_outline,
                              color: Colors.red,
                            ),
                            onPressed: () {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(content: Text('Usuwanie niezaimplementowane w v2')),
                              );
                            },
                          ),
                        );
                      },
                    );
                  },
                  loading: () => const Center(child: CircularProgressIndicator()),
                  error: (e, _) => Center(child: Text('Błąd: $e')),
                ),
              ),
            ],
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Błąd: $e')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddMenuItemDialog(context, ref.read(categoriesProvider).valueOrNull ?? []),
        icon: const Icon(Icons.add),
        label: const Text('Dodaj danie'),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
      ),
    );
  }

  void _showAddCategoryDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nowa Kategoria'),
        content: TextField(
          controller: nameCtrl,
          decoration: const InputDecoration(labelText: 'Nazwa kategorii'),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Anuluj'),
          ),
          FilledButton(
            onPressed: () async {
              if (nameCtrl.text.trim().isEmpty) return;
              final api = ref.read(apiServiceProvider);
              await api.createCategory(nameCtrl.text.trim());
              ref.invalidate(categoriesProvider);
              if (ctx.mounted) Navigator.pop(ctx);
            },
            child: const Text('Dodaj'),
          ),
        ],
      ),
    );
  }

  void _showAddMenuItemDialog(BuildContext context, List<PosCategory> categories) {
    if (categories.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Dodaj najpierw kategorię')));
      return;
    }
    
    final nameCtrl = TextEditingController();
    final priceCtrl = TextEditingController();
    int? dialogCategory = _selectedCategoryId ?? categories.first.id;

    showDialog(
      context: context,
      builder:
          (ctx) => StatefulBuilder(
            builder:
                (ctx, setDialogState) => AlertDialog(
                  title: const Text('Nowa pozycja w menu'),
                  content: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      TextField(
                        controller: nameCtrl,
                        decoration: const InputDecoration(labelText: 'Nazwa'),
                        autofocus: true,
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: priceCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Cena (zł)',
                          hintText: '0.00',
                        ),
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                      ),
                      const SizedBox(height: 12),
                      DropdownButtonFormField<int>(
                        value: dialogCategory,
                        decoration: const InputDecoration(
                          labelText: 'Kategoria',
                        ),
                        items:
                            categories
                                .map(
                                  (c) => DropdownMenuItem(
                                    value: c.id,
                                    child: Text(c.name),
                                  ),
                                )
                                .toList(),
                        onChanged: (v) {
                          if (v != null)
                            setDialogState(() => dialogCategory = v);
                        },
                      ),
                    ],
                  ),
                  actions: [
                    TextButton(
                      onPressed: () => Navigator.pop(ctx),
                      child: const Text('Anuluj'),
                    ),
                    FilledButton(
                      onPressed: () async {
                        if (nameCtrl.text.trim().isEmpty || dialogCategory == null) return;
                        final price = double.tryParse(priceCtrl.text) ?? 0.0;
                        final api = ref.read(apiServiceProvider);
                        await api.createMenuItemV2(
                          nameCtrl.text.trim(),
                          price,
                          dialogCategory!,
                        );
                        ref.invalidate(posMenuProvider);
                        if (ctx.mounted) Navigator.pop(ctx);
                      },
                      child: const Text('Dodaj'),
                    ),
                  ],
                ),
          ),
    );
  }
}
