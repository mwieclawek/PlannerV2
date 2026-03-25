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

// ══════════════════════════════════════════════════════════════════════════════
//  POS v2 Providers
// ══════════════════════════════════════════════════════════════════════════════

// ── Zones ────────────────────────────────────────────────────────────────────

final zonesProvider = FutureProvider.autoDispose<List<TableZone>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getZones();
});

// ── Tables v2 ────────────────────────────────────────────────────────────────

final posTablesProvider = FutureProvider.autoDispose<List<PosTable>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getTablesV2();
});

final posTablesByZoneProvider =
    FutureProvider.autoDispose.family<List<PosTable>, String>((ref, zoneId) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getTablesV2(zoneId: zoneId);
});

// ── Categories ───────────────────────────────────────────────────────────────

final categoriesProvider = FutureProvider.autoDispose<List<PosCategory>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getCategories();
});

// ── Menu v2 ──────────────────────────────────────────────────────────────────

final posMenuProvider = FutureProvider.autoDispose<List<PosMenuItem>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getMenuV2();
});

final posMenuByCategoryProvider =
    FutureProvider.autoDispose.family<List<PosMenuItem>, int>((ref, categoryId) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getMenuV2(categoryId: categoryId);
});

// ── Modifier Groups ──────────────────────────────────────────────────────────

final modifierGroupsProvider = FutureProvider.autoDispose<List<ModifierGroup>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getModifierGroups();
});

// ── Orders v2 ────────────────────────────────────────────────────────────────

final posOrdersProvider = FutureProvider.autoDispose<List<PosOrder>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getOrdersV2();
});

final posActiveOrdersProvider = FutureProvider.autoDispose<List<PosOrder>>((ref) async {
  final api = ref.watch(apiServiceProvider);
  final orders = await api.getOrdersV2();
  return orders.where((o) =>
      o.status == OrderStatus.OPEN ||
      o.status == OrderStatus.SENT ||
      o.status == OrderStatus.PARTIALLY_PAID).toList();
});

final posOrdersByTableProvider =
    FutureProvider.autoDispose.family<List<PosOrder>, String>((ref, tableId) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getOrdersV2(tableId: tableId);
});

// ── Tips ─────────────────────────────────────────────────────────────────────

final tipsProvider = FutureProvider.autoDispose<TipSummary>((ref) async {
  final api = ref.watch(apiServiceProvider);
  return await api.getMyTips();
});

// ── Cart v2 (with modifier support) ──────────────────────────────────────────

class PosCartItem {
  final PosMenuItem menuItem;
  int quantity;
  String? notes;
  int course;
  List<int> modifierIds;

  PosCartItem({
    required this.menuItem, this.quantity = 1, this.notes,
    this.course = 1, this.modifierIds = const [],
  });
}

class PosCartNotifier extends StateNotifier<List<PosCartItem>> {
  PosCartNotifier() : super([]);

  void addItem(PosMenuItem item, {List<int> modifierIds = const []}) {
    final index = state.indexWhere((e) =>
        e.menuItem.id == item.id &&
        _listEquals(e.modifierIds, modifierIds));
    if (index >= 0) {
      state = [
        for (int i = 0; i < state.length; i++)
          if (i == index)
            PosCartItem(
              menuItem: item,
              quantity: state[i].quantity + 1,
              notes: state[i].notes,
              course: state[i].course,
              modifierIds: modifierIds,
            )
          else
            state[i],
      ];
    } else {
      state = [...state, PosCartItem(menuItem: item, modifierIds: modifierIds)];
    }
  }

  void removeAt(int index) {
    state = [...state]..removeAt(index);
  }

  void updateQuantity(int index, int quantity) {
    if (quantity <= 0) {
      removeAt(index);
      return;
    }
    state = [
      for (int i = 0; i < state.length; i++)
        if (i == index)
          PosCartItem(
            menuItem: state[i].menuItem,
            quantity: quantity,
            notes: state[i].notes,
            course: state[i].course,
            modifierIds: state[i].modifierIds,
          )
        else
          state[i],
    ];
  }

  void clear() => state = [];

  double get total => state.fold(0.0, (sum, item) =>
      sum + item.menuItem.price * item.quantity);

  List<Map<String, dynamic>> toApiPayload() => state.map((e) => {
    'menu_item_id': e.menuItem.id,
    'quantity': e.quantity,
    'course': e.course,
    if (e.notes != null && e.notes!.isNotEmpty) 'notes': e.notes,
    if (e.modifierIds.isNotEmpty) 'modifier_ids': e.modifierIds,
  }).toList();

  bool _listEquals(List<int> a, List<int> b) {
    if (a.length != b.length) return false;
    for (int i = 0; i < a.length; i++) {
      if (a[i] != b[i]) return false;
    }
    return true;
  }
}

final posCartProvider =
    StateNotifierProvider.autoDispose<PosCartNotifier, List<PosCartItem>>((ref) {
      return PosCartNotifier();
    });
