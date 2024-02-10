import math
import time

from magicbot import StateMachine, state, timed_state, feedback, will_reset_to
from wpimath.geometry import Translation2d

from components.chassis import ChassisComponent
from components.injector import InjectorComponent
from components.intake import IntakeComponent
from components.shooter import ShooterComponent
from utilities.game import get_goal_speaker_position


class NoteManager(StateMachine):

    shooter_component: ShooterComponent

    chassis: ChassisComponent
    injector_component: InjectorComponent
    intake: IntakeComponent

    shot_desired = will_reset_to(False)
    intake_desired = will_reset_to(False)
    intake_cancel_desired = will_reset_to(False)

    def try_intake(self):
        self.intake_desired = True

    def cancel_intake(self):
        self.intake_cancel_desired = True

    def try_shoot(self):
        self.shot_desired = True

    @feedback
    def has_note(self):
        return self.injector_component.has_note()

    def translation_to_goal(self) -> Translation2d:
        return (
            get_goal_speaker_position().toTranslation2d()
            - self.chassis.get_pose().translation()
        )

    def has_just_fired(self) -> bool:
        """Intended to be polled by autonomous to tell when shooting is finished"""
        return self.last_state == "firing" and self.current_state == "idling"

    def execute(self):
        self.last_state = self.current_state
        super().execute()

    def on_enable(self) -> None:
        super().on_enable()
        if self.has_note():
            self.engage()
        else:
            self.engage(self.idling)

    @state(must_finish=True)
    def idling(self):
        self.intake.retract()

        # Update range
        self.shooter_component.set_range(self.translation_to_goal().norm())

        if self.intake_desired:
            self.next_state(self.dropping_intake)

    @state(must_finish=True)
    def dropping_intake(self):
        self.intake.deploy()

        # Update range
        self.shooter_component.set_range(self.translation_to_goal().norm())

        if self.intake.is_fully_deployed():
            self.next_state(self.intaking)

        if self.intake_cancel_desired:
            self.next_state(self.idling)

    @state(must_finish=True)
    def intaking(self, initial_call):
        if initial_call:
            self.note_seen_time = math.inf

        self.intake.intake()
        self.injector_component.intake()

        # Update range
        self.shooter_component.set_range(self.translation_to_goal().norm())

        if self.injector_component.has_note() and self.note_seen_time == math.inf:
            self.note_seen_time = time.monotonic()

        delay = 1  # seconds
        if time.monotonic() > self.note_seen_time + delay:
            self.next_state(self.holding_note)

        if self.intake_cancel_desired:
            self.next_state(self.idling)

    @state(first=True, must_finish=True)
    def holding_note(self):
        self.intake.retract()
        # Update range
        self.shooter_component.set_range(self.translation_to_goal().norm())

        if self.shot_desired:
            self.next_state(self.aiming)

    @state(must_finish=True)
    def aiming(self):
        if not self.shot_desired:
            self.next_state(self.holding_note)
            return

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

    @timed_state(duration=1, next_state=idling, must_finish=True)
    def firing(self):
        self.injector_component.shoot()