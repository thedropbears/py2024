from magicbot import StateMachine, state, feedback, will_reset_to
from wpimath.geometry import Translation2d

from components.chassis import ChassisComponent
from components.intake import IntakeComponent
from components.shooter import ShooterComponent
from controllers.shooter import Shooter
from utilities.game import get_goal_speaker_position


class NoteManager(StateMachine):

    shooter: Shooter

    shooter_component: ShooterComponent
    chassis: ChassisComponent
    intake: IntakeComponent

    shot_desired = will_reset_to(False)

    def __init__(self):
        self.intake_desired = False

    def try_intake(self):
        self.intake_desired = True

    def cancel_intake(self):
        self.intake_desired = False

    def try_shoot(self):
        self.shot_desired = True

    @feedback
    def has_note(self):
        return self.intake.has_note()

    def translation_to_goal(self) -> Translation2d:
        return (
            get_goal_speaker_position().toTranslation2d()
            - self.chassis.get_pose().translation()
        )

    def has_just_fired(self) -> bool:
        """Intended to be polled by autonomous to tell when shooting is finished"""
        return (
            self.last_state == "holding_note"
            and self.current_state == "not_holding_note"
        )

    def execute(self):
        self.last_state = self.current_state
        super().execute()

    def on_enable(self) -> None:
        super().on_enable()
        if self.has_note():
            self.engage()
        else:
            self.engage(self.not_holding_note)

    @state(must_finish=True, first=True)
    def holding_note(self):
        self.shooter_component.set_range(self.translation_to_goal().norm())

        self.intake_desired = False

        if self.shot_desired:
            self.shooter.engage()

        if not self.has_note():
            self.next_state(self.not_holding_note)

    @state(must_finish=True)
    def not_holding_note(self):
        self.shooter_component.set_range(self.translation_to_goal().norm())

        if self.intake_desired:
            self.intake.deploy()
            self.intake.intake()
        else:
            self.intake.retract()

        if self.has_note():
            self.next_state(self.holding_note)
