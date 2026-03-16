# serial_twistctl
A ROS2 package that converts received twist topics into velocity commands in a specific format and sends them via serial port.

Please remember to grant permissions to the output serial port, taking /dev/ttyACM0 as an example:

```bash
sudo chmod 666 /dev/ttyACM0
