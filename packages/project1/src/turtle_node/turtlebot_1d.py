#!/usr/bin/env python

import rospy
import helpers
import random
from geometry_msgs.msg import Twist, Pose2D, PoseWithCovarianceStamped
from turtlebot import TurtleBot
from std_msgs.msg import Float32


class TurtleBot1D(TurtleBot, object):

    def __init__(self):
        super(TurtleBot1D, self).__init__()

        rospy.on_shutdown(self.stop)

        self.robot_1_distance = None
        self.robot_3_distance = None
        self.robot_1_position = None
        self.robot_3_position = None
        self.pose11 = PoseWithCovarianceStamped()
        self.pose33 = PoseWithCovarianceStamped()
        self.pose32 = PoseWithCovarianceStamped()

        self.initialize_extra_subscribers()
        self.initialize_extra_publishers()

    def initialize_extra_publishers(self):
        self.cmd_vel_pub = rospy.Publisher('cmd_vel_mux/input/navi', Twist,
                                           queue_size=1)

        self.pose_wrt_1_from_1 = rospy.Publisher('pose11',
                                                 PoseWithCovarianceStamped,
                                                 queue_size=1)

        self.pose_wrt_3_from_3 = rospy.Publisher('pose33',
                                                 PoseWithCovarianceStamped,
                                                 queue_size=1)

        self.pose_wrt_3_from_2 = rospy.Publisher('pose33',
                                                 PoseWithCovarianceStamped,
                                                 queue_size=1)

    def initialize_extra_subscribers(self):
        self.robot_1_dist = rospy.Subscriber('/turtlebot1/scan_average', Float32,
                                            self.robot_1_dist_cb)

        self.robot_3_dist = rospy.Subscriber('/turtlebot3/scan_average', Float32,
                                            self.robot_3_dist_cb)

        self.robot_1_pos = rospy.Subscriber('/turtlebot1/position', Pose2D,
                                            self.robot_1_pos_cb)

        self.robot_3_pos = rospy.Subscriber('/turtlebot3/position', Pose2D,
                                            self.robot_3_pos_cb)

    def robot_1_dist_cb(self, distance):
        #TODO make this a circular array with a set number of measurements to average
        rospy.logdebug("Updated robot 1 distance")
        self.robot_1_distance = distance

    def robot_3_dist_cb(self, distance):
        self.robot_3_distance = distance

    def robot_1_pos_cb(self, position):
        self.robot_1_position = position

    def robot_3_pos_cb(self, position):
        self.robot_3_position = position

    def update_pose_11(self):
        if self.robot_1_distance is not None and self.robot_1_position is not None:
            self.pose11.pose.pose.position.x = self.robot_1_position.x + self.robot_1_distance.data
            # TODO add distance from edge to center of turtlebot to this calculation and kinect to center
            # TODO add variance calculation to this
            self.pose11.header.stamp = rospy.get_rostime()
            self.pose11.header.frame_id = 'turtlebot2/base_footprint_generated'
            self.pose_wrt_1_from_1.publish(self.pose11)
        else:
            if self.robot_1_distance is None:
                rospy.loginfo("Didn't update pose_11 because robot_1_distance = None")
            if self.robot_1_position is None:
                rospy.loginfo("Didn't update pose_11 because robot_1_position = None")

    def update_pose_33(self):
        if self.robot_3_distance is not None and self.robot_3_position is not None:
            self.pose33.pose.pose.position.x = self.robot_3_distance.data - self.robot_3_position.x
            # TODO add distance from edge to center of turtlebot to this calculation and kinect to center
            # TODO add variance calculation to this
            self.pose33.header.stamp = rospy.get_rostime()
            self.pose33.header.frame_id = 'turtlebot2/base_footprint_generated'
            self.pose_wrt_3_from_3.publish(self.pose33)

    def update_pose_32(self):
        if self.scan_distance is not None and self.robot_3_position is not None:
            self.pose32.pose.pose.position.x = self.robot_3_position.x - self.scan_distance
            # TODO add distance from edge to center of turtlebot to this calculation and kinect to center
            # TODO add variance calculation to this
            self.pose32.header.stamp = rospy.get_rostime()
            self.pose32.header.frame_id = 'turtlebot2/base_footprint_generated'
            self.pose_wrt_3_from_2.publish(self.pose32)

    def move(self, amount, lower_bound=1, upper_bound=5):
        goal_x = self.pose.x + amount

        within_bounds = helpers.check_bounds(goal_x, lower_bound, upper_bound)
        if within_bounds:
            move_cmd = Twist()
            if amount < 0:
                move_cmd.linear.x = -self.speed
                dist_to_goal = -amount
            else:
                move_cmd.linear.x = self.speed
                dist_to_goal = amount
            rospy.logdebug('Robot is heading to x: %s', str(goal_x))

            prev_time = helpers.get_curr_time()
            tot_dist_traveled = 0
            while dist_to_goal > 0.1:
                self.cmd_vel_pub.publish(move_cmd)
                self.rate.sleep()

                curr_time = helpers.get_curr_time()
                diff = curr_time - prev_time
                dist_traveled = self.speed * diff
                tot_dist_traveled += dist_traveled
                dist_to_goal -= dist_traveled
                prev_time = curr_time

            if amount < 0:
                self.pose.x -= tot_dist_traveled
            else:
                self.pose.x += tot_dist_traveled
            rospy.logdebug('Robot reached x: %s', str(goal_x))
        else:
            rospy.logwarn('Goal received out of bounds')

    def stop(self):
        rospy.logdebug('%s has stopped', self.namespace)
        self.cmd_vel_pub.publish(Twist())
        rospy.sleep(1)


def main():
    robot = TurtleBot1D()

    while not rospy.is_shutdown():
        robot.move(amount=random.uniform(-1, 1))
        rospy.sleep(1)
        robot.update_pose_11()
        robot.update_pose_32()
        robot.update_pose_33()
        rospy.sleep(1)

if __name__ == '__main__':
    try:
        main()
    except rospy.ROSInterruptException:
        pass
