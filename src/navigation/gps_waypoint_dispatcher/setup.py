from setuptools import find_packages, setup

package_name = 'gps_waypoint_dispatcher'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', ['config/campus_road_network.yaml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='FYP Team',
    maintainer_email='Kevinlasnh@outlook.com',
    description='GPS waypoint dispatcher for direct goals and road-network navigation',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'dispatcher_node = gps_waypoint_dispatcher.dispatcher_node:main',
            'goto_latlon = gps_waypoint_dispatcher.goto_latlon:main',
            'goto_name = gps_waypoint_dispatcher.goto_name:main',
            'stop = gps_waypoint_dispatcher.stop:main',
        ],
    },
)
