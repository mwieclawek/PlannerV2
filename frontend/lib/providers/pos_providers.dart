import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/models.dart';
import 'providers.dart';

// ── Tables ──────────────────────────────────────────────────────────────────

final tablesProvider = FutureProvider.autoDispose<List<RestaurantTable>>((
  ref,
) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getTables();
});

// ── Menu ────────────────────────────────────────────────────────────────────

final menuProvider = FutureProvider.autoDispose<List<MenuItem>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getMenu();
});

// ── Orders ──────────────────────────────────────────────────────────────────

final ordersProvider = FutureProvider.autoDispose<List<KitchenOrder>>((
  ref,
) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getOrders();
});

final activeOrdersProvider = FutureProvider.autoDispose<List<KitchenOrder>>((
  ref,
) async {
  final api = ref.watch(apiServiceProvider);
  final orders = await api.getOrders();
  return orders
      .where(
        (o) =>
            o.status == KitchenOrderStatus.PENDING ||
            o.status == KitchenOrderStatus.IN_PROGRESS ||
            o.status == KitchenOrderStatus.READY,
      )
      .toList();
});

// ── Cart (ongoing order before submitting) ──────────────────────────────────

class CartItem {
  final MenuItem menuItem;
  int quantity;
  String? notes;
  CartItem({required this.menuItem, this.quantity = 1, this.notes});
}

class CartNotifier extends StateNotifier<List<CartItem>> {
  CartNotifier() : super([]);

  void addItem(MenuItem item) {
    final index = state.indexWhere((e) => e.menuItem.id == item.id);
    if (index >= 0) {
      state = [
        for (int i = 0; i < state.length; i++)
          if (i == index)
            CartItem(
              menuItem: item,
              quantity: state[i].quantity + 1,
              notes: state[i].notes,
            )
          else
            state[i],
      ];
    } else {
      state = [...state, CartItem(menuItem: item)];
    }
  }

  void removeItem(String menuItemId) {
    state = state.where((e) => e.menuItem.id != menuItemId).toList();
  }

  void updateQuantity(String menuItemId, int quantity) {
    if (quantity <= 0) {
      removeItem(menuItemId);
      return;
    }
    state = [
      for (final item in state)
        if (item.menuItem.id == menuItemId)
          CartItem(
            menuItem: item.menuItem,
            quantity: quantity,
            notes: item.notes,
          )
        else
          item,
    ];
  }

  void updateNotes(String menuItemId, String? notes) {
    state = [
      for (final item in state)
        if (item.menuItem.id == menuItemId)
          CartItem(
            menuItem: item.menuItem,
            quantity: item.quantity,
            notes: notes,
          )
        else
          item,
    ];
  }

  void clear() => state = [];

  double get total =>
      state.fold(0.0, (sum, item) => sum + item.menuItem.price * item.quantity);
}

final cartProvider =
    StateNotifierProvider.autoDispose<CartNotifier, List<CartItem>>((ref) {
      return CartNotifier();
    });
