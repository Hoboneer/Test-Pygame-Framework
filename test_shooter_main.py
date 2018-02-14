from typing import Dict, Type, Tuple, Optional, TYPE_CHECKING
from mypy_extensions import TypedDict

import pygame

from pygame import Surface, Rect

if TYPE_CHECKING:
    from pygame.event import EventType

from abc import ABCMeta, abstractmethod

from test_pygame_space_shooter.engine.core.ecs import EntityManager
from test_pygame_space_shooter.engine.core.ecs.types import System, ComponentName, SystemName
from test_pygame_space_shooter.engine.core.state_machine import GameStateMachine, GameState

from test_pygame_space_shooter.engine_plugins.game_states import CombatState
from test_pygame_space_shooter.engine_plugins.components import (ImageComponent, ScreenPosComponent2D, PositionComponent2D, SimpleHitboxComponent2D, ComplexHitboxComponent2D,
                                                                 AbsoluteDirectionalMovementComponent2D, PhysicsComponent2D, DrawSystemFlagsComponent, ScreenTextComponent,
                                                                 EntityLabelComponent, TextLinkedComponent, MovementFlagsComponent2D)
from test_pygame_space_shooter.engine_plugins.systems import PlayerInputsHandlerCombatSystem, DrawSystem, PhysicsSimulationSystem, AssetsManagerSystem, TextLinksSystem, MovementApplySystem


GameInfo = TypedDict("GameInfo",
                    {
                        "title": str,
                        "max_fps": Optional[int],
                        "screen_size": Tuple[int, int],
                        "icon_name": str
                    })

SCREEN_SIZE = (720, 480)

class GameError(Exception):
    pass

class Context:
    def __init__(self, screen: Surface, screen_rect: Rect) -> None:
        self.screen = screen
        self.screen_rect = screen_rect

class BaseGame(metaclass=ABCMeta):
    def __init__(self, state_machine: GameStateMachine, entity_manager: EntityManager, systems: Dict[str, System], info: GameInfo) -> None:
        self.done = False
        self.title = info.get("title", "<No Title Supplied>")

        self.state_machine = state_machine

        self.entity_manager = entity_manager
        self.systems = systems

        # self.screen = pygame.display.set_mode(info["screen_size"])
        # self.screen_rect = self.screen.get_rect()  # HIGHLY dependent on pygame-- make this more general

        # self.clock = pygame.time.Clock()  # Same here

        # self._current_

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    def event_loop(self) -> None:
        for event in pygame.event.get():  # type: EventType
            if event.type == pygame.QUIT:
                self.done = True
            else:
                self.state_machine.state.handle_event(self.entity_manager, self.systems, event)  # other stuff?


class PygameGame(BaseGame):
    def __init__(self, state_machine: GameStateMachine, entity_manager: EntityManager, systems: Dict[str, System], info: GameInfo) -> None:
        super().__init__(state_machine, entity_manager, systems, info)

        try:
            self.screen = pygame.display.set_mode(info["screen_size"])
            icon_name = info["icon_name"]
        except KeyError:
            raise GameError("Required `info` key 'screen_size' and/or 'icon_name' not supplied")
        else:
            self.systems["AssetsManagerSystem"].load_images()
            self.screen_rect = self.screen.get_rect()
            pygame.display.set_icon(self.systems["AssetsManagerSystem"].images[icon_name])

        self.clock = pygame.time.Clock()
        self.max_fps = info.get("max_fps", 0)
        if self.max_fps is None:
            self.max_fps = 0

    def display_fps(self) -> None:
        pygame.display.set_caption("{} - FPS: {:.2f}".format(self.title, self.clock.get_fps()))

    def run(self) -> None:
        # Setting up the initial state
        self.state_machine.state.setup(self.entity_manager, self.systems)
        while not self.done:
            delta_time = self.clock.tick(self.max_fps) / 1000
            self.event_loop()
            self.state_machine.update_state(self.entity_manager, self.systems, delta_time)
            self.state_machine.draw_state(self.screen, self.systems)
            self.display_fps()
            pygame.display.update()
        self.close()

    def close(self) -> None:
        pass

def main() -> None:
    pygame.display.init()
    pygame.freetype.init()

    _new_combat_state = CombatState()
    game_states = {_new_combat_state.name: _new_combat_state}  # type: Dict[str, GameState]
    game_state_machine = GameStateMachine(states=game_states, init_state=_new_combat_state.name)

    game_components = {
        "ImageComponent": ImageComponent,
        "ScreenPosComponent2D": ScreenPosComponent2D,
        "PositionComponent2D": PositionComponent2D,
        "SimpleHitboxComponent2D": SimpleHitboxComponent2D,
        "ComplexHitboxComponent2D": ComplexHitboxComponent2D,
        "AbsoluteDirectionalMovementComponent2D": AbsoluteDirectionalMovementComponent2D,
        "PhysicsComponent2D": PhysicsComponent2D,
        "DrawSystemFlagsComponent": DrawSystemFlagsComponent,
        "ScreenTextComponent": ScreenTextComponent,
        "EntityLabelComponent": EntityLabelComponent,
        "TextLinkedComponent": TextLinkedComponent,
        "MovementFlagsComponent2D": MovementFlagsComponent2D
    }
    game_entity_manager = EntityManager(to_register=game_components)

    game_systems = {
        "PlayerInputsHandlerCombatSystem": PlayerInputsHandlerCombatSystem(),
        "DrawSystem": DrawSystem(),
        "PhysicsSimulationSystem": PhysicsSimulationSystem(),
        "AssetsManagerSystem": AssetsManagerSystem(project_folder_name="test_pygame_space_shooter",
                                                   plugins_folder_name="engine_plugins"),
        "TextLinksSystem": TextLinksSystem(),
        "MovementApplySystem": MovementApplySystem()
    }  # type: Dict[SystemName, System]

    game = PygameGame(game_state_machine,
                      game_entity_manager,
                      game_systems,
                      info={
                        "title": "Test Pygame Shooter (with ECS)",
                        "max_fps": 60,
                        "screen_size": SCREEN_SIZE,
                        "icon_name": "TEST_ICON"
                      })

    print("about to run")

    game.run()

if __name__ == "__main__":
    main()