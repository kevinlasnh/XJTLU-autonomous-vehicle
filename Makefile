SHELL := /bin/bash

.PHONY: setup build build-sensor build-perception build-planning build-navigation test launch-slam launch-explore launch-corridor launch-explore-gps launch-nav-gps launch-travel kill kill-runtime clean

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
	@$(MAKE) kill-runtime

kill-runtime:
	pkill -INT -f '[l]aunch_with_logs.sh|[m]onitor_corridor_status(\.py)?|[r]os2 bag|[r]viz2|[l]ivox_ros_driver2_node|[l]io_node|[p]go_node|[s]erial_twistctl_node|[n]mea_serial_driver|[p]lanner_server|[c]ontroller_server|[b]ehavior_server|[b]t_navigator|[s]moother_server|[v]elocity_smoother|[l]ifecycle_manager|[m]ap_server|[a]mcl|[c]omponent_container(_mt)?|[g]ps_route_runner|[g]ps_global_aligner|[r]obot_state_publisher|[p]ointcloud_to_laserscan' || true
	sleep 2
	pkill -KILL -f '[l]aunch_with_logs.sh|[m]onitor_corridor_status(\.py)?|[r]os2 bag|[r]viz2|[l]ivox_ros_driver2_node|[l]io_node|[p]go_node|[s]erial_twistctl_node|[n]mea_serial_driver|[p]lanner_server|[c]ontroller_server|[b]ehavior_server|[b]t_navigator|[s]moother_server|[v]elocity_smoother|[l]ifecycle_manager|[m]ap_server|[a]mcl|[c]omponent_container(_mt)?|[g]ps_route_runner|[g]ps_global_aligner|[r]obot_state_publisher|[p]ointcloud_to_laserscan' || true
	ros2 daemon stop >/dev/null 2>&1 || true
	@for dev in /dev/serial_twistctl /dev/wheeltec_gps; do \
		if [ -e "$$dev" ] && fuser "$$dev" >/dev/null 2>&1; then \
			fuser -k "$$dev" >/dev/null 2>&1 || true; \
		fi; \
	done
	@echo ">>> 导航相关残留进程已清理，ROS 2 daemon 已停止"

clean:
	rm -rf build/ install/ log/
