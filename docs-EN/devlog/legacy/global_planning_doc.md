# Global Planning Layer Development Memo

## Development Modules

### Highest Priority (Issues requiring immediate resolution, directly impacting system operation)
1. How to ensure the GPS map is accurate
2. What if the starting GPS value does not match any predefined node -- can the A* algorithm use its own initial GPS value as the starting point for navigation

### Medium Priority (Issues to resolve in the short term, no direct impact on system operation)

### Low Priority (Better if resolved, acceptable if not)

## Miscellaneous
1.

# Global Planning Layer Development Log

## 2025.11.27
1. Created the doc file
2. A* algorithm feature points need to be extracted, otherwise the points are too dense

## 2025.12.01
1. GPS waypoint positions must be set in obstacle-free areas, otherwise Nav2 simply cannot navigate the vehicle onto these waypoints
2. This A* algorithm is still quite basic -- it only supports path planning on existing nodes, and all nodes are predefined with GPS values
3. How to ensure the GPS map is accurate
4. What if the starting GPS value does not match any predefined node
5. The waypoint issue no longer needs consideration since all GPS values are fixed; the only remaining issue is how to maintain Nav2's real-time global map pose correctness when real-time GPS drifts
