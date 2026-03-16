import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
import osmnx as ox
import networkx as nx
from pathlib import Path as PathlibPath

class PathPublisher(Node):
    def __init__(self):
        super().__init__('path_publisher_node')
        # 创建发布器
        self.publisher_ = self.create_publisher(Path, 'path_topic', 10)
        self.timer = self.create_timer(1.0, self.publish_path)  # 每秒发布一次
        self.get_logger().info("Path Publisher Node has been started.")
        
        # 获取当前脚本所在的目录
        base_dir = PathlibPath(__file__).resolve().parent
        osm_file_path = base_dir.parent / "map" / "map_simplified2.osm"  # 假设地图文件在 map 文件夹下

        # 从本地 OSM 文件加载图形数据
        self.graph = ox.graph_from_xml(osm_file_path)

        # 设置起始点和终点（根据用户提供的节点ID）
        self.start_node = 9536946732  # 起点为9536946732
        self.end_node = 8984639093    # 终点为8984639093

        # A*路径规划
        self.route = nx.astar_path(self.graph, self.start_node, self.end_node, weight='length')

        # 打印路径
        self.get_logger().info(f"A*路径规划结果: {self.route}")

        # 计算路径长度
        total_length = 0
        for u, v in zip(self.route[:-1], self.route[1:]):  # 遍历路径的边
            edge_data = self.graph[u][v]
            total_length += edge_data[0]['length']

        # 输出路径的总长度
        self.get_logger().info(f"总路径长度：{total_length:.2f} 米")

    def publish_path(self):
        # 创建 Path 消息
        path_msg = Path()
        path_msg.header.frame_id = "map"
        path_msg.header.stamp = self.get_clock().now().to_msg()

        # 将路径节点转化为 PoseStamped 并添加到 Path 消息中
        for node_id in self.route:
            pose = PoseStamped()
            pose.header.frame_id = "map"
            pose.header.stamp = self.get_clock().now().to_msg()
            
            # 获取节点坐标
            node_coords = (self.graph.nodes[node_id]['x'], self.graph.nodes[node_id]['y'])
            
            # 填充位置信息
            pose.pose.position.x = node_coords[0]
            pose.pose.position.y = node_coords[1]
            pose.pose.position.z = 0.0  # 设为 0，假设是二维路径

            # 将 PoseStamped 添加到 Path 消息
            path_msg.poses.append(pose)
        
        # 发布路径消息
        self.publisher_.publish(path_msg)
        self.get_logger().info("Publishing path")

def main(args=None):
    rclpy.init(args=args)
    node = PathPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
