import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import '../../providers/module_provider.dart';
import '../../providers/pos_providers.dart';
import '../../models/models.dart';

class KdsScreen extends ConsumerStatefulWidget {
  const KdsScreen({super.key});

  @override
  ConsumerState<KdsScreen> createState() => _KdsScreenState();
}

class _KdsScreenState extends ConsumerState<KdsScreen> {
  Timer? _pollTimer;

  @override
  void initState() {
    super.initState();
    // Polling every 8 seconds
    _pollTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      ref.invalidate(activeOrdersProvider);
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ordersAsync = ref.watch(activeOrdersProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF263238),
      appBar: AppBar(
        title: Text(
          'Kuchnia – Bony',
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFF37474F),
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(activeOrdersProvider),
          ),
          IconButton(
            icon: const Icon(Icons.table_restaurant),
            tooltip: 'Widok sali',
            onPressed: () => Navigator.of(context).pop(),
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
        ],
      ),
      body: ordersAsync.when(
        data: (orders) {
          if (orders.isEmpty) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.check_circle_outline,
                    size: 80,
                    color: Colors.grey[600],
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Brak aktywnych zamówień',
                    style: GoogleFonts.inter(
                      fontSize: 20,
                      color: Colors.grey[500],
                    ),
                  ),
                ],
              ),
            );
          }

          // Group by status: PENDING first, then IN_PROGRESS, then READY
          final pending =
              orders
                  .where((o) => o.status == KitchenOrderStatus.PENDING)
                  .toList();
          final inProgress =
              orders
                  .where((o) => o.status == KitchenOrderStatus.IN_PROGRESS)
                  .toList();
          final ready =
              orders
                  .where((o) => o.status == KitchenOrderStatus.READY)
                  .toList();
          final sortedOrders = [...pending, ...inProgress, ...ready];

          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              childAspectRatio: 0.7,
            ),
            itemCount: sortedOrders.length,
            itemBuilder:
                (context, index) => _KdsTicket(order: sortedOrders[index]),
          );
        },
        loading:
            () => const Center(
              child: CircularProgressIndicator(color: Colors.white),
            ),
        error:
            (e, _) => Center(
              child: Text(
                'Błąd: $e',
                style: const TextStyle(color: Colors.white),
              ),
            ),
      ),
    );
  }
}

class _KdsTicket extends ConsumerWidget {
  final KitchenOrder order;
  const _KdsTicket({required this.order});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Color headerColor;
    Color borderColor;
    switch (order.status) {
      case KitchenOrderStatus.PENDING:
        headerColor = const Color(0xFFFF6F00);
        borderColor = const Color(0xFFFF6F00);
        break;
      case KitchenOrderStatus.IN_PROGRESS:
        headerColor = const Color(0xFF1565C0);
        borderColor = const Color(0xFF1565C0);
        break;
      case KitchenOrderStatus.READY:
        headerColor = const Color(0xFF2E7D32);
        borderColor = const Color(0xFF4CAF50);
        break;
      default:
        headerColor = Colors.grey;
        borderColor = Colors.grey;
    }

    final elapsed = DateTime.now().difference(order.createdAt);
    final elapsedStr =
        elapsed.inMinutes > 0
            ? '${elapsed.inMinutes} min'
            : '${elapsed.inSeconds} sek';

    return Card(
      elevation: 4,
      color: const Color(0xFF37474F),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: borderColor, width: 2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: headerColor,
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(10),
                topRight: Radius.circular(10),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    order.tableName ?? 'Stolik',
                    style: GoogleFonts.inter(
                      fontWeight: FontWeight.w800,
                      fontSize: 16,
                      color: Colors.white,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    elapsedStr,
                    style: GoogleFonts.inter(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // Items list
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              itemCount: order.items.length,
              itemBuilder: (context, index) {
                final item = order.items[index];
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: Colors.white12,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          '${item.quantity}',
                          style: GoogleFonts.inter(
                            fontWeight: FontWeight.w800,
                            color: Colors.white,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          item.menuItemName ?? '—',
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            color: Colors.white,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),

          // Action button
          Padding(
            padding: const EdgeInsets.all(10),
            child: _buildActionButton(context, ref),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(BuildContext context, WidgetRef ref) {
    switch (order.status) {
      case KitchenOrderStatus.PENDING:
        return FilledButton.icon(
          onPressed: () => _updateStatus(ref, 'IN_PROGRESS'),
          icon: const Icon(Icons.play_arrow),
          label: const Text('Rozpocznij'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF1565C0),
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(42),
          ),
        );
      case KitchenOrderStatus.IN_PROGRESS:
        return FilledButton.icon(
          onPressed: () => _updateStatus(ref, 'READY'),
          icon: const Icon(Icons.check),
          label: const Text('GOTOWE'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(42),
          ),
        );
      case KitchenOrderStatus.READY:
        return OutlinedButton.icon(
          onPressed: () => _updateStatus(ref, 'DELIVERED'),
          icon: const Icon(Icons.done_all),
          label: const Text('Wydano'),
          style: OutlinedButton.styleFrom(
            foregroundColor: const Color(0xFF4CAF50),
            side: const BorderSide(color: Color(0xFF4CAF50)),
            minimumSize: const Size.fromHeight(42),
          ),
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Future<void> _updateStatus(WidgetRef ref, String status) async {
    final api = ref.read(apiServiceProvider);
    await api.updateOrderStatus(order.id, status);
    ref.invalidate(activeOrdersProvider);
    ref.invalidate(ordersProvider);
  }
}
