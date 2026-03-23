import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import '../../providers/module_provider.dart';
import '../../providers/pos_providers.dart';
import '../../models/models.dart';
import 'order_creation_screen.dart';

class WaiterTablesScreen extends ConsumerWidget {
  const WaiterTablesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final tablesAsync = ref.watch(tablesProvider);
    final ordersAsync = ref.watch(activeOrdersProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Sala – Stoliki',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.kitchen),
            tooltip: 'Widok kuchni (KDS)',
            onPressed: () => Navigator.of(context).pushNamed('/pos/kds'),
          ),
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
      ),
      body: tablesAsync.when(
        data: (tables) {
          if (tables.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.table_restaurant,
                    size: 80,
                    color: Colors.grey[300],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Brak stolików',
                    style: GoogleFonts.inter(
                      fontSize: 20,
                      color: Colors.grey[400],
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Manager musi najpierw dodać stoliki w konfiguracji.',
                    style: TextStyle(color: Colors.grey[400]),
                  ),
                ],
              ),
            );
          }

          // Build a map of tableId -> active orders
          final ordersByTable = <String, List<KitchenOrder>>{};
          final orders = ordersAsync.valueOrNull ?? [];
          for (final order in orders) {
            ordersByTable.putIfAbsent(order.tableId, () => []).add(order);
          }

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(tablesProvider);
              ref.invalidate(activeOrdersProvider);
            },
            child: GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 14,
                mainAxisSpacing: 14,
                childAspectRatio: 0.95,
              ),
              itemCount: tables.length,
              itemBuilder: (context, index) {
                final table = tables[index];
                final tableOrders = ordersByTable[table.id] ?? [];
                final hasActive = tableOrders.isNotEmpty;
                final hasReady = tableOrders.any(
                  (o) => o.status == KitchenOrderStatus.READY,
                );

                Color cardColor;
                Color iconColor;
                String statusLabel;
                if (hasReady) {
                  cardColor = const Color(0xFF4CAF50).withOpacity(0.12);
                  iconColor = const Color(0xFF2E7D32);
                  statusLabel = '🟢 GOTOWE';
                } else if (hasActive) {
                  cardColor = const Color(0xFFFFF3E0);
                  iconColor = const Color(0xFFE65100);
                  statusLabel = '🟠 Aktywne (${tableOrders.length})';
                } else {
                  cardColor = Colors.grey[50]!;
                  iconColor = Colors.grey[400]!;
                  statusLabel = 'Wolny';
                }

                return Card(
                  elevation: hasActive ? 4 : 1,
                  color: cardColor,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(16),
                    side:
                        hasReady
                            ? const BorderSide(
                              color: Color(0xFF4CAF50),
                              width: 2,
                            )
                            : hasActive
                            ? const BorderSide(
                              color: Color(0xFFE65100),
                              width: 1.5,
                            )
                            : BorderSide.none,
                  ),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => OrderCreationScreen(table: table),
                        ),
                      );
                    },
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.table_restaurant,
                          size: 40,
                          color: iconColor,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          table.name,
                          style: GoogleFonts.inter(
                            fontWeight: FontWeight.w700,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          statusLabel,
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                            color:
                                hasReady
                                    ? const Color(0xFF2E7D32)
                                    : hasActive
                                    ? const Color(0xFFE65100)
                                    : Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Błąd: $e')),
      ),
    );
  }
}
