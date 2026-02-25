import 'package:flutter/material.dart';
import 'scheduler_tab.dart';
import 'giveaway_tab.dart';
import 'availability_view_tab.dart';

class SchedulerWrapperTab extends StatefulWidget {
  const SchedulerWrapperTab({super.key});

  @override
  State<SchedulerWrapperTab> createState() => _SchedulerWrapperTabState();
}

class _SchedulerWrapperTabState extends State<SchedulerWrapperTab>
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
    return Column(
      children: [
        Container(
          color: Colors.white,
          child: TabBar(
            controller: _tabController,
            labelColor: Theme.of(context).colorScheme.primary,
            unselectedLabelColor:
                Theme.of(context).colorScheme.onSurfaceVariant,
            indicatorColor: Theme.of(context).colorScheme.primary,
            tabs: const [
              Tab(
                text: 'Tworzenie grafiku',
                icon: Icon(Icons.calendar_month_outlined),
              ),
              Tab(text: 'Zmiany', icon: Icon(Icons.swap_horiz)),
              Tab(
                text: 'Dostępność',
                icon: Icon(Icons.event_available_outlined),
              ),
            ],
          ),
        ),
        Expanded(
          child: TabBarView(
            controller: _tabController,
            // Disable swipe to prevent conflicts with SchedulerTab's own drag gestures
            physics: const NeverScrollableScrollPhysics(),
            children: const [
              SchedulerTab(),
              GiveawayTab(),
              AvailabilityViewTab(),
            ],
          ),
        ),
      ],
    );
  }
}
