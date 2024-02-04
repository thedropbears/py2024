import dataclasses
import time
import math
import random
from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable, Protocol

import wpilib
from ids import PwmChannels


MAX_BRIGHTNESS = 50  # Integer value 0-255
Hsv = tuple[int, int, int]

FLASH_SPEED = 2
BREATHE_SPEED = 4
RAINBOW_SPEED = 8
MORSE_SPEED = 0.2


class HsvColour(Enum):
    RED = (0, 255, MAX_BRIGHTNESS)
    ORANGE = (20, 255, MAX_BRIGHTNESS)
    YELLOW = (30, 255, MAX_BRIGHTNESS)
    MAGENTA = (150, 255, MAX_BRIGHTNESS)
    BLUE = (120, 255, MAX_BRIGHTNESS)
    CYAN = (90, 255, MAX_BRIGHTNESS)
    GREEN = (60, 255, MAX_BRIGHTNESS)
    WHITE = (0, 0, MAX_BRIGHTNESS)
    OFF = (0, 0, 0)

    def with_hue(self, hue: int) -> Hsv:
        """
        Change the hue of the colour.

        Args:
            hue: The desired hue in [0,180).
        """
        _, s, v = self.value
        return (hue, s, v)

    def with_relative_brightness(self, multiplier: float) -> Hsv:
        """
        Scale the brightness of the colour.

        `multiplier` MUST be non-negative, and SHOULD be <= 1.
        """
        h, s, v = self.value
        return (h, s, int(v * multiplier))


class LightStrip:
    def __init__(self, strip_length: int) -> None:
        self.leds = wpilib.AddressableLED(PwmChannels.led_strip)
        self.leds.setLength(strip_length)
        self.strip_length = strip_length

        self.led_data = wpilib.AddressableLED.LEDData()
        self.strip_data = [self.led_data] * strip_length

        self.pattern: Pattern = Rainbow(HsvColour.MAGENTA)

        self.leds.setData(self.strip_data)
        self.leds.start()

    def want_note(self) -> None:
        self.pattern = Flash(HsvColour.MAGENTA)

    def holding_note(self) -> None:
        self.pattern = Solid(HsvColour.GREEN)

    def shooting(self) -> None:
        self.pattern = Solid(HsvColour.ORANGE)

    def intaking(self) -> None:
        self.pattern = Solid(HsvColour.CYAN)

    def climbing(self) -> None:
        self.pattern = Solid(HsvColour.YELLOW)

    def morse(self) -> None:
        self.pattern = Morse(HsvColour.YELLOW)

    def idle(self) -> None:
        self.pattern = Rainbow(HsvColour.RED)

    def disabled(self) -> None:
        self.pattern = Solid(HsvColour.WHITE)

    # --------------------------------------------------------------------

    def execute(self) -> None:
        colour = self.pattern.update()
        self.led_data.setHSV(*colour)
        self.leds.setData(self.strip_data)


class Pattern(Protocol):
    def update(self) -> Hsv: ...


@dataclasses.dataclass
class Solid(Pattern):
    colour: HsvColour

    def update(self) -> Hsv:
        return self.colour.value


@dataclasses.dataclass(eq=False)
class CommonPattern(ABC, Pattern):
    colour: HsvColour
    clock: Callable[[], float] = time.monotonic
    start_time: float = dataclasses.field(init=False)

    def __post_init__(self) -> None:
        self.start_time = self.clock()

    def elapsed_time(self) -> float:
        return self.clock() - self.start_time

    @abstractmethod
    def update(self) -> Hsv: ...


@dataclasses.dataclass
class Flash(CommonPattern):
    speed: float = FLASH_SPEED

    def update(self) -> Hsv:
        brightness = math.cos(self.speed * self.elapsed_time() * math.tau) >= 0
        return self.colour.with_relative_brightness(brightness)


@dataclasses.dataclass
class Breathe(CommonPattern):
    speed: float = BREATHE_SPEED

    def update(self) -> Hsv:
        brightness = (math.sin(self.speed * self.elapsed_time() * math.tau) + 1) / 2
        return self.colour.with_relative_brightness(brightness)


@dataclasses.dataclass
class Rainbow(CommonPattern):
    speed: float = RAINBOW_SPEED

    def update(self) -> Hsv:
        hue = round(360 * (self.elapsed_time() / self.speed % 1))
        return self.colour.with_hue(hue)


@dataclasses.dataclass
class Morse(CommonPattern):
    speed: float = MORSE_SPEED

    # NOTE Might be better to read this data from a file?
    MESSAGES = (
        "KILL ALL HUMANS",
        "MORSE CODE IS FOR NERDS",
        "HONEYBADGER DONT CARE",
        "GLHF",
        "I HATE MORSE CODE",
    )
    MORSE_TRANSLATION = {
        "A": ".-",
        "B": "-...",
        "C": "-.-.",
        "D": "-..",
        "E": ".",
        "F": "..-.",
        "G": "--.",
        "H": "....",
        "I": "..",
        "J": ".---",
        "K": "-.-",
        "L": ".-..",
        "M": "--",
        "N": "-.",
        "O": "---",
        "P": ".--.",
        "Q": "--.-",
        "R": ".-.",
        "S": "...",
        "T": "-",
        "U": "..-",
        "V": "...-",
        "W": ".--",
        "X": "-..-",
        "Y": "-.--",
        "Z": "--..",
        "1": ".----",
        "2": "..---",
        "3": "...--",
        "4": "....-",
        "5": ".....",
        "6": "-....",
        "7": "--...",
        "8": "---..",
        "9": "----.",
        "0": "-----",
    }
    DOT_LENGTH = 1
    DASH_LENGTH = 3
    SPACE_LENGTH = 4

    def __post_init__(self) -> None:
        super().__post_init__()
        self.pick_new_message()

    def update(self) -> Hsv:
        elapsed_time = self.elapsed_time()
        if elapsed_time > self.message_time:
            return self.colour.value

        # TODO Might be better to store current token index and time?
        running_total = 0.0
        for token in self.morse_message:
            if token == ".":
                running_total += self.DOT_LENGTH * self.speed
            elif token == "-":
                running_total += self.DASH_LENGTH * self.speed
            elif token == " ":
                running_total += self.SPACE_LENGTH * self.speed

            # This is the current character
            if running_total > elapsed_time:
                if token == " ":
                    return HsvColour.OFF.value
                else:
                    return self.colour.value

        # Default (Should never be hit!)
        return HsvColour.OFF.value

    def pick_new_message(self) -> None:
        # QUESTION? Should functions take args or assume previous step already done
        self.message = self.random_message()
        self.morse_message = self.translate_message(self.message)
        self.message_length = self.calculate_message_length(self.morse_message)
        self.message_time = self.speed * self.message_length

    def random_message(self) -> str:
        # TODO Maybe make it not pick the same message as last time?
        return random.choice(self.MESSAGES)

    @classmethod
    def translate_message(cls, message: str) -> str:
        message = message.upper()
        morse_message = ""
        for letter in message:
            if letter == " ":
                morse_message += " "
                continue
            morse_message += cls.MORSE_TRANSLATION[letter] + " "

        # Add some space at end of message
        morse_message += "  "
        return morse_message

    @classmethod
    def calculate_message_length(cls, morse_message: str) -> int:
        return (
            cls.DOT_LENGTH * morse_message.count(".")
            + cls.DASH_LENGTH * morse_message.count("-")
            + cls.SPACE_LENGTH * morse_message.count(" ")
        )
