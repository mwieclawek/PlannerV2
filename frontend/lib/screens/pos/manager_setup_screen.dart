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
    final tablesAsync = ref.watch(tablesProvider);

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
                  onLongPress: () => _confirmDeleteTable(context, ref, table),
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
                  await api.createTable(controller.text.trim());
                  ref.invalidate(tablesProvider);
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                child: const Text('Dodaj'),
              ),
            ],
          ),
    );
  }

  void _confirmDeleteTable(
    BuildContext context,
    WidgetRef ref,
    RestaurantTable table,
  ) {
    showDialog(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Usuń stolik?'),
            content: Text('Czy na pewno chcesz usunąć "${table.name}"?'),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Anuluj'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: Colors.red),
                onPressed: () async {
                  final api = ref.read(apiServiceProvider);
                  await api.deleteTable(table.id);
                  ref.invalidate(tablesProvider);
                  if (ctx.mounted) Navigator.pop(ctx);
                },
                child: const Text('Usuń'),
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
  MenuCategory _selectedCategory = MenuCategory.SOUPS;

  @override
  Widget build(BuildContext context) {
    final menuAsync = ref.watch(menuProvider);

    return Scaffold(
      body: Column(
        children: [
          // Category chips
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children:
                  MenuCategory.values.map((cat) {
                    final isSelected = cat == _selectedCategory;
                    return Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(cat.label),
                        selected: isSelected,
                        selectedColor: const Color(
                          0xFFE65100,
                        ).withOpacity(0.15),
                        onSelected:
                            (_) => setState(() => _selectedCategory = cat),
                      ),
                    );
                  }).toList(),
            ),
          ),

          // Menu items list
          Expanded(
            child: menuAsync.when(
              data: (items) {
                final filtered =
                    items
                        .where((i) => i.category == _selectedCategory)
                        .toList();
                if (filtered.isEmpty) {
                  return Center(
                    child: Text(
                      'Brak pozycji w kategorii „${_selectedCategory.label}"',
                      style: TextStyle(color: Colors.grey[500]),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 4,
                  ),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final item = filtered[index];
                    return ListTile(
                      leading: CircleAvatar(
                        backgroundColor: const Color(
                          0xFFE65100,
                        ).withOpacity(0.1),
                        child: Icon(
                          _categoryIcon(item.category),
                          color: const Color(0xFFE65100),
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
                        onPressed: () async {
                          final api = ref.read(apiServiceProvider);
                          await api.deleteMenuItem(item.id);
                          ref.invalidate(menuProvider);
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
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showAddMenuItemDialog(context),
        icon: const Icon(Icons.add),
        label: const Text('Dodaj danie'),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
      ),
    );
  }

  void _showAddMenuItemDialog(BuildContext context) {
    final nameCtrl = TextEditingController();
    final priceCtrl = TextEditingController();
    MenuCategory dialogCategory = _selectedCategory;

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
                      DropdownButtonFormField<MenuCategory>(
                        value: dialogCategory,
                        decoration: const InputDecoration(
                          labelText: 'Kategoria',
                        ),
                        items:
                            MenuCategory.values
                                .map(
                                  (c) => DropdownMenuItem(
                                    value: c,
                                    child: Text(c.label),
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
                        if (nameCtrl.text.trim().isEmpty) return;
                        final price = double.tryParse(priceCtrl.text) ?? 0.0;
                        final api = ref.read(apiServiceProvider);
                        await api.createMenuItem(
                          nameCtrl.text.trim(),
                          price,
                          dialogCategory.name,
                        );
                        ref.invalidate(menuProvider);
                        if (ctx.mounted) Navigator.pop(ctx);
                      },
                      child: const Text('Dodaj'),
                    ),
                  ],
                ),
          ),
    );
  }

  IconData _categoryIcon(MenuCategory cat) {
    switch (cat) {
      case MenuCategory.SOUPS:
        return Icons.soup_kitchen;
      case MenuCategory.MAINS:
        return Icons.dinner_dining;
      case MenuCategory.DESSERTS:
        return Icons.cake;
      case MenuCategory.DRINKS:
        return Icons.local_drink;
    }
  }
}
