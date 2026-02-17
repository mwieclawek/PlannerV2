import 'package:flutter/material.dart';

class AppLogo extends StatelessWidget {
  final double size;

  const AppLogo({super.key, this.size = 100});

  @override
  Widget build(BuildContext context) {
    // Dynamic Grid Concept: 3x3 grid of rounded squares
    // Creating "upward movement" using opacity and color
    final double itemSize = size / 3.4; // leave some spacing
    final double gap = size * 0.1;

    return SizedBox(
      width: size,
      height: size,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _buildRow(context, itemSize, gap, [0.4, 0.7, 1.0]),
          _buildRow(context, itemSize, gap, [0.2, 0.5, 0.8]),
          _buildRow(context, itemSize, gap, [0.1, 0.3, 0.6]),
        ],
      ),
    );
  }

  Widget _buildRow(BuildContext context, double size, double gap, List<double> opacities) {
    final colorScheme = Theme.of(context).colorScheme;
    
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: opacities.map((opacity) {
        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: colorScheme.primary.withOpacity(opacity),
            borderRadius: BorderRadius.circular(size * 0.3),
            boxShadow: [
              if (opacity > 0.6)
                BoxShadow(
                  color: colorScheme.primary.withOpacity(0.3),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
            ],
          ),
        );
      }).toList(),
    );
  }
}
