#!/usr/bin/env python3

import sys

from gps_waypoint_dispatcher.scene_runtime import default_scene_points_file, load_scene_points


def main() -> None:
    scene_points_file = sys.argv[1] if len(sys.argv) > 1 else str(default_scene_points_file())
    scene = load_scene_points(scene_points_file)
    destinations = sorted(scene["destination_names"].items(), key=lambda item: item[0])

    print(f"Scene: {scene['scene_name']}")
    print(f"File:  {scene_points_file}")
    if not destinations:
        print("Destinations: (none)")
        return

    print("Destinations:")
    for name, node_id in destinations:
        print(f"  {name} (node {node_id})")


if __name__ == "__main__":
    main()
