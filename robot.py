#!/usr/bin/env python3

import wpilib
import wpilib.event
import magicbot

from components.chassis import Chassis
from components.shooter import Shooter
import math

from utilities.scalers import rescale_js


class MyRobot(magicbot.MagicRobot):
    # Controllers

    # Components
    chassis: Chassis
    shooter: Shooter

    max_speed = magicbot.tunable(Chassis.max_wheel_speed * 0.95)

    def createObjects(self) -> None:
        self.data_log = wpilib.DataLogManager.getLog()

        self.gamepad = wpilib.XboxController(0)

        self.rumble_timer = wpilib.Timer()
        self.rumble_timer.start()
        self.rumble_duration = 0.0

        self.field = wpilib.Field2d()
        wpilib.SmartDashboard.putData(self.field)

    def rumble_for(self, intensity: float, duration: float):
        self.rumble_duration = duration
        self.rumble_timer.reset()
        self.gamepad.setRumble(wpilib.XboxController.RumbleType.kBothRumble, intensity)

    def short_rumble(self):
        self.rumble_for(0.4, 0.1)

    def long_rumble(self):
        self.rumble_for(0.8, 0.3)

    def teleopInit(self) -> None:
        self.dpad_angle = 0.0

    def teleopPeriodic(self) -> None:
        # Driving
        spin_rate = 4
        drive_x = -rescale_js(self.gamepad.getLeftY(), 0.1) * self.max_speed
        drive_y = -rescale_js(self.gamepad.getLeftX(), 0.1) * self.max_speed
        drive_z = -rescale_js(self.gamepad.getRightX(), 0.1, exponential=2) * spin_rate
        local_driving = self.gamepad.getBButton()
        driver_inputs = (drive_x, drive_y, drive_z)
        if local_driving:
            self.chassis.drive_local(*driver_inputs)
        else:
            self.chassis.drive_field(*driver_inputs)

        # give rotational access to the driver
        if drive_z != 0:
            self.chassis.stop_snapping()

        # testing rig for the snap to heading method
        if self.gamepad.getPOV() != -1:
            self.dpad_angle = self.gamepad.getPOV()

        if self.gamepad.getAButtonPressed():
            self.chassis.snap_to_heading(math.radians(self.dpad_angle))

        if self.gamepad.getBButtonPressed():
            self.chassis.lock_swerve()

        if self.gamepad.getBButtonReleased():
            self.chassis.unlock_swerve()

        # stop rumble after time
        if self.rumble_timer.hasElapsed(self.rumble_duration):
            self.gamepad.setRumble(wpilib.XboxController.RumbleType.kBothRumble, 0)

        # injecting
        if self.gamepad.getBButton():
            self.shooter.shoot()

    def testInit(self) -> None:
        pass

    def testPeriodic(self) -> None:
        # Cancel any running controllers
        if self.gamepad.getBackButtonPressed():
            self.cancel_controllers()

        self.chassis.update_odometry()

    def cancel_controllers(self):
        pass

    def disabledPeriodic(self) -> None:
        self.chassis.update_odometry()

    def autonomousInit(self) -> None:
        pass


if __name__ == "__main__":
    wpilib.run(MyRobot)
