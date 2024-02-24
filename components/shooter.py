import math
import numpy as np
from magicbot import tunable, feedback
from rev import CANSparkMax
from ids import SparkMaxIds, TalonIds, DioChannels

from phoenix6.controls import VelocityVoltage, Follower
from phoenix6.hardware import TalonFX
from phoenix6.configs import (
    MotorOutputConfigs,
    Slot0Configs,
    FeedbackConfigs,
    config_groups,
)
from phoenix6.signals import NeutralModeValue
from wpilib import DigitalInput, DutyCycle, SmartDashboard
from wpimath.controller import PIDController

from utilities.ctre import FALCON_FREE_RPS
from utilities.functions import clamp
from utilities.game import SPEAKER_HOOD_HEIGHT


class ShooterComponent:
    FLYWHEEL_GEAR_RATIO = 24.0 / 18.0
    FLYWHEEL_TOLERANCE = 1  # rps

    FLYWHEEL_MAX_SPEED = FALCON_FREE_RPS / FLYWHEEL_GEAR_RATIO

    MAX_INCLINE_ANGLE = 0.973  # ~55 degrees
    MIN_INCLINE_ANGLE = math.radians(20)
    INCLINATOR_TOLERANCE = math.radians(1)
    INCLINATOR_OFFSET = 0.822 * math.tau - math.radians(20)
    INCLINATOR_SCALE_FACTOR = math.tau  # rps -> radians

    FLYWHEEL_DISTANCE_LOOKUP = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
    FLYWHEEL_SPEED_LOOKUP = (
        FLYWHEEL_MAX_SPEED,
        FLYWHEEL_MAX_SPEED,
        FLYWHEEL_MAX_SPEED,
        FLYWHEEL_MAX_SPEED,
        FLYWHEEL_MAX_SPEED,
        FLYWHEEL_MAX_SPEED,
    )

    desired_inclinator_angle = tunable((MAX_INCLINE_ANGLE + MIN_INCLINE_ANGLE) / 2)
    desired_flywheel_speed = tunable(0.0)

    def __init__(self) -> None:
        self.inclinator = CANSparkMax(
            SparkMaxIds.shooter_inclinator, CANSparkMax.MotorType.kBrushless
        )
        self.inclinator_encoder = DutyCycle(
            DigitalInput(DioChannels.inclinator_encoder)
        )
        self.flywheel = TalonFX(TalonIds.shooter_flywheel)
        self.flywheel1 = TalonFX(TalonIds.shooter_flywheel1)  # change the name

        flywheel_config = self.flywheel.configurator
        flywheel_motor_config = MotorOutputConfigs()
        flywheel1_motor_config = MotorOutputConfigs()
        flywheel_motor_config.neutral_mode = NeutralModeValue.COAST
        flywheel1_motor_config.inverted = (
            config_groups.InvertedValue.COUNTER_CLOCKWISE_POSITIVE
        )

        flywheel_pid = (
            Slot0Configs()
            .with_k_p(0.3514)
            .with_k_i(0)
            .with_k_d(0)
            .with_k_s(0.19469)
            .with_k_v(0.15649)
            .with_k_a(0.017639)
        )

        flywheel_gear_ratio = FeedbackConfigs().with_sensor_to_mechanism_ratio(
            self.FLYWHEEL_GEAR_RATIO
        )

        flywheel_config.apply(flywheel_motor_config)
        flywheel_config.apply(flywheel_pid)
        flywheel_config.apply(flywheel_gear_ratio)
        flywheel_config.apply(flywheel1_motor_config)

        self.inclinator_controller = PIDController(3, 0, 0)
        self.inclinator_controller.setTolerance(ShooterComponent.INCLINATOR_TOLERANCE)
        SmartDashboard.putData(self.inclinator_controller)

    def on_enable(self) -> None:
        self.inclinator_controller.reset()

    @feedback
    def is_ready(self) -> bool:
        """Is the shooter ready to fire?"""
        return True
        # return self._flywheels_at_speed() and self._at_inclination()

    @feedback
    def _at_inclination(self) -> bool:
        """Is the inclinator close to the correct angle?"""
        return (
            abs(self.desired_inclinator_angle - self._inclination_angle())
            < self.INCLINATOR_TOLERANCE
        )

    @feedback
    def _flywheels_at_speed(self) -> bool:
        """Are the flywheels close to thier target speed"""
        return (
            abs(self.desired_flywheel_speed - self.flywheel.get_velocity().value)
            < self.FLYWHEEL_TOLERANCE
        )

    @feedback
    def _inclination_angle(self) -> float:
        """Get the angle of the mechanism in radians measured positive upwards from zero parellel to the ground."""
        return (
            self.inclinator_encoder.getOutput() * self.INCLINATOR_SCALE_FACTOR
            - self.INCLINATOR_OFFSET
        )

    @feedback
    def _flywheel_velocity(self) -> float:
        return self.flywheel.get_velocity().value

    def set_range(self, range: float) -> None:
        self.desired_inclinator_angle = math.atan2(SPEAKER_HOOD_HEIGHT, range)
        self.desired_flywheel_speed = float(
            np.interp(range, self.FLYWHEEL_DISTANCE_LOOKUP, self.FLYWHEEL_SPEED_LOOKUP)
        )

    def execute(self) -> None:
        """This gets called at the end of the control loop"""
        inclinator_speed = self.inclinator_controller.calculate(
            self._inclination_angle(),
            clamp(
                self.desired_inclinator_angle,
                ShooterComponent.MIN_INCLINE_ANGLE,
                ShooterComponent.MAX_INCLINE_ANGLE,
            ),
        )
        self.inclinator.set(inclinator_speed)

        flywheel_request = VelocityVoltage(self.desired_flywheel_speed)
        self.flywheel.set_control(flywheel_request)
        self.flywheel1 = Follower(self.flywheel)
