from typing import TYPE_CHECKING, Optional, Set, Iterable, Dict, List
from mypy_extensions import TypedDict

from vectormath import Vector2
import pygame.locals as pyg_locals

if TYPE_CHECKING:
    from pygame import Surface, Rect
    from pygame.freetype import Font

from ..engine.core.ecs.types import EntityID

class HealthComponent:
    def __init__(self, value: float) -> None:
        self.value = value


class ImageComponent:
    def __init__(self, image: "Surface") -> None:
        self.image = image


class ScreenPosComponent2D:
    def __init__(self, pos: "Rect") -> None:
        self.pos = pos

PositionComponent2D = Vector2

# TODO: Turn HitboxComponents into holders of *offsets* from their parent entity so no need for `reposition`

class SimpleHitboxComponent2D:
    def __init__(self, left: float, top: float, width: float, height: float) -> None:
        if width > 0 and height > 0:
            self.width  = width
            self.height = height

            self.center = Vector2(left + width / 2, top + height / 2)

            self.topleft     = Vector2(left, top)
            self.topright    = Vector2(left + width, top)
            self.bottomleft  = Vector2(left, top + height)
            self.bottomright = Vector2(left + width, top + height)

            self.left   = left
            self.right  = left + width
            self.top    = top
            self.bottom = top + height 
        else:
            raise ValueError("`width` and `height` must be greater than 0, got ({}, {})".format(width, height))

    def reposition(self, velocity: Vector2, dt: float) -> None:
        self.left += velocity.x * dt
        self.right = self.left + self.width
        self.top += velocity.y * dt
        self.bottom = self.top + self.height

        self.topleft     = Vector2(self.left, self.top)
        self.topright    = Vector2(self.left + self.width, self.top)
        self.bottomleft  = Vector2(self.left, self.top + self.height)
        self.bottomright = Vector2(self.left + self.width, self.top + self.height)

        self.center = Vector2(self.left + self.width / 2, self.top + self.height / 2)

    @property
    def centerx(self) -> float:
        ret = self.center.x  # type: float
        return ret

    @centerx.setter
    def centerx(self, other: float) -> None:
        self.center.x = other

    @property
    def centery(self) -> float:
        ret = self.center.y  # type: float
        return ret

    @centery.setter
    def centery(self, other: float) -> None:
        self.center.y = other

    @classmethod
    def from_rect(cls, rect: "Rect") -> "SimpleHitboxComponent2D":
        return cls(rect.left, rect.top, rect.width, rect.height)

    def collides_with(self, other: "SimpleHitboxComponent2D") -> bool:
        return bool((self.topleft < other.bottomright).all() and (self.bottomright > other.topleft).all())

class ComplexHitboxComponent2D:
    def __init__(self, hitboxes: Optional[Iterable[SimpleHitboxComponent2D]] = None) -> None:
        if hitboxes is not None:
            self.hitboxes = list(hitboxes)
        else:
            self.hitboxes = list()  # type: List[SimpleHitboxComponent2D]

    def collides_with(self, other: "ComplexHitboxComponent2D") -> bool:
        for hitbox1 in self.hitboxes:
            for hitbox2 in other.hitboxes:
                if hitbox1.collides_with(hitbox2):
                    return True
        return False

    def reposition(self, velocity: Vector2, dt: float) -> None:
        for hitbox in self.hitboxes:
            hitbox.reposition(velocity, dt)


class AbsoluteDirectionalMovementComponent2D:
    def __init__(self, movement_force_vectors: Dict[int, Vector2]) -> None:
        self.movement_force_vectors = movement_force_vectors


class MovementFlagsComponent2D:
    # VERY RUDIMENTARY:
    # This should be changed to have a state machine to handle it all easily
    def __init__(self) -> None:
        self.moving_right = False
        self.moving_left = False
        self.moving_up = False
        self.moving_down = False


class PhysicsComponent2D:
    def __init__(self, mass: float, max_velocity: Optional[Vector2] = None) -> None:
        self.velocity = Vector2(0, 0)
        self.mass = mass

        self._max_velocity = max_velocity
        self._forces = Vector2(0, 0)
        self._acceleration = Vector2(0, 0)

    # FORCE APPLICATION: START #
    def apply_force_to_x(self, force: float) -> None:
        self._forces.x += force

    def apply_force_to_y(self, force: float) -> None:
        self._forces.y += force

    def apply_force_vector(self, force_vector: Vector2) -> None:
        self._forces += force_vector
    # FORCE APPLICATION: END #

    # ACCELERATION APPLICATION: START #
    def calculate_acceleration(self) -> None:
        self._acceleration = self._forces / self.mass

    def apply_acceleration(self, dt: float) -> None:
        self.velocity += self._acceleration * dt
        self._forces = Vector2(0, 0)  # Clear the forces acting upon this object for next frame/whatever

        # Keeping velocity in bounds
        if self._max_velocity is not None:
            if abs(self.velocity.x) > self._max_velocity.x:
                if self.velocity.x > 0:
                    self.velocity.x = self._max_velocity.x
                elif self.velocity.x < 0:
                    self.velocity.x = -self._max_velocity.x
            if abs(self.velocity.y) > self._max_velocity.y:
                if self.velocity.y > 0:
                    self.velocity.y = self._max_velocity.y
                elif self.velocity.y < 0:
                    self.velocity.y = -self._max_velocity.y
    # ACCELERATION APPLICATION: END #


class DrawSystemFlagsComponent:
    def __init__(self) -> None:
        self.collided    = False
        self.collided_at = Vector2(0, 0)


class ScreenTextComponent:
    def __init__(self, template: str, font_obj: "Font") -> None:
        self.text = "<TEXT NOT INITIALISED WITH TEMPLATE>"
        self.template = template
        self.font = font_obj

    def format_text(self, *args: str, **kwargs: str) -> None:
        self.text = self.template.format(*args, **kwargs)

class EntityLabelComponent:
    def __init__(self, label: str) -> None:
        self.label = label.lower()


class TextLinkedComponent:
    def __init__(self, links: Dict[str, EntityID]) -> None:
        self.links = links