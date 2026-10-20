import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

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

  Widget _buildDesktopHeader(BuildContext context) {
    if (widget.appBar == null) return const SizedBox.shrink();

    Widget? titleWidget;
    List<Widget>? actions;

    if (widget.appBar is AppBar) {
      final bar = widget.appBar as AppBar;
      if (bar.title is Text) {
        final text = (bar.title as Text).data ?? '';
        titleWidget = Text(
          text,
          style: GoogleFonts.inter(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF0F172A),
            letterSpacing: -0.3,
          ),
        );
      } else {
        titleWidget = DefaultTextStyle.merge(
          style: GoogleFonts.inter(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: const Color(0xFF0F172A),
          ),
          child: bar.title ?? const SizedBox.shrink(),
        );
      }
      actions = bar.actions;
    } else {
      titleWidget = widget.appBar;
    }

    return Container(
      height: 60,
      padding: const EdgeInsets.symmetric(horizontal: 24),
      decoration: const BoxDecoration(
        color: Color(0xFFF6F8F8),
        border: Border(
          bottom: BorderSide(color: Color(0xFFE2E8F0), width: 1),
        ),
      ),
      child: Row(
        children: [
          if (titleWidget != null) titleWidget,
          const Spacer(),
          if (actions != null)
            IconTheme(
              data: const IconThemeData(
                color: Color(0xFF334155),
                size: 22,
              ),
              child: Theme(
                data: Theme.of(context).copyWith(
                  iconTheme: const IconThemeData(color: Color(0xFF334155)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: actions,
                ),
              ),
            ),
        ],
      ),
    );
  }

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

    final double sidebarWidth = _isHovered ? 220.0 : 68.0;

    return Scaffold(
      backgroundColor: const Color(0xFFF6F8F8),
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
                color: Colors.white,
                border: const Border(
                  right: BorderSide(
                    color: Color(0xFFE2E8F0),
                    width: 1,
                  ),
                ),
                boxShadow: _isHovered
                    ? [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.06),
                          blurRadius: 16,
                          offset: const Offset(3, 0),
                        ),
                      ]
                    : [],
              ),
              child: SafeArea(
                right: false,
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
                  itemCount: widget.destinations.length,
                  itemBuilder: (context, index) {
                    final dest = widget.destinations[index];
                    final isSelected = index == widget.selectedIndex;
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Material(
                        color: isSelected
                            ? const Color(0xFF0F5247).withValues(alpha: 0.1)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(10),
                          onTap: () => widget.onDestinationSelected(index),
                          child: Container(
                            height: 46,
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
                                          ? const Color(0xFF0F5247)
                                          : const Color(0xFF64748B),
                                      size: 22,
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
                                        style: GoogleFonts.inter(
                                          fontSize: 14,
                                          fontWeight: isSelected
                                              ? FontWeight.w600
                                              : FontWeight.w500,
                                          color: isSelected
                                              ? const Color(0xFF0F5247)
                                              : const Color(0xFF334155),
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
          Expanded(
            child: Column(
              children: [
                if (widget.appBar != null) _buildDesktopHeader(context),
                Expanded(child: widget.body),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
