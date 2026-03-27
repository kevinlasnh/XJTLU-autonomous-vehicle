# Project Development Memo

## Development Backlog

### Highest Priority (Issues requiring immediate resolution, directly impacting system operation)

### Medium Priority (To be resolved in the short term, no direct impact on system operation)

### Low Priority (Nice to have, not essential)

## Miscellaneous
1. The PS2 controller uses AAA batteries
2. When reading code, do not prioritize understanding the math first; understand the overall code logic first, then study the math if necessary
3. Record every problem encountered during development (whether major or minor) in the ***Problems and Solutions During Development*** document; see that document for the recording format
4. Remember to enable the network port after rebooting the system
5. Avoid lifting the green cover on top of the vehicle unless absolutely necessary. Given that the ribbon cables are not fully secured, minimize interference -- otherwise sensor connection issues will be a hassle
6. Timestamps in log files should uniformly use ROS system timestamps in nanosecond format
7. RViz configuration is determined by the parameters in the RViz config files, e.g., pgo.rviz
8. After modifying files in a ROS package, update the corresponding CMakeLists.txt file accordingly and ensure the package dependencies are included
9. Use `-b humble` to clone the humble branch; make sure all cloned repositories are on the humble branch
10. pcl_viewer -bc 1,1,1 -ps 3 "/home/jetson/2025_FYP/all_kind_output_file/Other_File/SLAM_saved_MAPs/map.pcd"

## ROS2 Fundamentals
1. When connecting ROS2 topics, three things must be verified to match: first, the message type; second, the data content semantics; third, the QoS policy
2. Using `--symlink-install` during compilation ensures that subsequent source code changes are directly symlinked to the install folder, eliminating the need to copy to install again -- this is much faster
3. SDK stands for Software Development Kit -- a complete collection of tools needed to develop for a specific platform/service

## Memo and Log Writing
1. Logs can record any information, including problems, to-do items, and any thoughts
2. After a problem recorded in the log is resolved, summarize the problem and solution and record them in the memo

## AI Agent Usage
1. Properly maintain every chat record with AI agents; each chat record represents a work context

## Sensor Debugging
1. For all sensor operation commands, refer to the cmd_collection.md file
2. For sensor log naming conventions, refer to lines 55-63 of serial_twistctl_node
3. I cannot think of anything else for now; refer to the "Code Writing and Modification" section below for guidelines

## Code Writing and Modification
1. First and foremost, regardless of how you modify code, remember: never let AI make changes directly in your files without understanding the original code logic yourself. This is extremely bad for project code management and your own code comprehension.
2. AI prompt for code commenting: "Re-comment this entire file. Add detailed Chinese comments for every line of code. Delete all existing comments. Most importantly, do not modify any of my original code content or structure. Place comments on the line above each code line, not on the same line. Finally, normalize code blank lines and indentation in this file."
3. Regarding algorithm usage: first understand that before writing something yourself, check whether there is an open-source solution you can use directly
4. When writing comments in code, ***do not use*** multi-line comments -- use single-line comments!!! Otherwise you will regret it when compilation errors arise
5. When modifying code that would impact overall system operation, always make a backup first, then make changes in the new file
6. When making critical code changes, annotate them according to the following format: 1. Reason 2. Content 3. Impact. Follow this framework when writing code. If you do not know what to fill in temporarily, use # as a placeholder. Of course, if you have not thought through these three points before modifying code, there is no need to make the change.
7. If using an AI agent to modify code, clearly annotate what was changed by <which AI model> after the modification
8. When making batch repetitive code changes, it is best to build a workflow for the AI agent; after providing detailed descriptions, the changes can proceed under human supervision
9. Properly maintain every Copilot conversation; manual naming is recommended

## How to Run Group Meetings
1. Draft an outline before presenting at group meetings; do not rush in to speak unprepared
2. Always start recording before the group meeting begins -- you will absolutely not remember what was said otherwise

## How to Run Sub-group Meetings
1. I do not know either; it has been a while since we had one

## GitHub Code Pushing
1. Push code to GitHub before finishing work for the night. Remember this without fail -- otherwise the day you arrive at the lab and find the board dead with all code lost, you will regret it
2. Do not use a blanket commit message for all additions. Carefully review the changes in each file/group of files before writing the commit message. Do not be lazy.
3. GitHub commit messages should be written uniformly in English

## Vehicle Parameter Tuning
1. Before adjusting parameters, make sure you understand why the parameter needs adjustment
2. When adjusting a small number of parameters, comment out the original parameter settings rather than deleting the entire line
3. When adjusting a large number of parameters, make a backup of the original parameter file first, then make adjustments in the new file

## Vehicle Field Testing
1. PS2 controller usage for the car: 1. D-pad up/down adjusts wheel speed 2. Left stick maps to linear velocity 3. Right stick maps to angular velocity 4. L2 switches to onboard serial control mode 5. R2 switches to controller mode 6. Y button enables motors -- after pressing, the car cannot be pushed by hand 7. X button disables motors -- after pressing, the car enters free-rolling state and can be pushed 8. B button emergency stops the car (***do not use currently -- this button causes severe wheel reversal***). After switching to onboard serial mode with L2, you still need to press Y to enable the motors, otherwise the lower-level board cannot receive speed commands from the upper-level board. Similarly, X and B buttons still function in this mode, as the controller has the highest control priority over the car.
2. During autonomous driving, one person must always be ready to press the X button on the controller for immediate emergency stop
3. In emergencies, kick the red emergency stop button on the car body. This button stays pressed once activated and requires manual twist-release before the system can power up again
4. Before publishing the first path, switch the vehicle to serial remote control mode and enable the motors -- otherwise the vehicle will spin in place
5. Before publishing a goal point in RViz2, confirm that fix_frame is set to map, not odom or base_link. Selecting map means goal points are set relative to the vehicle's global map, so the car will drive to where you intend. In summary, the fix_frame parameter is the reference coordinate frame for goal point setting.

## Workspace Usage and File Storage
1. Top-level launch files should be stored uniformly in the ros2_launch_file repository
2. All log files should be saved in a dedicated subdirectory under the All_Log directory. Name the subdirectory to briefly describe the log content, e.g., reader_log. The log file directory is linked to a HuggingFace Git repository; ensure timely pushes.
3. All descriptive text files (including but not limited to .md, .txt, .csv, ...) should be stored uniformly in text_file, unless the file directly impacts node source code execution, in which case it may be stored within the node package
4. All non-log files should be stored uniformly in Other_File. This directory is linked to a GitHub Git repository; ensure timely pushes.
5. Any files without a clear category should be stored at: /home/jetson/2025_FYP/all_kind_output_file/thing_unknown

## Lab Usage Guidelines
1. Before leaving the lab, always check that the car's charging power supply is off and the car's battery is disconnected
2. Record the day's work log in the project development log before the end of the workday; start writing by 21:15 at the latest

## Linux System Usage
1. SSH password: Kk761201
2. For frequently used console commands, refer to the file /home/jetson/2025_FYP/all_kind_output_file/Other_File/text_file/cmd_collection.md
3. To connect via SSH outside the LAN, download Tailscale on your computer. URL: https://tailscale.com/download
4. After downloading, log in. Contact Kevin for the account credentials
5. Test non-LAN connectivity by pinging 100.97.227.24. If the ping succeeds, remote SSH is available. Then in VS Code: ssh jetson@100.97.227.24

## Linux VPN/Proxy Setup
1.

## Console Commands

### Miscellaneous
1. pkill -f ros2
2. ros2 daemon stop && sleep 2 && ros2 daemon start && sleep 2
3. ros2 daemon status
4. cd /home/jetson/2025_FYP/car_ws && colcon build --packages-select <pkg_name> --symlink-install
5. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && rviz2
6. cd /home/jetson/2025_FYP/car_ws && colcon build --symlink-install (compile entire workspace)
7. cat /etc/nv_tegra_release (check system JetPack version)
8. cd /home/jetson/2025_FYP/software_DL/'Clash for Windows-0.20.39-arm64-linux' (navigate to Clash download directory)
9. deactivate (exit virtual environment)
10. cd /home/jetson && cat /proc/device-tree/model (check development board model)

# Project Development Log

## 2025.11.10
1. Wrote standardized development documentation and development memos for the entire project

## 2025.11.11
1. The vehicle still exhibits the issue where the constructed map rotates along with the vehicle during self-rotation. This should not happen. The problem likely lies with PGO and IMU -- meaning the vehicle's SLAM functionality is broken and requires in-depth investigation. This issue is critical: without functional SLAM, the vehicle cannot operate at all.

## 2025.11.12
1. Identified the cause of the map rotating with the vehicle during self-rotation: it was a fix_frame parameter setting issue in RViz2

## 2025.11.13
1. Vehicle hardware ribbon cables may be loose; cables need inspection
2. Need to align sensor timestamps across all running components in the entire system
3. Parameter adjustments are too frequent; need to create a new YAML file to store all tunable parameters for non-Nav2 nodes (better to do this later, as it is still unclear which parameters need tuning)
4. Project development guidelines and master log files have been moved to the car_ws directory
5. The lower-level board's PID speed control has an issue: the emergency stop button trigger causes severe wheel reversal
6. Updated the classification scheme for project descriptive files and summarized current project files

## 2025.11.19
1. Did not work today; need to complete coursework assignments -- running out of time

## 2025.11.20
1. Doing assignments; will lose marks if not submitted

## 2025.11.21
1. Continuing assignments

## 2025.11.25
1. Re-checked the console workspace configuration
2. After making changes within a package, the CMakeLists.txt file must be updated accordingly; otherwise compilation will fail
3. Came up with an important development concept; recording from here onward
4. First, the global map is a GPS map, and a global path segment goes from one GPS point to another
5. Such global paths are generally long and need to be divided into multiple waypoints
6. The raw data for these waypoints is GPS data. The global path is then composed of several GPS points: a start point, multiple intermediate waypoints, and an endpoint
7. All these GPS points are stored in order in a suitable data structure. With each waypoint having a specific index, a reasonable global path can be perfectly described
8. However, note that these are just GPS points. GPS point data cannot be directly used as Nav2 goal point data -- it needs to be converted to Nav2's goal point format. Refer to Nav2_doc.md for Nav2's goal point format
9. This involves a goal point data conversion that is absolutely critical -- it directly determines whether the entire navigation system can be successfully deployed
10. There are two important conversions: first, using the initial GPS position to derive Nav2's initial pose; second, using the target GPS position to derive Nav2's target pose. Without these two poses, Nav2 cannot navigate from start to finish
11. I suddenly realized -- the conversion can work like this: when Nav2 starts up, it feeds back its global map initial pose (roughly [0,0,?] as an example) to the upper-layer GPS global planning system. The GPS global planning system then binds the current GPS position to the Nav2 initial pose feedback (binding x,y to longitude and latitude respectively, for example). Then the GPS global planning system back-calculates the Nav2 target pose for the next waypoint based on the binding between Nav2's initial pose and its bound GPS starting point. By extension, it derives the Nav2 target poses for all GPS waypoints along the route, stores them in a data structure in the corresponding order, and sends them to Nav2 sequentially for navigation
12. Under this system, Nav2 only needs to navigate from initial pose to target pose -- meaning **Nav2-scoped global map navigation is effectively local map navigation within the overall system framework**
13. Of course, there is an issue that must be discussed: if the overall system's global path is too long, Nav2 may need to reset its global map pose after completing navigation from one waypoint to the next -- re-initialize its pose, discard the previously stored global map coordinate frame, re-initialize its pose to [0,0,?] at the current waypoint, and begin new global map storage. This helps refresh memory and prevents memory overflow. If this operation is performed, all subsequent GPS waypoints' corresponding Nav2 target poses would need to be recalculated. Alternatively, computing only the next waypoint's Nav2 target pose each time seems viable too.
14. After navigating to a waypoint, the upper-layer GPS global navigation system sends the next waypoint's corresponding target pose to Nav2. Repeating this process navigates the entire global GPS path.
15. Returning to Nav2: it now only needs point-to-point navigation, meaning Nav2 only needs a single costmap for navigation.
16. Let us consider how Nav2 should plan its own global path between two GPS waypoints. If there is nothing between them, the path is a straight line (shortest distance between two points). When obstacles appear on the costmap, the path needs to go around them. At this point, we no longer need to distinguish between dynamic and static obstacles, because the path is refreshed at high frequency -- it just needs to ensure the vehicle can safely avoid all obstacles. With this, all the theory forms a closed loop.
17. Of course, Nav2's stock code does not support navigation with only a single costmap, so this involves significant work -- definitely requiring source-level modifications.
18. This approach has been validated as feasible by Grok, which generated detailed markdown documentation

## 2025.11.26
1. Could try converting all GPS waypoints to Nav2 waypoints at once, since Nav2 has waypoint functionality -- meaning multiple waypoints can be inserted into a single path. This would directly map all GPS waypoints to one-to-one Nav2 waypoints, letting Nav2 traverse the entire global path rather than navigating only waypoint-to-waypoint
2. This is still an experimental idea. If this works directly, it would be very simple. The concern is that feeding the entire global path into Nav2 might cause memory overflow
3. Need to do a project milestone summary today, then schedule meetings with supervisors

### Project Summary
1. Under the current system framework, extended vehicle operation may result in the vehicle stopping mid-path after a new goal point is set, while the costmap and global planning path continue updating
   1. Unresolved; this issue occurs infrequently, so no dedicated investigation has been conducted
   2. Possible causes: serial output node not sending velocity commands properly, or Nav2's velocity smoother or controller node freezing while the map layer continues running
2. Slow costmap dissipation: obstacle cost regions sometimes linger on the costmap after the obstacle has moved. These residual cost zones should theoretically disappear immediately and transition to traversable areas.
   1. This problem is quite troublesome, involving too many factors. Currently cannot guarantee 100% accurate high-frequency costmap refresh.
   2. Factors potentially involved: FAST-LIO2, PGO, and Nav2's own costmap node configuration
3. Global map sliding window causing map loss: this is no longer considered an issue, as the new system framework requires Nav2 to be configured this way
4. GPS coordinate to Nav2 target pose conversion: this is extremely critical -- directly determines whether the upper-layer global navigation system can interface with Nav2's navigation system
   1. May require designing a new conversion node; this could involve significant work
5. Nav2 reverse driving: previously attempted enabling Nav2's reverse driving feature, but after enabling it, Nav2 sometimes directly prefers driving the vehicle in reverse to track the path. This is unreasonable. The purpose of enabling reverse was to handle the special scenario where the vehicle enters a dead end and turning in place is difficult, requiring reverse to escape.
   1. Current solution: reverse driving is disabled; Nav2 is only allowed to turn in place for path re-tracking
   2. However, using only in-place rotation for escaping creates significant problems. The vehicle's rotation trajectory is not a perfect circle because the wheels do not produce equal force on both sides during in-place rotation, so the rotation center is not at the midpoint of the wheel axis projection. This could cause the vehicle to scrape obstacles on either side during in-place rotation escape maneuvers.
   3. Many rounds of tuning may be needed to achieve reasonable reverse driving
6. The costmap sometimes identifies certain signs on the ceiling as obstacles
   1. This issue has been resolved; the cause was the point cloud processing height parameter in Nav2
7. Nav2's velocity_smoother node closed-loop control currently has issues. Two input sources were tested for linear and angular velocity closed-loop control: first, raw wheel odometry feedback (linear and angular velocity data) from the C board -- the car mostly drives normally with this but is wobbly, and may suddenly spin wildly after driving for a while; second, FAST-LIO2 odometry data -- this should theoretically be very accurate, but currently connecting FAST-LIO2 output to closed-loop control prevents the vehicle from driving at all
   1. This issue also requires time to investigate
8. Nav2 does not natively support navigation with only a single costmap; special configuration is required, potentially involving significant modification work and parameter tuning
   1. This is quite troublesome. The current situation requires only the global map's coordinate frame and TF chain, without needing the global costmap or static grid map for navigation -- this requires special configuration
9. The PGO global planning node experiences message queue overflow during extended operation, causing message drops and subsequent TF chain breakage
   1. Temporarily resolved by increasing queue depth to 50, at the cost of increased memory usage
10. FAST-LIO2 and PGO node memory usage increases during extended operation, though not dramatically -- total system memory is around 5GB at startup, rising to 7GB after 20 minutes of operation
    1. Node source code could be further optimized by adding real-time memory release mechanisms
11. SLAM_toolbox severe memory overflow: manual mapping in the corridor outside the lab caused memory to fill completely
    1. Detailed analysis has not yet been conducted
12. LiDAR data degradation: when the LiDAR is too close to a wall, data degrades. This is critical for obstacle avoidance in narrow corridors.
    1. Switch to FAST-LIVO2 if possible
13. FAST-LIO2 output loss causes costmap loss. Sometimes the costmap disappears entirely; testing confirmed that restarting the FAST-LIO2 node resolves it
14. No URDF file found for this vehicle. Without it, the simulation platform cannot be built, reducing debugging efficiency -- every small adjustment requires manual testing, and the current testing area is limited
    1. This is a critical issue; a simulation testing platform is needed for efficient vehicle parameter testing
15. Nav2's waypoint system has not been enabled yet; development needs to begin
16. A new board is needed for camera development. Ideally a better development board; if not feasible, get another identical board and flash it with ROS1

17. Current system development can be roughly divided into two major tracks: first, [**Vehicle Perception** + **Nav2 Obstacle Avoidance**]; second, [**Upper-layer GPS Position Calibration** + **Global GPS Path Planning** + **GPS-to-Nav2 Waypoint Conversion**]
18. Still in the system building phase; personal workload must be large due to logical coupling issues
19. A simulation platform can be used for vehicle algorithm simulation

## 2025.11.27
1. Going forward, development needs to be modular in detail, especially when writing logs, so that each fine-grained module's development progress is clearly tracked
2. Remember to ask about the poster and reimbursement matters this afternoon
3. Ideally use one agent conversation per specific development scenario
4. Each development scenario essentially corresponds to a specific development problem, which should be recorded in a dedicated section of the current doc file's memo. Record all encountered problems there. When writing daily logs, organize each day's content by problem -- write daily logs in a problem-solving format.
5. The Global_cognition_and_Navigation_layer repository has been cloned to the src directory; Global_doc.md development file has been created
6. Had a group meeting and currently working on the meeting summary

## 2025.12.1
1. The development backlog in each doc file needs to record very detailed development issues
2. Project development backlog has been categorized into three priorities: highest, medium, and low
3. Kevin has a low-grade fever; development efficiency is reduced