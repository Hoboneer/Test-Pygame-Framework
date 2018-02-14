from typing import Dict, TYPE_CHECKING
from abc import ABCMeta, abstractmethod

if TYPE_CHECKING:
    from pygame.event import EventType
    from pygame import Surface

from ..ecs.types import System, SystemName
from ..ecs import EntityManager

class GameState(metaclass=ABCMeta):
    def __init__(self, name: str) -> None:
        self.name = name
        self.next_state = None  # type: "GameState"
        self.done = False

    @abstractmethod
    def setup(self, entity_manager: EntityManager, systems: Dict[SystemName, System]) -> None:
        raise NotImplementedError

    @abstractmethod
    def cleanup(self, entity_manager: EntityManager, systems: Dict[SystemName, System]) -> None:
        raise NotImplementedError

    @abstractmethod
    def handle_event(self, entity_manager: EntityManager, systems: Dict[SystemName, System], event: "EventType") -> None:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity_manager: EntityManager, systems: Dict[SystemName, System], dt: float) -> None:
        raise NotImplementedError

    @abstractmethod
    def draw(self, screen: "Surface", systems: Dict[SystemName, System]) -> None:
        raise NotImplementedError

class StateMachineError(Exception):
    pass

class GameStateMachine:
    def __init__(self, states: Dict[str, GameState], init_state: str) -> None:
        self.states = states
        try:
            self.state = self.states[init_state]
        except KeyError:
            raise StateMachineError("Cannot initialise state machine because `init_state` ({}) is not a valid state".format(init_state))

    def change_state(self, entity_manager: EntityManager, systems: Dict[SystemName, System]) -> None:
        # ...
        next_state = self.state.next_state.name
        self.state.cleanup(entity_manager, systems)
        self.state.done = False
        self.state = self.states[next_state]
        self.state.setup(entity_manager, systems)

    def update_state(self, entity_manager: EntityManager, systems: Dict[SystemName, System], dt: float) -> None:
        if self.state.done:
            self.change_state(entity_manager, systems)
        self.state.update(entity_manager, systems, dt)

    def draw_state(self, screen: "Surface", systems: Dict[SystemName, System]) -> None:
        self.state.draw(screen, systems)