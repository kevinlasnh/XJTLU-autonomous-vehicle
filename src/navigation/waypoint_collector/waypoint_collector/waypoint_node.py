#!/usr/bin/env python3
"""
航点收集器节点 (使用 FollowWaypoints)

功能说明:
- 使用 RViz "Publish Point" 工具点击添加中间航点
- 使用 RViz "2D Goal Pose" 设定最终目标并触发导航
- 机器人会依次导航到所有航点，最后到达最终目标
- 在 RViz 中可视化所有已添加的航点

作者: FYP Team
日期: 2025.12.01
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PointStamped, PoseStamped
from nav2_msgs.action import FollowWaypoints
from visualization_msgs.msg import Marker, MarkerArray


class WaypointCollectorNode(Node):
    def __init__(self):
        super().__init__('waypoint_collector')
        
        # 航点列表
        self.waypoints = []
        
        # 导航期间的航点副本（用于可视化）
        self.navigation_waypoints = []
        
        # 订阅 clicked_point (Publish Point 工具)
        self.clicked_sub = self.create_subscription(
            PointStamped,
            '/clicked_point',
            self.clicked_point_callback,
            10
        )
        
        # 订阅 goal_pose (2D Goal Pose 工具)
        self.goal_sub = self.create_subscription(
            PoseStamped,
            '/goal_pose',
            self.goal_pose_callback,
            10
        )
        
        # Action Client - 使用 FollowWaypoints
        self.nav_client = ActionClient(
            self,
            FollowWaypoints,
            'follow_waypoints'
        )
        
        # Marker 发布器 - 用于在 RViz 中可视化航点
        self.marker_pub = self.create_publisher(
            MarkerArray,
            '/waypoint_markers',
            10
        )
        
        self.get_logger().info('=' * 50)
        self.get_logger().info('航点收集器已启动 (FollowWaypoints)')
        self.get_logger().info('=' * 50)
        self.get_logger().info('操作说明:')
        self.get_logger().info('  1. 在 RViz 中使用 "Publish Point" 点击添加中间航点')
        self.get_logger().info('  2. 使用 "2D Goal Pose" 设定最终目标并开始导航')
        self.get_logger().info('  3. 机器人会依次经过所有航点到达最终目标')
        self.get_logger().info('  4. 在 RViz 中添加 MarkerArray 显示 /waypoint_markers')
        self.get_logger().info('=' * 50)

    def publish_waypoint_markers(self, waypoints_to_show=None):
        """发布所有航点的可视化标记到 RViz
        
        Args:
            waypoints_to_show: 要显示的航点列表，如果为 None 则使用 self.waypoints
        """
        if waypoints_to_show is None:
            waypoints_to_show = self.waypoints
        
        marker_array = MarkerArray()
        
        for i, wp in enumerate(waypoints_to_show):
            # 球形标记表示航点位置
            sphere_marker = Marker()
            sphere_marker.header.frame_id = 'map'
            sphere_marker.header.stamp = self.get_clock().now().to_msg()
            sphere_marker.ns = 'waypoint_spheres'
            sphere_marker.id = i
            sphere_marker.type = Marker.SPHERE
            sphere_marker.action = Marker.ADD
            sphere_marker.pose = wp.pose
            sphere_marker.scale.x = 0.15
            sphere_marker.scale.y = 0.15
            sphere_marker.scale.z = 0.15
            # 绿色表示中间航点，最后一个（终点）用红色
            if i == len(waypoints_to_show) - 1 and len(waypoints_to_show) > 1:
                # 红色终点
                sphere_marker.color.r = 1.0
                sphere_marker.color.g = 0.0
                sphere_marker.color.b = 0.0
            else:
                # 绿色中间航点
                sphere_marker.color.r = 0.0
                sphere_marker.color.g = 1.0
                sphere_marker.color.b = 0.0
            sphere_marker.color.a = 0.9
            marker_array.markers.append(sphere_marker)
            
            # 文字标记显示序号
            text_marker = Marker()
            text_marker.header.frame_id = 'map'
            text_marker.header.stamp = self.get_clock().now().to_msg()
            text_marker.ns = 'waypoint_labels'
            text_marker.id = i + 1000  # 避免 ID 冲突
            text_marker.type = Marker.TEXT_VIEW_FACING
            text_marker.action = Marker.ADD
            text_marker.pose.position.x = wp.pose.position.x
            text_marker.pose.position.y = wp.pose.position.y
            text_marker.pose.position.z = wp.pose.position.z + 0.25  # 文字在球上方
            text_marker.pose.orientation.w = 1.0
            text_marker.scale.z = 0.2  # 文字大小
            # 白色文字
            text_marker.color.r = 1.0
            text_marker.color.g = 1.0
            text_marker.color.b = 1.0
            text_marker.color.a = 1.0
            text_marker.text = f'#{i + 1}'
            marker_array.markers.append(text_marker)
        
        # 如果有航点，添加连接线
        if len(waypoints_to_show) > 1:
            line_marker = Marker()
            line_marker.header.frame_id = 'map'
            line_marker.header.stamp = self.get_clock().now().to_msg()
            line_marker.ns = 'waypoint_path'
            line_marker.id = 2000
            line_marker.type = Marker.LINE_STRIP
            line_marker.action = Marker.ADD
            line_marker.scale.x = 0.03  # 线宽
            # 黄色连接线
            line_marker.color.r = 1.0
            line_marker.color.g = 1.0
            line_marker.color.b = 0.0
            line_marker.color.a = 0.8
            line_marker.pose.orientation.w = 1.0
            
            for wp in waypoints_to_show:
                line_marker.points.append(wp.pose.position)
            
            marker_array.markers.append(line_marker)
        
        self.marker_pub.publish(marker_array)

    def clear_waypoint_markers(self):
        """清除 RViz 中的所有航点标记"""
        marker_array = MarkerArray()
        
        # 创建一个 DELETEALL 标记
        delete_marker = Marker()
        delete_marker.header.frame_id = 'map'
        delete_marker.header.stamp = self.get_clock().now().to_msg()
        delete_marker.action = Marker.DELETEALL
        marker_array.markers.append(delete_marker)
        
        self.marker_pub.publish(marker_array)

    def clicked_point_callback(self, msg: PointStamped):
        """收到 Publish Point 点击，添加为中间航点"""
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = msg.point.x
        pose.pose.position.y = msg.point.y
        pose.pose.position.z = 0.0
        pose.pose.orientation.w = 1.0
        
        self.waypoints.append(pose)
        
        self.get_logger().info(
            f'[+] 添加航点 #{len(self.waypoints)}: '
            f'({msg.point.x:.2f}, {msg.point.y:.2f})'
        )
        
        # 更新 RViz 可视化
        self.publish_waypoint_markers()

    def goal_pose_callback(self, msg: PoseStamped):
        """收到 2D Goal Pose，作为最终目标并触发导航"""
        self.waypoints.append(msg)
        
        total = len(self.waypoints)
        self.get_logger().info(
            f'[!] 收到最终目标: ({msg.pose.position.x:.2f}, {msg.pose.position.y:.2f})'
        )
        self.get_logger().info(f'[>] 开始导航，共 {total} 个航点')
        
        self.send_navigation_goal()

    def send_navigation_goal(self):
        """发送航点到 Nav2 FollowWaypoints"""
        if not self.waypoints:
            self.get_logger().warn('航点列表为空！')
            return
        
        self.get_logger().info('等待 FollowWaypoints Action Server...')
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('FollowWaypoints Action Server 不可用！')
            self.get_logger().error('请确保 Nav2 已正确启动')
            return
        
        # 构建 Goal
        goal_msg = FollowWaypoints.Goal()
        goal_msg.poses = self.waypoints.copy()
        
        # 保存航点副本用于导航期间的可视化（在清空 waypoints 之前）
        self.navigation_waypoints = self.waypoints.copy()
        
        # 立即发布可视化，确保航点显示
        self.publish_waypoint_markers(self.navigation_waypoints)
        
        # 打印所有航点
        self.get_logger().info('航点列表:')
        for i, wp in enumerate(self.waypoints):
            self.get_logger().info(
                f'  #{i + 1}: ({wp.pose.position.x:.2f}, {wp.pose.position.y:.2f})'
            )
        
        self.get_logger().info('发送导航目标...')
        send_future = self.nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )
        send_future.add_done_callback(self.goal_response_callback)
        
        # 清空航点列表（但保留 navigation_waypoints 用于可视化）
        self.waypoints.clear()

    def goal_response_callback(self, future):
        """Goal 被接受/拒绝的回调"""
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().error('导航目标被拒绝！')
            return
        
        self.get_logger().info('导航目标已接受，机器人开始移动...')
        
        # 保存 goal_handle 用于可能的取消操作
        self._goal_handle = goal_handle
        
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        """导航过程中的反馈 - 显示当前航点索引"""
        feedback = feedback_msg.feedback
        current_idx = feedback.current_waypoint
        self.get_logger().info(f'[导航中] 正在前往航点 #{current_idx + 1}')
        
        # 持续显示航点可视化
        if self.navigation_waypoints:
            self.publish_waypoint_markers(self.navigation_waypoints)

    def result_callback(self, future):
        """导航完成的回调"""
        result = future.result().result
        missed = result.missed_waypoints
        
        if len(missed) == 0:
            self.get_logger().info('=' * 50)
            self.get_logger().info('所有航点导航完成！')
            self.get_logger().info('=' * 50)
        else:
            self.get_logger().warn(f'导航完成，但有 {len(missed)} 个航点失败:')
            for idx in missed:
                self.get_logger().warn(f'  - 航点 #{idx + 1} 失败')
        
        # 导航完成后清除可视化
        self.clear_waypoint_markers()
        self.navigation_waypoints = []
        
        self.get_logger().info('可以继续添加新航点...')


def main(args=None):
    rclpy.init(args=args)
    node = WaypointCollectorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('节点关闭')
    
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
