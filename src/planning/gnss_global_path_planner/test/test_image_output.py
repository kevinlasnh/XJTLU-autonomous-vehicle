import matplotlib.pyplot as plt

# 初始化交互模式
plt.ion()

# 创建绘图对象
fig, ax = plt.subplots(figsize=(10, 10))

# 示例数据
nodes = [(120.738366 + i * 0.0001, 31.274736 + i * 0.0001) for i in range(10)]
current_position = (120.738366, 31.274736)
target_position = (120.738466, 31.274836)

# 更新图像
for _ in range(10):
    ax.clear()
    ax.scatter(*zip(*nodes), c='blue', s=5, label='Nodes')
    ax.scatter(current_position[0], current_position[1], c='green', s=100, label='Current Position')
    ax.scatter(target_position[0], target_position[1], c='red', s=100, label='Target Position')
    ax.legend()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.pause(0.5)