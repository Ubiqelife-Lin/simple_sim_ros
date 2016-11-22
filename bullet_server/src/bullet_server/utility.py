#!/usr/bin/env python
# Copyright Lucas Walter 2016

import math
import rospy
import tf

from bullet_server.msg import Anchor, Body, Constraint, Face, Link
from bullet_server.msg import Material, Node, SoftBody, SoftConfig, Tetra
from bullet_server.srv import *

def make_rigid_box(name, mass, xs, ys, zs, wd, ln, ht,
                   roll=0, pitch=0, yaw=0):
    body = Body()
    body.name = name
    body.type = Body.BOX
    body.mass = mass
    body.pose.position.x = xs
    body.pose.position.y = ys
    body.pose.position.z = zs
    rot90 = tf.transformations.quaternion_from_euler(roll, pitch, yaw)
    body.pose.orientation.x = rot90[0]
    body.pose.orientation.y = rot90[1]
    body.pose.orientation.z = rot90[2]
    body.pose.orientation.w = rot90[3]

    body.scale.x = wd
    body.scale.y = ln
    body.scale.z = ht
    return body

def make_rigid_cylinder(name, mass, xs, ys, zs, radius, thickness,
                        roll=math.pi/2.0, pitch=0, yaw=0):
    # make the top cylinder plate
    body = Body()
    body.name = name
    body.mass = mass
    rot90 = tf.transformations.quaternion_from_euler(roll, pitch, yaw)
    body.pose.orientation.x = rot90[0]
    body.pose.orientation.y = rot90[1]
    body.pose.orientation.z = rot90[2]
    body.pose.orientation.w = rot90[3]
    body.pose.position.x = xs
    body.pose.position.y = ys
    body.pose.position.z = zs
    body.type = Body.CYLINDER
    body.scale.x = radius
    body.scale.y = thickness
    body.scale.z = radius
    return body

# load in default values since otherwise the default is zero
def make_soft_config():
    config = SoftConfig()
    config.kVCF = 1.0
    config.kDF = 0.2
    config.kCHR = 1.0
    config.kKHR = 0.1
    config.kSHR = 1.0
    config.kAHR = 0.7
    config.kSRHR_CL = 0.1
    config.kSKHR_CL = 1.0
    config.kSSHR_CL = 0.5
    config.kSR_SPLT_CL = 0.5
    config.kSK_SPLT_CL = 0.5
    config.kSS_SPLT_CL = 0.5
    config.maxvolume = 1.0
    config.timescale = 1.0
    return config

def make_soft_cube(name, node_mass, xs, ys, zs, ln,
                   nx=4, ny=4, nz=4, flip=1.0):
    body = SoftBody()
    body.config = make_soft_config()
    body.name = name

    # dynamic friction
    body.config.kDF = 0.9

    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                n1 = Node()
                n1.mass = node_mass
                n1.position.x = xs + (i - nx/2 + 0.5) * ln * flip
                n1.position.y = ys + (j - ny/2 + 0.5) * ln * flip
                n1.position.z = zs + (k - nz/2 + 0.5) * ln * flip
                body.node.append(n1)

    for ind1 in range(len(body.node)):
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    if i == 0 and j == 0 and k == 0:
                        continue
                    ind2 = ind1 + i * ny * nz + j * nz + k
                    if ind2 < len(body.node):
                        l1 = Link()
                        l1.node_indices[0] = ind1
                        l1.node_indices[1] = ind2
                        body.link.append(l1)

    mat = Material()
    mat.kLST = 0.25
    mat.kVST = 0.1
    mat.kAST = 0.1
    body.material.append(mat)

    return body

def make_tetra(node_indices, make_links=True):
    tetra = Tetra()
    tetra.node_indices = node_indices
    links = []
    if make_links:
        for i in range(len(node_indices)):
            for j in range(i+1, len(node_indices)):
                link = Link()
                link.node_indices[0] = node_indices[i]
                link.node_indices[1] = node_indices[j]
                links.append(link)

    return tetra, links

def make_soft_tetra_cube(name, node_mass, xs, ys, zs, ln,
                   nx=2, ny=2, nz=2, flip=1.0):
    body = SoftBody()
    body.config = make_soft_config()
    body.name = name

    # dynamic friction
    body.config.kDF = 0.9

    for k in range(nz):
        for j in range(ny):
            for i in range(nx):
                n1 = Node()
                n1.mass = node_mass
                n1.position.x = xs + (i - nx/2 + 0.5) * ln * flip
                n1.position.y = ys + (j - ny/2 + 0.5) * ln * flip
                n1.position.z = zs + (k - nz/2 + 0.5) * ln * flip
                body.node.append(n1)

    #    6  7
    #  4   5
    #
    #    2  3
    #  0   1
    tetra, links = make_tetra([0, 1, 2, 4])
    body.tetra.append(tetra)
    for link in links:
        body.link.append(link)
    tetra, links = make_tetra([1, 3, 2, 7])
    body.tetra.append(tetra)
    for link in links:
        body.link.append(link)
    tetra, links = make_tetra([1, 2, 4, 7])
    body.tetra.append(tetra)
    for link in links:
        body.link.append(link)
    tetra, links = make_tetra([4, 7, 6, 2])
    body.tetra.append(tetra)
    for link in links:
        body.link.append(link)
    tetra, links = make_tetra([4, 5, 7, 1])
    body.tetra.append(tetra)
    for link in links:
        body.link.append(link)

    mat = Material()
    mat.kLST = 0.25
    mat.kAST = 0.1
    mat.kVST = 0.9
    body.material.append(mat)

    return body

def make_wheel_assembly(prefix, xs, ys, zs, flip=1.0):
    motor_mass = 0.2
    motor_thickness = 0.1
    motor_radius = 0.2
    motor_y = 0.8
    motor = make_rigid_cylinder(prefix + "_motor", motor_mass,
                                xs, ys - motor_y * flip, zs,
                                motor_radius, motor_thickness,
                                0, 0, 0)

    hinge = Constraint()
    hinge.name = prefix + "_motor_hinge"
    hinge.body_a = "chassis"
    hinge.body_b = prefix + "_motor"
    hinge.type = Constraint.HINGE
    hinge.pivot_in_a.x = xs
    hinge.pivot_in_a.y = -motor_y * flip
    hinge.pivot_in_a.z = 0
    hinge.pivot_in_b.x = 0
    hinge.pivot_in_b.y = 0
    hinge.pivot_in_b.z = 0
    hinge.axis_in_a.x = 0
    hinge.axis_in_a.y = 1.0
    hinge.axis_in_a.z = 0
    hinge.axis_in_b.x = 0
    hinge.axis_in_b.y = 1.0
    hinge.axis_in_b.z = 0
    # These have to be < -pi and > pi to be unlimited
    hinge.lower_ang_lim = -3.2  # -math.pi
    hinge.upper_ang_lim = 3.2  # math.pi
    hinge.max_motor_impulse = 25000.0

    wheel_offset = 1.5
    nx = 4
    ny = 4
    nz = 4
    soft_length = 0.4
    node_mass = 0.1
    wheel = make_soft_cube(prefix + "wheel", node_mass,
                           xs, ys - wheel_offset * flip, zs, soft_length,
                           nx, ny, nz,
                           flip)

    # attach the rigid motor wheel to the soft wheel
    for i in range(2):
        for j in range(3):
            for k in range(2):
                xi = i + 1  # int(nx/2) - 1
                yi = j + 1  # int(ny/2) - 1
                zi = k + 1  # int(nz/2) - 1
                ind = xi * ny * nz + yi * nz + zi
                if ind < len(wheel.node):
                    anchor = Anchor()
                    anchor.disable_collision_between_linked_bodies = False
                    # the weaker the influence, the longer the spring between
                    # the local_pivot and the node
                    # TODO(lucasw) probably should have more anchors,
                    # but weaken the influence with distance from the wheel
                    # axle
                    anchor.influence = 1.0

                    anchor.node_index = ind
                    anchor.rigid_body_name = prefix + "_motor"
                    anchor.local_pivot.x = wheel.node[ind].position.x - xs
                    anchor.local_pivot.y = wheel.node[ind].position.y - ys + 0.8 * flip
                    anchor.local_pivot.z = wheel.node[ind].position.z - zs
                    wheel.anchor.append(anchor)

    return (motor, hinge, wheel)

