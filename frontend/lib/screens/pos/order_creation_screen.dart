import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../providers/providers.dart';
import '../../providers/pos_providers.dart';
import '../../models/models.dart';

class OrderCreationScreen extends ConsumerStatefulWidget {
  final RestaurantTable table;
  const OrderCreationScreen({super.key, required this.table});

  @override
  ConsumerState<OrderCreationScreen> createState() =>
      _OrderCreationScreenState();
}

class _OrderCreationScreenState extends ConsumerState<OrderCreationScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isSending = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(
      length: MenuCategory.values.length,
      vsync: this,
    );
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final menuAsync = ref.watch(menuProvider);
    final cart = ref.watch(cartProvider);
    final cartNotifier = ref.read(cartProvider.notifier);
    final cartTotal = cartNotifier.total;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.table.name,
          style: GoogleFonts.outfit(
            fontWeight: FontWeight.bold,
            color: Colors.white,
          ),
        ),
        backgroundColor: const Color(0xFFE65100),
        foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          isScrollable: true,
          tabs: MenuCategory.values.map((c) => Tab(text: c.label)).toList(),
        ),
      ),
      body: Column(
        children: [
          // Menu grid
          Expanded(
            flex: 3,
            child: menuAsync.when(
              data:
                  (items) => TabBarView(
                    controller: _tabController,
                    children:
                        MenuCategory.values.map((cat) {
                          final catItems =
                              items.where((i) => i.category == cat).toList();
                          if (catItems.isEmpty) {
                            return Center(
                              child: Text(
                                'Brak pozycji',
                                style: TextStyle(color: Colors.grey[400]),
                              ),
                            );
                          }
                          return GridView.builder(
                            padding: const EdgeInsets.all(12),
                            gridDelegate:
                                const SliverGridDelegateWithFixedCrossAxisCount(
                                  crossAxisCount: 3,
                                  crossAxisSpacing: 10,
                                  mainAxisSpacing: 10,
                                  childAspectRatio: 1.4,
                                ),
                            itemCount: catItems.length,
                            itemBuilder: (context, index) {
                              final item = catItems[index];
                              return Material(
                                elevation: 1,
                                borderRadius: BorderRadius.circular(12),
                                child: InkWell(
                                  borderRadius: BorderRadius.circular(12),
                                  onTap: () => cartNotifier.addItem(item),
                                  child: Container(
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(
                                        color: Colors.grey[200]!,
                                      ),
                                    ),
                                    padding: const EdgeInsets.all(10),
                                    child: Column(
                                      mainAxisAlignment:
                                          MainAxisAlignment.center,
                                      children: [
                                        Flexible(
                                          child: Text(
                                            item.name,
                                            textAlign: TextAlign.center,
                                            overflow: TextOverflow.ellipsis,
                                            maxLines: 2,
                                            style: GoogleFonts.inter(
                                              fontWeight: FontWeight.w600,
                                              fontSize: 13,
                                            ),
                                          ),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          '${item.price.toStringAsFixed(2)} zł',
                                          style: GoogleFonts.inter(
                                            fontWeight: FontWeight.w700,
                                            fontSize: 14,
                                            color: const Color(0xFFE65100),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              );
                            },
                          );
                        }).toList(),
                  ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Błąd: $e')),
            ),
          ),

          // Cart summary
          Container(
            decoration: BoxDecoration(
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black12,
                  blurRadius: 8,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (cart.isNotEmpty) ...[
                  Container(
                    constraints: const BoxConstraints(maxHeight: 180),
                    child: ListView.builder(
                      shrinkWrap: true,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      itemCount: cart.length,
                      itemBuilder: (context, index) {
                        final item = cart[index];
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 3),
                          child: Row(
                            children: [
                              // Quantity controls
                              IconButton(
                                icon: const Icon(
                                  Icons.remove_circle_outline,
                                  size: 20,
                                ),
                                onPressed:
                                    () => cartNotifier.updateQuantity(
                                      item.menuItem.id,
                                      item.quantity - 1,
                                    ),
                                visualDensity: VisualDensity.compact,
                              ),
                              Text(
                                '${item.quantity}',
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                              IconButton(
                                icon: const Icon(
                                  Icons.add_circle_outline,
                                  size: 20,
                                ),
                                onPressed:
                                    () => cartNotifier.updateQuantity(
                                      item.menuItem.id,
                                      item.quantity + 1,
                                    ),
                                visualDensity: VisualDensity.compact,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  item.menuItem.name,
                                  style: GoogleFonts.inter(fontSize: 13),
                                ),
                              ),
                              Text(
                                '${(item.menuItem.price * item.quantity).toStringAsFixed(2)} zł',
                                style: GoogleFonts.inter(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                  const Divider(height: 1),
                ],
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Koszyk',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: Colors.grey,
                            ),
                          ),
                          Text(
                            '${cartTotal.toStringAsFixed(2)} zł',
                            style: GoogleFonts.outfit(
                              fontWeight: FontWeight.bold,
                              fontSize: 24,
                              color: const Color(0xFFE65100),
                            ),
                          ),
                        ],
                      ),
                      const Spacer(),
                      if (cart.isNotEmpty) ...[
                        TextButton(
                          onPressed: () => cartNotifier.clear(),
                          child: const Text('Wyczyść'),
                        ),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                          onPressed: _isSending ? null : _submitOrder,
                          icon:
                              _isSending
                                  ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      color: Colors.white,
                                    ),
                                  )
                                  : const Icon(Icons.send),
                          label: const Text('Wyślij na kuchnię'),
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFFE65100),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(
                              horizontal: 24,
                              vertical: 14,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _submitOrder() async {
    setState(() => _isSending = true);
    try {
      final cart = ref.read(cartProvider);
      final api = ref.read(apiServiceProvider);

      final items =
          cart
              .map(
                (e) => {
                  'menu_item_id': e.menuItem.id,
                  'quantity': e.quantity,
                  if (e.notes != null && e.notes!.isNotEmpty) 'notes': e.notes,
                },
              )
              .toList();

      await api.createOrder(widget.table.id, items);

      ref.read(cartProvider.notifier).clear();
      ref.invalidate(activeOrdersProvider);
      ref.invalidate(ordersProvider);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Zamówienie wysłane na kuchnię!'),
            backgroundColor: Color(0xFF2E7D32),
          ),
        );
        Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Błąd: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) setState(() => _isSending = false);
    }
  }
}
