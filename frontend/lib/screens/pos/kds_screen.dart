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
      ref.invalidate(posActiveOrdersProvider);
    });
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ordersAsync = ref.watch(posActiveOrdersProvider);

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
            onPressed: () => ref.invalidate(posActiveOrdersProvider),
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
          // Filter to only items relevant to KDS
          final kdsOrders = <PosOrder>[];
          for (final order in orders) {
            final activeItems = order.items.where((i) =>
                i.kdsStatus == KdsStatus.NEW ||
                i.kdsStatus == KdsStatus.PREPARING ||
                i.kdsStatus == KdsStatus.READY).toList();
            if (activeItems.isNotEmpty) {
              kdsOrders.add(order);
            }
          }

          if (kdsOrders.isEmpty) {
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

          // Sort orders: NEW first, then PREPARING, then READY.
          int getOrderWeight(PosOrder o) {
            if (o.items.any((i) => i.kdsStatus == KdsStatus.NEW)) return 0;
            if (o.items.any((i) => i.kdsStatus == KdsStatus.PREPARING)) return 1;
            return 2;
          }

          kdsOrders.sort((a, b) {
            final wA = getOrderWeight(a);
            final wB = getOrderWeight(b);
            if (wA != wB) return wA.compareTo(wB);
            return a.createdAt.compareTo(b.createdAt);
          });

          return GridView.builder(
            padding: const EdgeInsets.all(16),
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 3,
              crossAxisSpacing: 16,
              mainAxisSpacing: 16,
              childAspectRatio: 0.7,
            ),
            itemCount: kdsOrders.length,
            itemBuilder:
                (context, index) => _KdsTicket(order: kdsOrders[index]),
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
  final PosOrder order;
  const _KdsTicket({required this.order});

  KdsStatus _getTicketCollectiveStatus() {
    final items = order.items.where((i) =>
        i.kdsStatus == KdsStatus.NEW ||
        i.kdsStatus == KdsStatus.PREPARING ||
        i.kdsStatus == KdsStatus.READY).toList();
    if (items.any((i) => i.kdsStatus == KdsStatus.NEW)) return KdsStatus.NEW;
    if (items.any((i) => i.kdsStatus == KdsStatus.PREPARING)) return KdsStatus.PREPARING;
    return KdsStatus.READY;
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    Color headerColor;
    Color borderColor;
    final collectiveStatus = _getTicketCollectiveStatus();

    switch (collectiveStatus) {
      case KdsStatus.NEW:
        headerColor = const Color(0xFFFF6F00);
        borderColor = const Color(0xFFFF6F00);
        break;
      case KdsStatus.PREPARING:
        headerColor = const Color(0xFF1565C0);
        borderColor = const Color(0xFF1565C0);
        break;
      case KdsStatus.READY:
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

    final items = order.items.where((i) =>
        i.kdsStatus == KdsStatus.NEW ||
        i.kdsStatus == KdsStatus.PREPARING ||
        i.kdsStatus == KdsStatus.READY).toList();

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
              itemCount: items.length,
              itemBuilder: (context, index) {
                final item = items[index];
                final isDone = item.kdsStatus == KdsStatus.READY;
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
                          item.itemNameSnapshot,
                          style: GoogleFonts.inter(
                            fontSize: 13,
                            color: isDone ? Colors.grey : Colors.white,
                            fontWeight: FontWeight.w500,
                            decoration: isDone ? TextDecoration.lineThrough : null,
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
            child: _buildActionButton(context, ref, collectiveStatus, items),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(BuildContext context, WidgetRef ref, KdsStatus collectiveStatus, List<PosOrderItem> items) {
    switch (collectiveStatus) {
      case KdsStatus.NEW:
        return FilledButton.icon(
          onPressed: () => _updateAllItems(ref, items, KdsStatus.NEW, 'PREPARING'),
          icon: const Icon(Icons.play_arrow),
          label: const Text('Rozpocznij'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF1565C0),
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(42),
          ),
        );
      case KdsStatus.PREPARING:
        return FilledButton.icon(
          onPressed: () => _updateAllItems(ref, items, KdsStatus.PREPARING, 'READY'),
          icon: const Icon(Icons.check),
          label: const Text('GOTOWE'),
          style: FilledButton.styleFrom(
            backgroundColor: const Color(0xFF2E7D32),
            foregroundColor: Colors.white,
            minimumSize: const Size.fromHeight(42),
          ),
        );
      case KdsStatus.READY:
        return OutlinedButton.icon(
          onPressed: () => _updateAllItems(ref, items, KdsStatus.READY, 'DELIVERED'),
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

  Future<void> _updateAllItems(WidgetRef ref, List<PosOrderItem> items, KdsStatus currentStatus, String targetStatus) async {
    final api = ref.read(apiServiceProvider);
    
    // Update all items that match the collective 'waiting' state
    for (final item in items) {
      if (item.kdsStatus == currentStatus) {
        await api.updateKdsItemStatus(item.id, targetStatus);
      }
    }
    
    ref.invalidate(posActiveOrdersProvider);
  }
}
