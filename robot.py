#!/usr/bin/env python3

import wpilib
import wpilib.event
from wpimath.geometry import Rotation3d, Translation3d
import magicbot
from magicbot import tunable

from components.chassis import ChassisComponent
from components.injector import InjectorComponent
from components.vision import VisualLocalizer

from components.shooter import ShooterComponent
from components.intake import IntakeComponent
from components.climber import ClimberComponent
from components.led import LightStrip

from controllers.shooter import Shooter
from controllers.climber import Climber

from utilities.game import is_red

import math

from utilities.scalers import rescale_js


class MyRobot(magicbot.MagicRobot):
    # Controllers
    shooter: Shooter
    climber: Climber

    # Components
    chassis: ChassisComponent
    injector_component: InjectorComponent
    shooter_component: ShooterComponent
    intake: IntakeComponent
    climber_component: ClimberComponent
    lights: LightStrip

    max_speed = magicbot.tunable(4)  # m/s
    inclination_angle = tunable(0.0)
    vision_port: VisualLocalizer
    vision_starboard: VisualLocalizer

    def createObjects(self) -> None:
        self.data_log = wpilib.DataLogManager.getLog()

        self.gamepad = wpilib.XboxController(0)

        self.rumble_timer = wpilib.Timer()
        self.rumble_timer.start()
        self.rumble_duration = 0.0

        self.field = wpilib.Field2d()
        wpilib.SmartDashboard.putData(self.field)

        self.lights_strip_length = 144  # TODO Change to correct length

        self.vision_port_name = "ardu_cam_port"
        self.vision_port_pos = Translation3d(0.287, 0.055, 0.27)
        self.vision_port_rot = Rotation3d(
            0, -math.radians(20), math.radians(180) - math.radians(90 - 71.252763)
        )

        self.vision_starboard_name = "ardu_cam_starboard"
        self.vision_starboard_pos = Translation3d(0.287, -0.058, 0.27)
        self.vision_starboard_rot = Rotation3d(
            0, -math.radians(20), math.radians(180) + math.radians(90 - 71.252763)
        )

    def rumble_for(self, intensity: float, duration: float):
        self.rumble_duration = duration
        self.rumble_timer.reset()
        self.gamepad.setRumble(wpilib.XboxController.RumbleType.kBothRumble, intensity)

    def short_rumble(self):
        self.rumble_for(0.4, 0.1)

    def long_rumble(self):
        self.rumble_for(0.8, 0.3)

    def teleopInit(self) -> None:
        pass

    def teleopPeriodic(self) -> None:
        # Driving
        spin_rate = 4
        drive_x = -rescale_js(self.gamepad.getLeftY(), 0.1) * self.max_speed
        drive_y = -rescale_js(self.gamepad.getLeftX(), 0.1) * self.max_speed
        drive_z = -rescale_js(self.gamepad.getRightX(), 0.1, exponential=2) * spin_rate
        local_driving = self.gamepad.getYButton()

        if local_driving:
            self.chassis.drive_local(drive_x, drive_y, drive_z)
        else:
            if is_red():
                drive_x = -drive_x
                drive_y = -drive_y
            self.chassis.drive_field(drive_x, drive_y, drive_z)

        # give rotational access to the driver
        if drive_z != 0:
            self.chassis.stop_snapping()

        dpad = self.gamepad.getPOV()
        if dpad != -1:
            if is_red():
                self.chassis.snap_to_heading(-math.radians(dpad) + math.pi)
            else:
                self.chassis.snap_to_heading(-math.radians(dpad))

        # Set current robot direction to forward
        if self.gamepad.getXButton():
            self.chassis.reset_yaw()

        # stop rumble after time
        if self.rumble_timer.hasElapsed(self.rumble_duration):
            self.gamepad.setRumble(wpilib.XboxController.RumbleType.kBothRumble, 0)

        # Climbing arm controls

        if self.gamepad.getLeftBumper():
            self.climber.deploy()

        if self.gamepad.getRightBumper():
            self.climber.climb()

    def testInit(self) -> None:
        pass

    def testPeriodic(self) -> None:
        # moving arm
        if self.gamepad.getAButton():
            self.intake.deploy()
        elif self.gamepad.getYButton():
            self.intake.retract()

        # injecting
        if self.gamepad.getBButton():
            self.injector_component.shoot()

        if self.gamepad.getXButton():
            self.intake.intake()

        if self.gamepad.getLeftBumper():
            self.climber_component.deploy()

        if self.gamepad.getRightBumper():
            self.climber_component.retract()

        # Cancel any running controllers
        if self.gamepad.getBackButtonPressed():
            self.cancel_controllers()

        self.shooter.execute()

        self.intake.execute()
        self.shooter_component.execute()
        self.climber_component.execute()

        self.chassis.update_odometry()

        self.vision_port.execute()
        self.vision_starboard.execute()

    def cancel_controllers(self):
        self.climber.stop()

    def disabledPeriodic(self) -> None:
        self.chassis.update_alliance()
        self.chassis.update_odometry()

        self.intake.try_initialise_limits()
        self.lights.execute()
        self.vision_port.execute()
        self.vision_starboard.execute()

    def autonomousInit(self) -> None:
        pass


if __name__ == "__main__":
    wpilib.run(MyRobot)
