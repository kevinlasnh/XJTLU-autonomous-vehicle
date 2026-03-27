# FASTLIO2 Algorithm In-Depth

## Current Location in the Project

- Package name: `fastlio2`
- Current primary outputs:
  - `/fastlio2/lio_odom`
  - `/fastlio2/body_cloud`
- Current primary entry point:

```bash
ros2 launch fastlio2 lio_no_rviz.py params_file:=~/fyp_autonomous_vehicle/src/bringup/config/master_params.yaml
```

- Current parameter source is primarily `src/bringup/config/master_params.yaml`; `lio_no_rviz.py` retains legacy `fastlio2/config/lio.yaml` fallback capability.
- The downstream `pgo` node directly consumes `/fastlio2/lio_odom` and `/fastlio2/body_cloud`.
- This document mainly explains the algorithm principles; for the full vehicle pipeline, also refer to `docs/architecture.md` and `docs/knowledge/pgo.md`.

## 1. Odom (Odometry) Data Interpretation

The odom output from FASTLIO2 (`nav_msgs/Odometry`) contains two core data components:

- **`pose.pose.position`**: `(x, y, z)` -- vehicle position in the world coordinate frame
- **`pose.pose.orientation`**: `(x, y, z, w)` -- vehicle attitude in the world coordinate frame (quaternion representation)

These data are not raw measurements from any single sensor. Instead, they are optimal estimates obtained by fusing IMU forward integration with LiDAR point cloud matching through **IESKF (Iterated Error-State Kalman Filter)**. Specifically, the IMU provides high-frequency (200Hz) acceleration and angular velocity data for short-term prediction, while the LiDAR provides per-frame (10Hz) point cloud data to correct accumulated errors.

---

## 2. Position Data Computation

### 2.1 Initial State

At system startup, the initial state is:

```
Position: t_wi = [0, 0, 0]^T
Velocity: v = [0, 0, 0]^T
Rotation: R_wi = I (identity matrix)
```

### 2.2 IMU Data Arrival

When the first IMU data frame arrives, it contains:

- **acc**: accelerometer measurement (in body frame)
- **gyro**: gyroscope measurement (in body frame)
- **dt**: sampling interval, approximately **5ms** (200Hz)

### 2.3 Computing Acceleration in the World Frame

The IMU-measured acceleration `acc` is in the body frame and needs to be transformed to the world frame:

```
a_world = R_wi × (acc - ba) + g
```

Where:
- **`R_wi`**: rotation matrix at the current time (body -> world rotation)
- **`acc`**: raw accelerometer measurement
- **`ba`**: accelerometer bias, which drifts slowly over time and is estimated online by the filter
- **`g`**: gravity acceleration vector `[0, 0, -9.81]^T`

### 2.4 Velocity and Position Update

After obtaining the acceleration in the world frame, velocity and position are updated through numerical integration:

```
v_new = v + a_world × dt
t_wi_new = t_wi + v × dt + 0.5 × a_world × dt²
```

Each time an IMU data frame arrives (every 5ms), the above integration is performed once, continuously accumulating to produce the current position estimate.

---

## 3. Computing the Rotation Matrix R_wi

Updating the rotation matrix `R_wi` is one of the core operations in FASTLIO2, broken down into the following 7 steps:

### Step 1: Remove Gyroscope Bias

```
ω_true = gyro - bg
```

- **`gyro`**: raw gyroscope measurement (rad/s)
- **`bg`**: gyroscope bias, estimated online by IESKF
- **`ω_true`**: true angular velocity

### Step 2: Compute Angular Increment

```
Δθ = ω_true × dt
```

- **`dt`**: IMU sampling interval (approximately 5ms)
- **`Δθ`**: angular change during this time interval (3D vector, in radians)

### Step 3: Exponential Map (Rotation Vector -> Rotation Matrix)

```
ΔR = Sophus::SO3d::exp(Δθ).matrix()
```

The Sophus library's `SO3::exp()` function maps the angular increment vector to a rotation matrix. This is the **exponential map of the Lie group SO(3)**:
- Input: 3D rotation vector `Δθ`
- Output: 3x3 rotation matrix `ΔR`
- The internal implementation is equivalent to the Rodrigues formula

### Step 4: Update the Rotation Matrix

```
R_wi = R_wi × ΔR
```

The incremental rotation is right-multiplied onto the current rotation matrix, achieving cumulative rotation update.

**Error analysis**: Each integration step introduces small errors (gyroscope noise, discretization error), which accumulate over time. If relying solely on IMU integration, the rotation estimate would diverge quickly. Therefore, LiDAR data is needed for correction (Steps 5-6).

### Step 5: LiDAR Data Residual Computation

When a LiDAR point cloud frame arrives, the point cloud is matched against the existing map to compute residuals, which are used to correct the accumulated IMU integration errors.

**Point cloud coordinate transformation**:

Points captured by the LiDAR are in the LiDAR coordinate frame and need to be transformed to the world frame:

```
p_world = R_wi × p_lidar + t_wi
```

- **`p_lidar`**: point coordinates in the LiDAR frame
- **`R_wi`**: currently estimated rotation matrix
- **`t_wi`**: currently estimated position
- **`p_world`**: transformed world coordinates

**ikd-Tree nearest neighbor search**:

For each transformed point, the 5 nearest neighbors are searched in the ikd-Tree (incremental KD-tree) for local plane fitting.

**Plane fitting**:

Least-squares plane fitting is performed on the 5 nearest neighbors, yielding the plane equation:

```
n^T × p + d = 0
```

Where `n` is the plane normal vector and `d` is the distance parameter.

**Residual computation**:

The transformed point is substituted into the plane equation to obtain the point-to-plane distance as the residual:

```
residual = n^T × p_world + d
```

If the current `R_wi` and `t_wi` are very accurate, the residual should be close to 0. Larger residuals indicate less accurate pose estimates.

### Step 6: IESKF Pose Correction

After collecting residuals from all valid points, the optimal correction is solved through **Iterated Error-State Kalman Filter (IESKF)**.

**Jacobian matrix H**:

For each residual, partial derivatives with respect to state variables (position, rotation, velocity, biases, etc.) are computed to form the observation Jacobian matrix `H`.

**Normal equation**:

```
(H^T × H) × Δx = H^T × residuals
```

**Pseudo-inverse solution**:

```
Δx = (H^T × H)^(-1) × H^T × residuals
```

Where `Δx` contains corrections for rotation, position, velocity, biases, and other state variables.

**Rotation correction**:

```
R_wi = R_wi × Exp(Δθ_correction)
```

- **`Δθ_correction`**: rotation correction vector extracted from `Δx`
- **`Exp()`**: SO(3) exponential map

### Step 7: Final Rotation Matrix Update

After multiple iterations (typically 3-5), convergence is reached. The final `R_wi` is the optimal rotation estimate at the current time, and `t_wi` has also been corrected. These results are packaged into the odom message for publication.

---

## 4. Quaternion Data Interpretation

### 4.1 Meaning of Quaternions

The `orientation` in odom represents rotation as a quaternion `(x, y, z, w)`, where:

- **`w`**: scalar part, equal to `cos(θ/2)`, where `θ` is the rotation angle
- **`(x, y, z)`**: vector part, equal to `sin(θ/2) × (nx, ny, nz)`, where `(nx, ny, nz)` is the unit vector of the rotation axis

Quaternions satisfy the constraint: `x² + y² + z² + w² = 1`

### 4.2 Rodrigues Rotation Formula

Given a rotation axis `n` (unit vector) and rotation angle `θ`, the formula for rotating a vector `v`:

```
v_rotated = v × cos(θ) + (n × v) × sin(θ) + n × (n · v) × (1 - cos(θ))
```

This is the fundamental formula for understanding rotations; both quaternions and rotation matrices can be derived from it.

### 4.3 Quaternion -> Rotation Matrix

```
R = | 1-2(y²+z²)   2(xy-wz)     2(xz+wy)   |
    | 2(xy+wz)     1-2(x²+z²)   2(yz-wx)   |
    | 2(xz-wy)     2(yz+wx)     1-2(x²+y²) |
```

### 4.4 Rotation Matrix -> Quaternion

Reverse conversion formula:

```
w = 0.5 × √(1 + R[0][0] + R[1][1] + R[2][2])
x = (R[2][1] - R[1][2]) / (4w)
y = (R[0][2] - R[2][0]) / (4w)
z = (R[1][0] - R[0][1]) / (4w)
```

Note: When `w` is close to 0, alternative formula branches must be used to avoid numerical instability.

### 4.5 Euler Angle Representation (ZYX Order)

Quaternions can also be converted to Euler angles. FASTLIO2 uses ZYX order (i.e., first rotate around Z-axis for yaw, then around Y-axis for pitch, finally around X-axis for roll):

- **Yaw**: rotation around the Z-axis, representing vehicle heading
- **Pitch**: rotation around the Y-axis, representing forward/backward tilt
- **Roll**: rotation around the X-axis, representing lateral tilt

**Gimbal Lock**:

When Pitch approaches +/-90 degrees, the rotation axes of Yaw and Roll coincide, causing one degree of freedom to be lost. This is the gimbal lock problem. This is why FASTLIO2 internally uses rotation matrices or quaternions rather than Euler angles to represent rotations -- quaternions and rotation matrices do not suffer from gimbal lock.

---

## 5. Detailed FASTLIO2 Algorithm Pipeline

### Stage 0: System Initialization

After startup, the system does not begin localization immediately. Instead, it first collects **20 IMU data frames** for initialization:

1. **Collect stationary IMU data**: Assuming the vehicle is stationary, collect approximately 20 frames of acceleration and angular velocity data
2. **Gravity estimation**: Average the acceleration readings to estimate the gravity direction `g_est`
3. **Initial bias estimation**: The mean angular velocity serves as the initial gyroscope bias `bg_init`
4. **Initial covariance setup**: Set the initial uncertainty for state variables
5. **State initialization**: `R_wi = I`, `t_wi = 0`, `v = 0`

After initialization is complete, the system enters normal operation.

### Stage 1: Data Reception and Synchronization (SyncPackage)

```
SyncPackage() → Align IMU data and LiDAR point clouds by timestamp
```

1. Receive LiDAR point cloud (10Hz), record its start and end timestamps
2. Collect all IMU data within that time window (200Hz, approximately 20 frames)
3. Package the paired {IMU sequence + LiDAR point cloud} as one processing unit
4. Ensure the IMU data time coverage spans the entire LiDAR scan period

### Stage 2: IMU Forward Integration + Pose Sequence Generation

For each IMU data frame collected in Stage 1, forward integration is performed frame by frame:

1. **Bias removal**: `ω_true = gyro - bg`, `a_true = acc - ba`
2. **Rotation update**: `R_wi = R_wi × Exp(ω_true × dt)`
3. **Acceleration transformation**: `a_world = R_wi × a_true + g`
4. **Velocity update**: `v = v + a_world × dt`
5. **Position update**: `t_wi = t_wi + v × dt + 0.5 × a_world × dt²`
6. **Save intermediate poses**: Each IMU frame's corresponding `{R_wi, t_wi}` is saved as a pose sequence

The pose sequence generated in this step has two purposes:
- The last pose serves as the IESKF prediction
- Intermediate poses are used for point cloud de-distortion in the next step

### Stage 3: Point Cloud De-distortion

**Why is de-distortion needed?**

A LiDAR scan takes approximately 100ms to complete one frame, during which the vehicle is continuously moving. Therefore, different points within the same frame are captured at different vehicle poses. Without correction, the point cloud would exhibit motion blur distortion.

**De-distortion steps**:

1. **Obtain point timestamps**: Each point carries a time offset `t_offset` relative to the frame start
2. **Look up corresponding pose**: Based on `t_offset`, interpolate within the pose sequence from Stage 2 to get the vehicle pose `{R_i, t_i}` at the time the point was captured
3. **Transform to a unified coordinate frame**: Transform each point from its capture-time coordinate frame to the frame-end coordinate frame
4. **Formula**: `p_corrected = R_end^(-1) × (R_i × p_lidar_i + t_i - t_end)`
5. **Output**: All points are unified to the same time instant's coordinate frame, eliminating motion distortion

### Stage 4: IESKF Iterative Optimization (Core)

This is the most critical step in FASTLIO2, correcting accumulated IMU integration errors through iterative optimization:

#### Sub-step 1: Transform Point Cloud to the World Frame

```
p_world = R_wi × p_lidar + t_wi
```

Using the current best pose estimate (the first iteration uses the IMU integration prediction), transform the de-distorted point cloud to the world frame.

#### Sub-step 2: KNN Nearest Neighbor Search

For each transformed point, search for the **5 nearest neighbors** in the ikd-Tree. The ikd-Tree is an incremental KD-tree that supports efficient dynamic insertion and deletion operations.

#### Sub-step 3: Plane Fitting

Least-squares plane fitting on the 5 nearest neighbors:

```
n^T × p + d = 0
```

If the fitting quality is insufficient (e.g., neighbors are too scattered), the point is marked as invalid and excluded from subsequent optimization.

#### Sub-step 4: Compute Jacobian Matrix

For the residual `r = n^T × (R_wi × p_lidar + t_wi) + d`, compute partial derivatives with respect to state variables:

- Partial derivative with respect to position `t_wi`: `∂r/∂t = n^T`
- Partial derivative with respect to rotation `R_wi`: `∂r/∂θ = -n^T × R_wi × [p_lidar]×` (where `[p_lidar]×` is the skew-symmetric matrix)

These form the observation Jacobian matrix `H`.

#### Sub-step 5: Solve for the Correction

```
K = P × H^T × (H × P × H^T + R_noise)^(-1)
Δx = K × residuals
```

Or equivalently via the normal equation pseudo-inverse:

```
Δx = (H^T × R_noise^(-1) × H + P^(-1))^(-1) × H^T × R_noise^(-1) × residuals
```

#### Sub-step 6: State Update

```
R_wi = R_wi × Exp(Δθ)
t_wi = t_wi + Δt
v = v + Δv
bg = bg + Δbg
ba = ba + Δba
```

#### Sub-step 7: Convergence Check

Check whether the norm of the correction `Δx` is below the threshold:
- If `||Δx|| < threshold`, converged -- exit the iteration
- Otherwise, return to Sub-step 1 and re-perform point cloud transformation and residual computation with the updated pose
- Typically **3-5 iterations** are sufficient for convergence

**Key insight: Why only optimize the final pose?**

FASTLIO2 does not go back to optimize intermediate IMU integration poses; it only optimizes the pose at the LiDAR frame end time. The reasons are:
- The relative rotation accuracy of IMU integration is very high (gyroscope drift is minimal over short time spans)
- The main errors come from long-term accumulation, which can be effectively eliminated by correcting the final pose
- Per-frame correction is far more efficient than global optimization
- The corrected bias estimates `ba` and `bg` propagate to the next frame's IMU integration, indirectly improving subsequent integration accuracy

### Stage 5: Map Update

After optimization converges, the current frame's point cloud is added to the global map:

1. **ikd-Tree pruning**: Delete points too far from the current position (maintaining local map size)
2. **Incremental addition**: Incrementally insert the current frame's de-distorted points (transformed to the world frame) into the ikd-Tree
3. The ikd-Tree automatically rebalances to maintain query efficiency

### Stage 6: Result Publication

1. **TF publication**: Publish the `odom -> base_link` coordinate transform
2. **Odom publication**: Publish the `nav_msgs/Odometry` message containing position and attitude
3. **Point cloud publication**: Publish the current frame point cloud (in the world frame) and the global map point cloud
4. **Path publication**: Publish the historical trajectory (`nav_msgs/Path`)

---

## 6. Algorithm Core Summary

```
FASTLIO2 = High-frequency IMU integration prediction + Per-frame LiDAR correction + Iterative optimization + Incremental mapping
```

- **High-frequency IMU integration prediction**: 200Hz provides continuous pose estimates, filling the gaps between LiDAR frames
- **Per-frame LiDAR correction**: 10Hz corrects accumulated IMU integration errors through point cloud matching
- **Iterative optimization (IESKF)**: Multiple iterations drive the pose estimate to converge to the optimal value
- **Incremental mapping (ikd-Tree)**: Real-time maintenance of a local map with efficient nearest-neighbor queries
