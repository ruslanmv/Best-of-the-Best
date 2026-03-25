---
title: "PyBullet: Physics Simulation for Robotics and Reinforcement Learning"
date: 2026-01-20T09:00:00+00:00
last_modified_at: 2026-01-20T09:00:00+00:00
topic_kind: "package"
topic_id: "pybullet"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - robotics
  - physics-simulation
  - reinforcement-learning
  - bullet-physics
  - urdf
excerpt: "PyBullet is a Python binding for the Bullet physics engine, providing real-time physics simulation for robotics, reinforcement learning, and VR applications."
header:
  overlay_image: /assets/images/2026-01-20-package-pybullet/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-20-package-pybullet/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

PyBullet is a Python binding for the [Bullet Physics SDK](https://pybullet.org/), a widely used open-source physics engine. It is designed for robotics simulation, reinforcement learning research, and VR applications. PyBullet lets you load articulated robots described in URDF, SDF, or MJCF formats, simulate forward dynamics, compute inverse kinematics, and render camera images -- all from Python.

In this guide you will learn how to set up PyBullet, load robot models, run physics simulations, and read joint and link states.

## Overview

Key features:

* Real-time rigid body dynamics with contact and friction
* Loading of URDF, SDF, and MJCF robot descriptions
* Forward and inverse kinematics
* Inverse dynamics and Jacobian computation
* Synthetic camera rendering (RGB, depth, segmentation)
* Built-in GUI and headless (DIRECT) rendering modes
* Integration with OpenAI Gym for reinforcement learning environments

Use cases:

* Sim-to-real robotics research
* Reinforcement learning environment prototyping
* Grasp planning and manipulation
* Locomotion control for legged robots

Current version: **pybullet 3.2.6**

## Getting Started

Installation:

```
pip install pybullet
```

Quick example -- load a plane and the KUKA robot arm, then step the simulation:

```python
import pybullet as p
import pybullet_data

# Connect to the physics server (use p.GUI for a graphical window)
physics_client = p.connect(p.DIRECT)

# Add the built-in data path so we can load bundled URDFs
p.setAdditionalSearchPath(pybullet_data.getDataPath())

# Set gravity
p.setGravity(0, 0, -9.81)

# Load a ground plane and the KUKA iiwa robot
plane_id = p.loadURDF("plane.urdf")
robot_id = p.loadURDF("kuka_iiwa/model.urdf", basePosition=[0, 0, 0])

# Step the simulation for 240 steps (one second at 240 Hz)
for _ in range(240):
    p.stepSimulation()

# Disconnect when done
p.disconnect()
```

## Core Concepts

### Physics Connection Modes

PyBullet requires a connection to a physics server before any simulation work. The two most common modes are:

* `p.GUI` -- opens a graphical window for visualization.
* `p.DIRECT` -- runs headless, useful for training and CI pipelines.

### Loading Models

Robot and object models are loaded with `p.loadURDF()`, `p.loadSDF()`, or `p.loadMJCF()`. Each returns a unique body ID used to query and control the body.

### Stepping and Control

* `p.stepSimulation()` -- advances physics by one timestep.
* `p.setJointMotorControl2()` -- applies torque, velocity, or position control to a joint.
* `p.getJointState()` -- returns the current position, velocity, applied torque, and reaction forces of a joint.
* `p.getLinkState()` -- returns the position and orientation of a link.

## Practical Examples

### Example 1: Applying Joint Position Control

```python
import pybullet as p
import pybullet_data

physics_client = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

plane_id = p.loadURDF("plane.urdf")
robot_id = p.loadURDF("kuka_iiwa/model.urdf", basePosition=[0, 0, 0])

num_joints = p.getNumJoints(robot_id)
print(f"Robot has {num_joints} joints")

# Set a target position for joint 0
target_position = 1.0  # radians
p.setJointMotorControl2(
    bodyUniqueId=robot_id,
    jointIndex=0,
    controlMode=p.POSITION_CONTROL,
    targetPosition=target_position,
    force=500,
)

# Run the simulation until the joint reaches the target
for step in range(1000):
    p.stepSimulation()

joint_state = p.getJointState(robot_id, 0)
print(f"Joint 0 position: {joint_state[0]:.4f} rad")

p.disconnect()
```

### Example 2: Rendering a Synthetic Camera Image

```python
import pybullet as p
import pybullet_data

physics_client = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

plane_id = p.loadURDF("plane.urdf")
robot_id = p.loadURDF("kuka_iiwa/model.urdf", basePosition=[0, 0, 0])

# Compute view and projection matrices
view_matrix = p.computeViewMatrix(
    cameraEyePosition=[1.5, 0, 1.0],
    cameraTargetPosition=[0, 0, 0.5],
    cameraUpVector=[0, 0, 1],
)
projection_matrix = p.computeProjectionMatrixFOV(
    fov=60, aspect=1.0, nearVal=0.1, farVal=100.0
)

# Capture an image
width, height, rgb_pixels, depth_pixels, seg_mask = p.getCameraImage(
    width=320, height=240,
    viewMatrix=view_matrix,
    projectionMatrix=projection_matrix,
)
print(f"Captured image of size {width}x{height}")

p.disconnect()
```

### Example 3: Collision Detection Between Objects

```python
import pybullet as p
import pybullet_data

physics_client = p.connect(p.DIRECT)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)

plane_id = p.loadURDF("plane.urdf")

# Create two boxes
col_shape = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1])
vis_shape = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.1, 0.1, 0.1], rgbaColor=[1, 0, 0, 1])

box_a = p.createMultiBody(baseMass=1.0, baseCollisionShapeIndex=col_shape,
                          baseVisualShapeIndex=vis_shape, basePosition=[0, 0, 0.5])
box_b = p.createMultiBody(baseMass=1.0, baseCollisionShapeIndex=col_shape,
                          baseVisualShapeIndex=vis_shape, basePosition=[0, 0, 0.8])

# Step and check contacts
for _ in range(240):
    p.stepSimulation()

contacts = p.getContactPoints(box_a, box_b)
print(f"Number of contact points between boxes: {len(contacts)}")

p.disconnect()
```

## Best Practices

* Use `p.DIRECT` mode for training and headless environments; reserve `p.GUI` for debugging and visualization.
* Always call `p.setAdditionalSearchPath(pybullet_data.getDataPath())` so that bundled URDF files (plane, robots) are found automatically.
* Set an appropriate simulation timestep with `p.setTimeStep()` -- the default is 1/240 seconds.
* When running reinforcement learning, reset the simulation with `p.resetSimulation()` at the start of each episode rather than disconnecting and reconnecting.
* Use `p.setRealTimeSimulation(0)` and call `p.stepSimulation()` manually for deterministic, reproducible training.

## Conclusion

PyBullet provides a full-featured physics simulation environment accessible entirely from Python. It is one of the most popular tools for robotics simulation and reinforcement learning research thanks to its bundled robot models, synthetic rendering, and straightforward API.

Resources:

* [PyBullet Quickstart Guide](https://docs.google.com/document/d/10sXEhzFRSnvFcl3XxNGhnD4N2SedqwdAvK3dsihxVUA/)
* [PyBullet on PyPI](https://pypi.org/project/pybullet/)
* [Bullet Physics GitHub](https://github.com/bulletphysics/bullet3)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
