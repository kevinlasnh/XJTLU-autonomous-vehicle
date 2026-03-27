# Perception Layer Memo

## Development Backlog

### Highest Priority (Issues requiring immediate resolution, directly impacting system operation)
1.

### Medium Priority (To be resolved in the short term, no direct impact on system operation)
1. Add a topic output for the PGO node's global point cloud so it can be displayed in RViz
2. Remove the world_cloud publication from FAST-LIO2, as this data serves no useful purpose

### Low Priority (Nice to have, not essential)
1.

## Three-Way Fusion Algorithm Development Draft
1. First, we need to use GPS data to calibrate the robot's real-time pose in the global coordinate frame -- that is, to know where we are. Without GPS calibration of the real-time pose, the robot's global coordinate frame may drift from the physical world coordinate frame.
2. Second, we need to use GPS data to calibrate the target poses of our goal point and all waypoints in the global coordinate frame. This ensures we know where our targets are, so that positions in the physical world can be accurately mapped into the robot's global coordinate frame.
3. Both calibrations are indispensable and are key to ensuring complete navigation.

## Miscellaneous
1. Increasing the PGO message filter queue depth can effectively solve the costmap staleness or dissipation issue that occurs in Nav2 during extended operation.
2. body_cloud -- Relative position: fixed to the robot body, moves with the robot. Data characteristics: point cloud positions change with robot pose. Use cases: local perception, real-time obstacle avoidance, close-range obstacle detection.
3. world_cloud -- Relative position: fixed in the world coordinate frame, does not change with robot motion. Data characteristics: point cloud positions are stable in the world frame, used to build global maps. Use cases: SLAM mapping, global path planning, map saving.
4. The PGO node serves as the global optimization and loop closure detection module in the entire SLAM system. Its core purpose is to build and optimize global map consistency, eliminate odometry drift, and correct localization errors accumulated during extended FAST-LIO2 operation. When the robot returns to a previously visited location, it corrects the global map through loop closure detection and provides a globally consistent coordinate frame by publishing the map-to-odom TF transform as a global localization reference.
5. Point cloud map saving is based on the PGO node's pose graph optimization. A new keyframe is saved only when the robot moves more than 0.5 meters or rotates more than 10 degrees. Each individual sub-map is a keyframe, and the complete map is the global map formed by stitching all keyframes together.
6. If QoS parameters do not match, a topic will not receive any messages.
7. The slam_toolbox and pointcloud_to_laserscan nodes are pre-compiled binaries that come with the Humble installation. To modify their parameters, you only need to edit the corresponding YAML parameter files in the respective packages -- you cannot modify the node source code.

## Odom (Odometry) Data Interpretation
1. FAST-LIO2 outputs odom (odometry) data, which is extremely critical. This data contains the estimated position and orientation: position is **pose.pose.position (x, y, z)** -- these three values represent the robot's position in the world coordinate frame (i.e., in the global map frame); orientation is **pose.pose.orientation (x, y, z, w)** -- these four values represent the robot's orientation in the world coordinate frame (i.e., in the global map frame).
2. Odom data is computed through forward integration of IMU data, as part of the IESKF (Iterated Error-State Kalman Filter). The detailed computation process is explained below.
3. First, let us interpret the position data computation:
   1. Initially, position t_wi = 0 and velocity v = 0.
   2. Then the first batch of IMU data arrives.
   3. Input: linear acceleration acc and angular velocity gyro. The time step is dt, approximately 5ms. Both linear acceleration and angular velocity are presented in matrix form, containing data for the x, y, and z axes. Note carefully: at this point, both linear acceleration and angular velocity are in the robot's body coordinate frame.
   4. The next step is to convert the linear acceleration and angular velocity from the robot's body frame to the global frame. Compute: a_world = R_wi x (acc - ba) + g, where a_world is the linear acceleration in the global frame. R_wi (Rotate from World to IMU) is the rotation matrix from the global frame to the body frame, representing the robot's current pose and heading -- a 3x3 matrix obtained by integrating gyroscope angular velocity. ba is the accelerometer bias (zero offset) -- the reading when the true acceleration is zero may not be zero, and is part of the state. (acc - ba) represents the true acceleration after removing the bias. R_wi x (acc - ba) converts the acceleration from the body frame to the global frame. g is the gravity vector, typically [0, 0, -9.81] m/s^2, representing gravitational acceleration in the global frame; the sign of the z-component depends on the coordinate frame definition.
      1. The computation of the robot's rotation matrix R_wi can be broken down into seven steps.
      2. Before we begin, let us explain the meaning of the rotation matrix in detail:
      3. First: pre-input data -- gyroscope measurement matrix gyro and time step dt (the time difference between two consecutive IMU measurements).
      4. Step 1: Remove the gyro bias bg to obtain the true gyroscope data. Formula: **omega_true = gyro - bg**
      5. Step 2: Compute the angular increment. Formula: **delta_theta = omega_true x dt = [delta_theta_x, delta_theta_y, delta_theta_z]**
      6. Step 3: Exponential mapping to obtain the incremental rotation. Formula: **delta_R = Sophus::SO3d::exp(delta_theta).matrix()**. This step is the **core** of the computation; I cannot fully understand it at this time.
      7. Step 4: Update the rotation matrix. **R_wi = R_wi x delta_R**. The multiplication here concretely means rotating once more from the current pose R_wi. After this step, the predicted pose is obtained, but the predicted pose contains accumulated error. The error mainly comes from delta_R. Based on delta_R's formula **delta_R = Exp((omega - bg) x dt)** (involving sin and cos), with three separate rotation matrices maintaining rotations around the x, y, and z axes: first, the angular velocity omega has measurement noise (the acquired data may not be precise); then the bias bg may also have error (if bg is inaccurate); finally, the time step dt may have error (if the measurement is imprecise). These three types of errors accumulate over computation, causing the total error of the rotation matrix to grow ever larger.
      8. Step 5: LiDAR data arrives -- compute the pose residual. The main task here is to compare whether point cloud data can match existing map planes. This involves interpreting the point cloud data format and meaning, as well as computing residuals.
         1. LiDAR data measures distance and angles relative to itself, independent of any external coordinate frame. The specific measurements are: distance r (how far the laser traveled before reflecting back), horizontal angle theta (the horizontal direction of the laser emission), and vertical angle phi (the vertical direction of the laser emission). In other words, the raw data may look like **(r=5m, theta=30deg, phi=0deg)** -- this data is unrelated to the world coordinate frame.
         2. After this data returns, the raw measurements are converted to (x, y, z) in the LiDAR's local coordinate frame -- still unrelated to the world frame. The conversion uses the standard spherical-to-Cartesian coordinate formula: **(x=r*cos(phi)*cos(theta), y=r*cos(phi)*sin(theta), z=r*sin(phi))**. After this conversion, each point has coordinates in the robot's local frame.
         3. The question arises: we now need to transform these points into the global coordinate frame, because the SLAM map is built in the global frame. To convert real-time point cloud data into the global frame, we must use the robot's rotation matrix.
         4. The formula to transform points from the robot's local frame to the global frame is: **p_world = R_wi x p_lidar + t_wi**. To solve for a point's position in the global frame: take the vector from each point to the robot's local frame origin, multiply by the rotation matrix between the robot's body frame and the global frame, then add the translation vector from the robot's body frame origin to the global frame origin. This is a classic robotics coordinate frame problem.
         5. The next step is to use the IESKF (Iterated Error-State Kalman Filter) to solve for the pose correction. After each point is transformed from the body frame to the global frame, it is compared against known wall planes in the global map. However, since we are in SLAM real-time mapping mode, each newly added point in the global frame is compared against known planes in the saved global point cloud map. **So how are these known planes determined?** FAST-LIO2 uses an ikd-Tree data structure to store the scanned global point cloud map. This involves a dynamic local plane fitting algorithm, as follows:
            1. Step 1: For each new point, find its 5 nearest neighbors in the ikd-Tree.
            2. Step 2: Fit a local plane using these 5 selected points, represented by the standard equation **ax + by + cz + d = 0**.
            3. Step 3: Compute the **residual** of the new point to this plane. The **residual** is the distance from the new point to the fitted plane, using the point-to-plane distance formula **r = |n . (Q - P_bar)|**. If r = 0, the point lies on the plane (perfect, no residual). Any value greater or less than zero indicates a mismatch between the new point and the fitted plane (residual exists).
      9. Step 6: Pose correction. Using the formula **R_wi = R_wi x Exp(delta_theta_correction)**, the corrected pose is obtained. This involves the core of the Iterated Error-State Kalman Filter. The optimization objective is to **find the correction delta_theta that minimizes the sum of squared residuals of all points**. This is a nonlinear least-squares problem involving the Jacobian matrix H, which represents the partial derivative of the residual with respect to the pose correction: **H = d(residual) / d(pose)**. This Jacobian is derived from the point-to-plane distance formula. The physical meaning of this partial derivative is: when the pose changes slightly, how much does the residual change? Here, H is the sensitivity of the residual to the correction. When we make a small change to the pose (the pose correction), the residual changes linearly: **r_i(delta_theta) ~ r_i(0) + H . delta_theta**, which can be understood as **H . delta_theta = change in residual**. For multiple points in matrix form: **r = H . delta_theta + b**. To minimize the residual means finding the minimum of **||H . delta_theta + b||^2**. Expanding: **(delta_theta)^T . H^T . H . delta_theta + 2 . b^T . H . delta_theta + b^T . b**. Taking the derivative with respect to delta_theta gives the Normal Equation: **H^T . H . delta_theta = -H^T . b**, which rearranges to **delta_theta = (H^T H)^(-1) . H^T . b**, where **H+ = (H^T H)^(-1) H^T** is the pseudo-inverse (Moore-Penrose inverse) of H. Thus we obtain **delta_theta = H+ . b** -- the concrete computed value of the pose correction.
      10. Step 7: Update the rotation matrix R_wi using the pose correction delta_theta computed in the previous step, yielding the final pose. Formula: **R_wi = R_wi x Exp(delta_theta)**
   5. Next, velocity integration is performed using the global-frame acceleration a_world from the previous step: **v = v + a_world x dt**
   6. After velocity integration, position integration is performed using the velocity v from the previous step: **t_wi = t_wi + v x dt**. This yields the robot's relative position matrix in the global coordinate frame -- this position is estimated.
   7. Then point cloud data arrives for position residual computation. This is similar to the pose residual computation -- the main task is to check whether point cloud data can match existing map planes. The reason global position can also be back-calculated from point cloud residuals is that the formula **p_world = R_wi x p_lidar + t_wi** contains t_wi (the position vector). Since t_wi is included in the global point cloud position computation, after matching point cloud data to global map planes, the correction for the position vector t_wi can be back-calculated. The idea is: when the global position changes slightly, how does the residual change? The Jacobian for global position is actually simpler and less computationally expensive. After calibration using local point cloud information, we obtain: **delta_t_wi = H^(-1) x b**
   8. Then the global position vector is corrected using the computed correction: **t_wi = t_wi + delta_t_wi**
4. Now let us interpret the quaternion data. Quaternion data and rotation matrix data are interconvertible.
   1. To compute a quaternion, first think about robot rotation. For any rotation, we need to know two things: which axis to rotate around, and how many degrees to rotate (correct idea, but with different implementation methods).
   2. w, x, y, z are all real numbers. Any 3D rotation can be uniquely represented by a unit axis u=(Ux, Uy, Uz) and an angle theta (radians). w: cos(theta/2) determines only the rotation magnitude, range [-1,1]. x, y, z: sin(theta/2) multiplied by the three axis components together determine the rotation direction; they are not coordinates or independent vectors, but scalar coefficients of direction x half-angle sine.
   3. Note that the quaternion method finds a single unique rotation axis u and uses rotation angle theta for a single rotation!! w itself is not an angle, and (x,y,z) are not the axis used directly!! They together encode the axis and angle. The actual rotation axis is:
       u=(x,y,z)/sqrt(x^2+y^2+z^2), rotation angle theta=2arccos(w)
   4. Important constraint: ||q||^2 = w^2 + x^2 + y^2 + z^2 = cos^2(theta/2) + sin^2(theta/2) . |u|^2 = 1. This forces it onto the 4D unit sphere, compressing 4 parameters into 3 effective degrees of freedom, which exactly matches the 3 degrees of freedom needed for 3D rotation.
   5. Given the rotation axis matrix u and rotation angle theta, the quaternion can be computed: **q = w + xi + yj + zk = [w, x, y, z] = [q_w, q_x, q_y, q_z]**. A unit quaternion (|q|=1) looks like: **q = cos(theta/2) + sin(theta/2)(Ux*i + Uy*j + Uz*k)**. Note that theta is the rotation angle, and (Ux, Uy, Uz) are the unit vectors of the three rotation axes -- the 3 components of the new axis vector u. Finally: q = cos(theta/2) + sin(theta/2)*u, where cos(theta/2) -> w, sin(theta/2)*u -> (x,y,z).
   6. The rotation matrix R is a 3x3 orthogonal matrix, R=Rz(psi)*Ry(theta)*Rx(phi). Its properties: R^T*R=I, det(R)=1. For any vector v, the rotated vector v'=Rv can transform a vector from the body frame to the world frame or vice versa. It and the quaternion are essentially different parameterizations of the same rotation.
   8. Physical meaning: Column 1 of R = the body-frame x-axis unit vector in the world frame. Column 2 of R = the body-frame y-axis unit vector in the world frame. Column 3 of R = the body-frame z-axis unit vector in the world frame.
   9. Rodrigues' rotation formula: v' = cos(theta)*v + (1-cos(theta))(u.v)u + sin(theta)(u x v). u is the given rotation axis vector (Ux, Uy, Uz). The resulting R can transform any vector v to v'. Starting from a unit quaternion (w,x,y,z), directly substituting the implicit quantities cos(theta) = 2w^2 - 1 and sin(theta) = 2w into Rodrigues' formula gives the rotation matrix R: diagonal elements R_ii = 1-2(y^2+z^2), 1-2(x^2+z^2), 1-2(x^2+y^2); off-diagonal elements R_12 = 2(xy - wz), R_13 = 2(xz + wy), R_21 = 2(xy + wz), R_23 = 2(yz - wx), R_31 = 2(xz - wy), R_32 = 2(yz + wx).
   10. Reverse derivation: obtaining w, x, y, z from R: first compute the trace t = R_11 + R_22 + R_33. If t > 0, let s = 2*sqrt(t+1), then directly obtain w = (t+1)/s, x = (R_32 - R_23)/s, y = (R_13 - R_31)/s, z = (R_21 - R_12)/s. If t <= 0, switch to the branch based on R's largest diagonal element, compute s, and similarly use the corresponding column elements and sums/differences of R to calculate w, x, y, z. The entire process uses only R's entries without trigonometric functions, yielding the unit quaternion.
   11. Euler angles: parameterize a 3D rotation by decomposing it into three single-axis rotations executed in a fixed order -- each axis rotates by its corresponding angle. The common order is ZYX (yaw psi, pitch theta, roll phi). Performing three successive axis rotations in order, substituting the three angles (psi, theta, phi) into the corresponding basic rotation matrices Rz(psi), Ry(theta), Rx(phi): R = Rz(psi)*Ry(theta)*Rx(phi), yielding the rotation matrix expressed by these three angles. Conversely, the angles psi, theta, phi can be recovered from R's elements using inverse tangent combinations. This method suffers from gimbal lock; in pose control applications, rotation matrices and quaternions are predominantly used.
   12. Gimbal lock: When the middle pitch angle theta = +/-90 degrees in ZYX Euler angles, the rank of the Jacobian of the rotation mapping R(psi, theta, phi) = Rz(psi)*Ry(theta)*Rx(phi) drops from 3 to 2. Columns 1 and 3 become linearly dependent, psi and phi merge into a single degree of freedom (psi - phi), and the 3D control space collapses into a 2D plane. Alternatively: yaw and roll become fully coupled into a fixed angle (psi + phi) -- no matter how you independently change yaw or roll, the effect is identical, so the total degrees of freedom drop from 3 to 2. When pitch = 90 degrees, theta = pi/2, sin(theta) = 1, cos(theta) = 0, substituting into the formula above:
R = [ 0 -sin(psi+phi) cos(psi+phi)
      0  cos(psi+phi) sin(psi+phi)
      -1    0         0    ]

## FAST-LIO2 Algorithm Detailed Walkthrough

### Phase 0: System Initialization (executed once at startup)
1. Collect the first N frames of IMU data (default 20 frames)
2. Compute the mean acceleration to estimate gravity direction
3. Compute the mean angular velocity to estimate gyroscope bias bg
4. Set the initial pose R_wi (aligning the Z-axis with the gravity direction)
5. Initialize the covariance matrix P
6. Receive the first point cloud frame and build the initial ikd-Tree map
7. Initialization complete; enter normal mapping mode

### Phase 1: Data Reception and Synchronization (executed per frame)
1. IMU data (~200Hz) continuously enters imu_buffer
2. LiDAR data (~10Hz) continuously enters lidar_buffer
3. Wait for a complete point cloud frame to arrive
4. Collect all IMU data within the time range of that point cloud frame (approximately 10-20 samples)
5. Package into SyncPackage { cloud, imus[], time_start, time_end }

### Phase 2: IMU Forward Integration + Pose Sequence Generation
1. First, use IMU forward integration to obtain a predicted pose (not necessarily accurate)

#### 2.1 Integration Process (executed for each IMU sample)
1. Remove gyroscope bias: **omega_true = gyro - bg**
2. Compute angular increment: **delta_theta = omega_true x dt**
3. Exponential mapping to obtain rotation increment: **delta_R = Exp(delta_theta)**
4. Update rotation matrix: **R_wi = R_wi x delta_R**
5. Remove accelerometer bias and transform to world frame: **a_world = R_wi x (acc - ba) + g**
6. Velocity integration: **v = v + a_world x dt**
7. Position integration: **t_wi = t_wi + v x dt**
8. **Save the current pose to poses_cache** (used for point cloud de-distortion)

#### 2.2 Integration Results
- Obtain a sequence of N poses at different time instants: poses_cache
- Obtain the predicted final pose (at the end of the scan)

### Phase 3: Point Cloud De-distortion
1. Use the predicted pose sequence to de-distort the point cloud, making it approximately correct

#### 3.1 Why De-distortion Is Needed
- A point cloud scan takes ~100ms to complete one revolution
- During this time the vehicle is moving; the vehicle pose is different at each point's scan time
- Without correction, the point cloud would be "smeared" together

#### 3.2 De-distortion Process (executed for each point)
1. Get the point's scan timestamp t_point (stored in the curvature field)
2. Look up the corresponding IMU pose (R_point, t_point) from poses_cache
3. Compute the point's world coordinates at its scan time: **p_world = R_point x p_local + t_point**
4. Transform to a unified coordinate frame at scan end time: **p_corrected = R_end^(-1) x (p_world - t_end)**
5. Update the point coordinates

### Phase 4: IESKF Iterative Optimization (Core)
1. Match the de-distorted point cloud against the previously accumulated SLAM map (ikd-Tree)
2. Compute residuals and solve for the pose correction
3. Apply the correction to the predicted pose, obtaining the corrected vehicle body frame pose relative to the global frame
4. Check whether the pose correction is small enough:
   - If sufficiently small (rotation < 0.01 deg, translation < 0.015 cm) -> exit iteration
   - If the correction is large -> return to step 4.1, recompute with the corrected pose, repeat

#### 4.1 Transform Point Cloud to World Frame
- For each point: **p_world = R_wi x (R_il x p_body + t_il) + t_wi**
- Where R_wi, t_wi are the current estimated pose (continuously corrected during iteration)

#### 4.2 Nearest Neighbor Search in ikd-Tree
- For each world-frame point, find the 5 nearest points in the map
- Formula: **neighbors = ikd_tree.nearest_search(p_world, k=5)**

#### 4.3 Plane Fitting + Residual Computation
1. Fit a local plane using the 5 nearest neighbors: **ax + by + cz + d = 0**
2. Get the plane normal vector: **n = [a, b, c]**
3. Compute point-to-plane distance (residual): **residual = n . p_world + d**
   - residual = 0 means the point is on the plane -- perfect match
   - residual != 0 means there is error

#### 4.4 Compute Jacobian Matrix + Build Equation
1. Jacobian matrix: partial derivative of residual with respect to pose: **J = d(residual) / d[R_wi, t_wi]**
2. Physical meaning: how much does the residual change when the pose changes slightly
3. Accumulate contributions from all valid points:
   - **H += J^T x J** (Hessian matrix)
   - **b += J^T x residual** (residual vector)

#### 4.5 Solve for Correction
- Least-squares solution: **delta_x = -H^(-1) x b**
- delta_x contains:
  - delta_theta = [delta_theta_x, delta_theta_y, delta_theta_z] rotation correction
  - delta_t = [delta_t_x, delta_t_y, delta_t_z] translation correction

#### 4.6 Update Pose
- Rotation update: **R_wi = R_wi x Exp(delta_theta)**
- Translation update: **t_wi = t_wi + delta_t**
- Also update other states: velocity v, biases bg, ba, etc.

#### 4.7 Check Convergence
- Convergence criteria: **|delta_theta| < 0.01 deg && |delta_t| < 0.015 cm**
- Not converged -> return to 4.1, continue iterating
- Converged -> exit iteration, output final pose

### Phase 5: Map Update
1. Trim the local map: delete points too far from the robot, keeping the map window following the robot
2. Incrementally add new points: transform the de-distorted point cloud to the world frame and add to the ikd-Tree

### Phase 6: Result Publication
1. Publish TF transform: world -> body (position + quaternion pose)
2. Publish odometry: /lio_odom (pose + twist)
3. Publish point clouds:
   - /body_cloud -> body-frame point cloud (for PGO), i.e., point cloud relative to the robot's local frame
   - /world_cloud -> world-frame point cloud (for visualization), i.e., point cloud transformed from the local frame to the global frame
4. Publish path: /lio_path (historical trajectory)

### Key Insight: Why Only Optimize the Final Pose?
1. IMU measures **relative changes** (very accurate), not absolute pose
2. All intermediate poses = final pose - relative changes
3. After correcting the final pose, all intermediate poses are **automatically corrected**
4. Once intermediate poses are corrected, point cloud de-distortion is also **automatically more accurate**
5. This is what "error state" means in IESKF: only estimate the error, not the entire state

### Algorithm Core Summary
```
Executed every ~100ms:
  Collect data -> IMU integration -> Point cloud de-distortion -> IESKF iterative optimization -> Update map -> Publish results -> Loop
```

**FAST-LIO2 = IMU high-frequency integration prediction + LiDAR per-frame correction + iterative optimization + incremental mapping**

## PGO Node Functions
1. The PGO node's basic functions are: collecting keyframes, detecting loop closures, performing graph optimization, and publishing the map-to-odom TF transform chain.
2. The PGO node's keyframe collection strategy works as follows: point cloud keyframe data comes from FAST-LIO2's body_cloud topic, using point cloud data entirely in the robot's body frame. It simultaneously receives odom data from FAST-LIO2, which contains the global pose corresponding to each keyframe's point cloud. Keyframe collection is based on the vehicle's movement and rotation, since point cloud data volume is large and most frames do not need to be saved -- only the most critical ones. **In fact, the PGO node receives every frame but only saves keyframes.**
3. Having both body-frame point cloud data and corresponding odom information ensures that even without loop closure triggering, the map can be saved by converting local point cloud data to the global map, thus saving a complete SLAM global map.
4. The PGO global SLAM map is stored in the `m_key_poses[]` list, where each element contains: pose information (r_local, t_local, r_global, t_global), timestamp, and body_cloud point cloud. During loop closure search, a KdTree is **temporarily constructed** (containing only position coordinates x, y, z) for fast lookup of nearby historical frames, and discarded after use. When saving the map, this list is traversed and point clouds are stitched using optimized poses. In the saved patches folder, each .pcd file is a keyframe's point cloud data, map.pcd is the complete map with all keyframes stitched together, and poses.txt contains each keyframe's pose information.
5. The core of PGO is the loop closure detection function. This roughly consists of three steps:
   1. Step 1: Identify the loop closure. The key problem here is how the robot knows it has been to this location before. The robot only knows its current position, current point cloud, and historical keyframes (previously saved positions + point clouds). Loop closure identification has three sub-steps:
      1. Sub-step 1: Position coarse filtering -- are there historical frames nearby? This checks whether there are previously visited locations near the robot's current position. The specific method is to store all historical keyframes in a KdTree (an efficient search structure), excluding the latest keyframe itself, then search using the current position to see if there are historical frames within a 15-meter radius.
      2. Sub-step 2: Time filtering -- is the historical frame from a long time ago? This ensures that the loop closure represents actually having traveled a large loop and returned, rather than an immediate loop at the start.
      3. Sub-step 3: Point cloud confirmation -- is the surrounding environment identical? This is the final loop closure check. Position proximity plus time gap is not enough, because odom can drift and the position may be wrong -- relying on position alone might produce a false loop closure. The point cloud confirmation logic compares whether the scanned point cloud shapes of the two frames approximately match. The PGO node uses the ICP (Iterative Closest Point) algorithm for point cloud alignment. ICP only aligns the latest frame with the historical frame -- just these two frames participate. The subsequent task of adjusting the positions of multiple frames to correct the entire graph is handled by the GTSAM graph optimization algorithm.
         1. The ICP algorithm works by continuously rotating and translating the latest frame's point cloud to find a pose that matches the historical frame's point cloud.
         2. ICP outputs three things: first, an alignment success flag indicating whether alignment succeeded; second, an alignment score -- a value representing the average distance from each transformed source point to its nearest target point after ICP completes (lower score means better alignment between the two frames, more reliable loop closure, corresponding to the `loop_score_tresh: 0.15` parameter in the PGO YAML); third, the transformation matrix T -- the transform needed to "align" the source point cloud to the target point cloud, i.e., the relative pose difference between the current frame and the historical frame. This matrix is output to GTSAM as a **Loop Factor** constraint.
   2. The next step is adding loop closure constraints to the factor graph.
   3. Then GTSAM graph optimization is launched. This algorithm's function is to straighten the entire graph. The ICP algorithm aligned the historical frame with the current frame, but this alignment is only local -- the overall graph still has errors. The graph optimization algorithm's function is to straighten the entire graph so that all keyframes satisfy these loop closure constraints, making the overall map more accurate.
      1. First, what is in the factor graph? The graph's nodes are each keyframe's pose; the edges are constraints. There are three types of constraints:
         1. Type 1: Prior factor -- only connected to frame 0, meaning the first frame must be fixed at the origin.
         2. Type 2: Odometry factor -- from frame i to frame i+1, i.e., the relative pose between adjacent frames. Data comes from FAST-LIO2's odom output.
         3. Type 3: Loop factor -- relative pose between frame i and frame j. Data comes from the PGO node's loop closure detection, i.e., between the historical frame and the latest frame, from the ICP algorithm.
      2. Overall, GTSAM's objective is to minimize the total error of all constraints. Imagine: odometry constraints are like springs connecting adjacent frames; loop closure constraints are like a new spring pulling the current frame and historical frame together. But when the loop closure spring pulls, it does not only move the current frame -- all frames along the spring chain are pulled, each spring stretched slightly, until a state is reached where the total spring force is minimized.
      3. GTSAM graph optimization outputs the optimized global poses of all keyframes -- a **list** containing optimized rotation **R_global** and translation **t_global** for each keyframe. These values can replace the original odom values output by FAST-LIO2 for each frame, and the node uses these values to update each frame's r_global and t_global.
      4. The next step is computing the offset -- the total drift amount, specifically for the latest frame (the robot's current newest pose). This **offset** corrects drift within the built map scope, discovered through loop closure detection. It can only guarantee internal map consistency, not external consistency -- it cannot guarantee absolute position correctness.
      5. The final step is publishing the TF transform chain from map to odom. This transform is the offset computed in the previous step. Its purpose is to correct the odom pose output by FAST-LIO2, yielding a more accurate odom pose.

## TF Transform Chain

### Basic Concepts
1. The essence of TF is telling you where one coordinate frame is and which direction it faces relative to another coordinate frame.

### odom to base_link
1. The odom-to-base_link transform contains two pieces of information.
2. First: the relative position from the local frame to the global frame, represented by the **t_wi** position vector.
3. Second: the rotation of the local frame relative to the global frame, represented by the **R_wi** rotation matrix (in quaternion form).

### map to odom
1. The map-to-odom transform contains the offset information -- the drift of the robot's latest odom pose relative to the global map.
2. This offset is computed by the PGO node's loop closure detection and GTSAM graph optimization algorithm.

***Combining these two TF chain segments yields the true latest global pose.***

## Relationship Between FAST-LIO2 and PGO Nodes
1. The FAST-LIO2 node provides two types of data to the PGO node: body_cloud and odom, supplying real-time point cloud data and odometry data.

## Console Commands

### Miscellaneous
1. cd /home/jetson/2025_FYP/car_ws && colcon build --packages-select fastlio2 pgo --symlink-install
2. pcl_viewer /home/jetson/2025_FYP/car_ws/SLAM_saved_MAPs/<map_file_name.pcd>
3. ros2 topic echo /scan > /dev/null &
4. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch fastlio2_pointcloud_to_laserscan test_pointcloud_to_laserscan.py (point cloud to laser scan node)
5. ros2 service call /pgo/save_maps interface/srv/SaveMaps "{file_path: '/home/jetson/2025_FYP/car_ws/SLAM_saved_MAPs', save_patches: true}"
6. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch pgo pgo_launch.py
7. ros2 service call /pgo/save_maps interface/srv/SaveMaps "{file_path: '/home/jetson/2025_FYP/all_kind_output_file/Other_File/SLAM_saved_MAPs/<file_dir>', save_patches: true}"
8. pcl_viewer /home/jetson/2025_FYP/all_kind_output_file/Other_File/SLAM_saved_MAPs/3D/<file_dir>/map.pcd
9. cd /home/jetson/2025_FYP/car_ws && colcon build --packages-select fastlio2_pointcloud_to_laserscan --symlink-install (compile conversion node)
10. ros2 run nav2_map_server map_saver_cli -f /home/jetson/2025_FYP/all_kind_output_file/Other_File/SLAM_saved_MAPs/2D/<file_dir>/map (save the SLAM-scanned 2D occupancy grid map)
11. ros2 topic hz /scan (check the scan topic output rate of the 3D-to-2D laser conversion node)
12. ros2 topic echo /map_metadata --once (check whether SLAM toolbox is outputting a map)
13. cd ~/2025_FYP/car_ws && colcon build --packages-select fastlio2_slam_toolbox ros2_launch_file --symlink-install --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3 (compile SLAM toolbox node)
14. cd /home/jetson/2025_FYP/car_ws && source install/setup.bash && ros2 launch fastlio2 lio_launch.py

### Build
1. cd /home/jetson/2025_FYP/car_ws && colcon build --symlink-install --packages-select pointcloud_to_laserscan && source install/setup.bash

# Perception Layer Development Log

## 2025.11.11
1. Added log file writing functionality to the FAST-LIO node and verified that the node's message publication timestamps use ROS system standard time
2. Added logging functionality to the PGO node and verified that its message publication uses the received message's timestamp
3. Added a parameter-based toggle for log file writing to each logging-capable node, allowing log writing to be disabled before runtime to reduce system load
4. Increased the PGO message queue depth to 50, resolving message loss caused by queue overflow during operation
5. Observed that GPU usage accumulates over runtime; need to find a way to allow FAST-LIO2 and PGO to discard unnecessary memory during operation
6. The PGO node still produces errors during extended operation: [rviz2-3] [INFO] [1763019376.264879975] [pgo.rviz2]: Message Filter dropping message: frame 'base_link' at time 1763019375.271 for reason 'discarding message because the queue is full' [rviz2-3] [INFO] [1763019376.265166398] [pgo.rviz2]: Message Filter dropping message: frame 'odom' at time 1763019375.271 for reason 'discarding message because the queue is full'

## 2025.11.13
1. Updated FAST-LIO2 node execution frequency to 50 Hz, increasing message publication rate to support faster costmap updates
2. Reduced PGO node message publication frequency to 20 Hz to alleviate unnecessary publication overhead

## 2025.11.18
1. Created a new "FASTLIO2 development" conversation session in Copilot, dedicated to handling code development issues in the FASTLIO2 perception package
2. Need to revisit how the localizer package is used

## 2025.11.23
1. LiDAR data degrades when the sensor is too close to a wall
2. Adjusted PGO keyframe collection angle and distance thresholds to 5 degrees and 0.1 meters respectively, enabling more frequent keyframe saving
3. Successfully scanned a corridor map near the CB studio with good results
4. Planning to use SLAM_toolbox for mapping to obtain 2D maps of the current scene
5. Modified the pointcloud_to_laserscan node's QoS parameters to Best Effort for compatibility
6. Explicitly set the scan topic output QoS to Best Effort in the launch file for compatibility
7. The scan topic now outputs successfully
8. The SLAM_toolbox node parameters also need TF configuration matching Nav2 to work correctly
9. Successfully generated a 2D occupancy grid map via SLAM toolbox; verified the map quality is good
10. Do not name your own packages the same as system packages, as this prevents the system from identifying them correctly
11. Created the fastlio2_slam_toolbox package, which stores the corresponding YAML files
12. Both slam_toolbox and pointcloud_to_laserscan packages now use cloned source code instead of the Humble pre-compiled binaries
13. Went out to scan with SLAM; ran out of memory halfway through
14. After analysis, slam_toolbox cannot replace the PGO node
15. The current option is to try connecting the scan topic into Nav2 to see if it performs better than feeding point clouds directly into Nav2

## 2025.11.27
1. Modified the FAST-LIO2 RViz configuration; point cloud images now display correctly
2. Should we tightly couple GPS, point cloud, and IMU information? This needs further thought
3. Recording some thoughts on coordinate frame position calibration for the new system architecture:
   1. During long-distance one-way navigation with Nav2, the PGO node has difficulty triggering loop closure detection
   2. PGO can only guarantee relative map consistency -- it can ensure the map is self-consistent and optimize the relative trajectory shape, but it **cannot guarantee that the map perfectly aligns with the real-world coordinate frame** -- it cannot determine the trajectory's absolute position
   3. This problem becomes severe during ultra-long-distance one-way navigation
   4. Therefore, an absolutely accurate data reference is needed. For long-distance navigation, this data is GPS
   5. During long-distance navigation, the GPS start point of the route -- the GPS point aligned with Nav2's global map initial pose [0,0,0] -- must be absolutely precise. Before the route is completed, the binding relationship and specific values between this GPS point and Nav2's global map initial pose [0,0,0] must be persistently maintained, as this is critical for real-time position feedback calibration
   6. Since the vehicle navigates through Nav2's global coordinate frame, any deviation between this global frame and the real-world physical frame means the vehicle's navigation no longer matches real-world physical features
   7. At this point, the following method can be used for real-time global coordinate position calibration, leveraging precise GPS satellite data
   8. First, we must make an assumption: the GPS data is absolutely precise with no error. Only then can we begin the derivation. If GPS data is perfectly accurate, then all marked points on the original GPS map have perfectly accurate GPS values. This means our initial pose GPS value and target pose GPS value are both perfectly accurate, making the global path's start and end points fully determined. At this point, all intermediate waypoints along the global path are also fully determined and precise. Then, based on the initial pose GPS value, the poses of all waypoints and the endpoint are back-calculated, yielding a global coordinate frame that can be aligned with Nav2's global frame.
   9. Now comes a critical issue: the vehicle's position in Nav2's global frame may drift, causing Nav2's global frame to deviate from the real-world physical frame. This drift means the GPS back-calculated value from the vehicle's current global-frame coordinates differs from the vehicle's actual GPS value. Think of it like driving a car with all windows covered, given only a built-in screen showing a virtual route -- you are told the path and how to drive. You can see on the screen how far you have driven along the route, but you cannot be sure you have driven that far in the real world. The correct approach is to periodically uncover the car to check whether your screen position matches your real-world position -- this is equivalent to using the vehicle's real-time GPS value, referenced against the binding anchor point between the global map's initial pose and initial GPS position, to back-calculate the current real-time pose on Nav2's global map.
   10. This idea is still quite idealistic, because GPS itself has non-trivial error. Therefore this method can only serve as a reference, not as an absolutely precise calibration means.
4. Currently there are two approaches: first, modify the existing system; second, pull in an external library. The first approach would involve a very large workload.

## 2025.11.28
1. Studied odom data computation
2. Summarized the most critical fusion algorithm approach so far
3. The Decay Time parameter in RViz determines what the map looks like; a larger value produces a better visual stacking effect
4. The ikd-tree in FAST-LIO2 stores local point cloud data for IESKF point cloud matching; uses a sliding window mechanism that follows robot movement
5. The only difference between FAST-LIO2's body_cloud and world_cloud is their respective coordinate frames
6. The current SLAM incremental map is not built from FAST-LIO2's world_cloud, but from the keyframe list called m_key_poses[] in the PGO node. FAST-LIO2's world_cloud only serves RViz visualization

## 2025.11.30
1. During long-distance one-way navigation, PGO cannot trigger loop closure, so drift cannot be corrected
2. When loop closure straightens the map, it does not consider the actual physical scene. At this point, the constructed map may be pulled slightly off, deviating from the physical map -- the entire trajectory may shift or rotate as a whole
3. Loop closure makes the map "close," but the way it closes does not necessarily perfectly match the real physical scene. Error is distributed across the map, which may have slight overall deformation
4. Completed the full algorithm logic analysis for the FAST-LIO2 and PGO node algorithms
5. Completed partial algorithm logic chain construction for the GPS portion of the three-way fusion algorithm

## 2025.12.01
1. PGO algorithm understanding correction: all keyframes are always stored in a vector list m_key_poses[]; this list stores all keyframes' pose information, with new keyframes pushed as they are received
2. The PGO KdTree only stores position information (not even orientation). This data structure's purpose is solely to search for nearby historical keyframes
3. GPS Factor constrains: keyframe node (x, y, z) position. Currently, PGO triggers GTSAM optimization only when loop closure is detected