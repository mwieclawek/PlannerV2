import 'package:flutter/material.dart';

class HoverSidebarDestination {
  final Widget icon;
  final Widget selectedIcon;
  final String label;

  const HoverSidebarDestination({
    required this.icon,
    required this.selectedIcon,
    required this.label,
  });
}

class HoverSidebarScaffold extends StatefulWidget {
  final PreferredSizeWidget? appBar;
  final Widget body;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final List<HoverSidebarDestination> destinations;
  final double desktopBreakpoint;

  const HoverSidebarScaffold({
    super.key,
    this.appBar,
    required this.body,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.destinations,
    this.desktopBreakpoint = 768.0,
  });

  @override
  State<HoverSidebarScaffold> createState() => _HoverSidebarScaffoldState();
}

class _HoverSidebarScaffoldState extends State<HoverSidebarScaffold> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.of(context).size.width;
    final isDesktop = screenWidth >= widget.desktopBreakpoint;

    if (!isDesktop) {
      return Scaffold(
        appBar: widget.appBar,
        body: widget.body,
        bottomNavigationBar: NavigationBar(
          selectedIndex: widget.selectedIndex,
          onDestinationSelected: widget.onDestinationSelected,
          destinations: widget.destinations
              .map(
                (d) => NavigationDestination(
                  icon: d.icon,
                  selectedIcon: d.selectedIcon,
                  label: d.label,
                ),
              )
              .toList(),
        ),
      );
    }

    final colorScheme = Theme.of(context).colorScheme;
    final double sidebarWidth = _isHovered ? 220.0 : 68.0;

    return Scaffold(
      appBar: widget.appBar,
      body: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          MouseRegion(
            onEnter: (_) => setState(() => _isHovered = true),
            onExit: (_) => setState(() => _isHovered = false),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOutCubic,
              width: sidebarWidth,
              decoration: BoxDecoration(
                color: colorScheme.surface,
                border: Border(
                  right: BorderSide(
                    color: colorScheme.outlineVariant.withValues(alpha: 0.6),
                    width: 1,
                  ),
                ),
                boxShadow: _isHovered
                    ? [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.08),
                          blurRadius: 12,
                          offset: const Offset(2, 0),
                        ),
                      ]
                    : [],
              ),
              child: SafeArea(
                right: false,
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
                  itemCount: widget.destinations.length,
                  itemBuilder: (context, index) {
                    final dest = widget.destinations[index];
                    final isSelected = index == widget.selectedIndex;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Material(
                        color: isSelected
                            ? colorScheme.primaryContainer
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(12),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(12),
                          onTap: () => widget.onDestinationSelected(index),
                          child: Container(
                            height: 48,
                            padding: const EdgeInsets.symmetric(horizontal: 14),
                            alignment: Alignment.centerLeft,
                            child: SingleChildScrollView(
                              scrollDirection: Axis.horizontal,
                              physics: const NeverScrollableScrollPhysics(),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconTheme(
                                    data: IconThemeData(
                                      color: isSelected
                                          ? colorScheme.onPrimaryContainer
                                          : colorScheme.onSurfaceVariant,
                                      size: 24,
                                    ),
                                    child: isSelected
                                        ? dest.selectedIcon
                                        : dest.icon,
                                  ),
                                  AnimatedOpacity(
                                    duration: const Duration(milliseconds: 150),
                                    opacity: _isHovered ? 1.0 : 0.0,
                                    child: Padding(
                                      padding: const EdgeInsets.only(left: 14),
                                      child: Text(
                                        dest.label,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          fontSize: 14,
                                          fontWeight: isSelected
                                              ? FontWeight.w600
                                              : FontWeight.w500,
                                          color: isSelected
                                              ? colorScheme.onPrimaryContainer
                                              : colorScheme.onSurfaceVariant,
                                        ),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
          Expanded(child: widget.body),
        ],
      ),
    );
  }
}
