import math

from wpimath.geometry import Translation2d

from magicbot import StateMachine, state, timed_state

from components.chassis import ChassisComponent
from components.intake import IntakeComponent
from components.shooter import ShooterComponent
from utilities.game import get_goal_speaker_position


class Shooter(StateMachine):

    shooter_component: ShooterComponent
    chassis: ChassisComponent
    intake: IntakeComponent

    def translation_to_goal(self) -> Translation2d:
        return (
            get_goal_speaker_position().toTranslation2d()
            - self.chassis.get_pose().translation()
        )

    @state(first=True)
    def aiming(self):
        translation_to_goal = self.translation_to_goal()

        # Determine heading required for goal
        bearing_to_speaker = (
            math.atan2(translation_to_goal.y, translation_to_goal.x) + math.pi
        )

        # Update range
        self.shooter_component.set_range(translation_to_goal.norm())

        # Set to appropriate heading
        self.chassis.snap_to_heading(bearing_to_speaker)
        if self.chassis.at_desired_heading() and self.shooter_component.is_ready():
            self.next_state(self.firing)

    @timed_state(duration=1, must_finish=True)
    def firing(self):
        self.intake.inject()
