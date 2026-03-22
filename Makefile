SHELL := /bin/bash

.PHONY: setup build build-sensor build-perception build-planning build-navigation test launch-slam launch-explore launch-corridor launch-explore-gps launch-nav-gps launch-travel kill clean

setup:
	@echo ">>> 拉取第三方依赖..."
	git config --global --unset http.proxy || true
	git config --global --unset https.proxy || true
	vcs import < dependencies.repos
	@echo ">>> 安装 rosdep 依赖..."
	rosdep install --from-paths src --ignore-src -y --skip-keys "slam_toolbox navigation2"
	@echo ">>> 环境配置完成"

build:
	source /opt/ros/humble/setup.bash && \
	colcon build --symlink-install --parallel-workers 1

build-sensor:
	source /opt/ros/humble/setup.bash && \
	colcon build --symlink-install --packages-select \
		livox_ros_driver2 wit_ros2_imu wit_imu_traj \
		serial serial_reader serial_twistctl gyro_odometry \
		nmea_navsat_driver gnss_calibration wheeltec_gps_path nmea_msgs

build-perception:
	source /opt/ros/humble/setup.bash && \
	colcon build --symlink-install --packages-select \
		fastlio2 hba localizer interface pgo pgo_original \
		pointcloud_to_laserscan pointcloud_to_grid

build-planning:
	source /opt/ros/humble/setup.bash && \
	colcon build --symlink-install --packages-select \
		global2local_tf gnss_global_path_planner global_path_planning

build-navigation:
	source /opt/ros/humble/setup.bash && \
	colcon build --symlink-install --packages-select \
		waypoint_collector waypoint_nav_tool gps_waypoint_dispatcher

test:
	source /opt/ros/humble/setup.bash && \
	colcon test && colcon test-result --verbose

launch-slam:
	bash scripts/launch_with_logs.sh slam

launch-explore:
	bash scripts/launch_with_logs.sh explore

launch-corridor:
	bash scripts/launch_with_logs.sh corridor

launch-explore-gps:
	bash scripts/launch_with_logs.sh explore-gps

launch-nav-gps:
	bash scripts/launch_with_logs.sh nav-gps

launch-travel:
	bash scripts/launch_with_logs.sh travel

kill:
	pkill -f ros2 || true
	@echo ">>> 所有 ROS2 进程已终止"

clean:
	rm -rf build/ install/ log/
