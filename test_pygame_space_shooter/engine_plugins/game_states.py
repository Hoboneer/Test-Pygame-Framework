from typing import Dict, TYPE_CHECKING

from vectormath import Vector2
import pygame.locals as pyg_locals
from pygame import Rect
from pygame.freetype import SysFont

if TYPE_CHECKING:
    from pygame.event import EventType
    from pygame import Surface

from ..engine.core.state_machine import GameState
from ..engine.core.ecs import EntityManager
from ..engine.core.ecs.types import System, SystemName
from .components import (ImageComponent, ScreenPosComponent2D, PositionComponent2D, SimpleHitboxComponent2D, ComplexHitboxComponent2D,
                         AbsoluteDirectionalMovementComponent2D, PhysicsComponent2D, DrawSystemFlagsComponent, ScreenTextComponent,
                         EntityLabelComponent, TextLinkedComponent, MovementFlagsComponent2D)

class CombatState(GameState):
    def __init__(self) -> None:
        super().__init__("CombatState")

    def setup(self, entity_manager: EntityManager, systems: Dict[SystemName, System]) -> None:
        # Creating the text on screen
        # Player coords
        text_coords = (0, 0)
        text_content = "Player coords || x: {} | y: {}"
        # TODO: Figure out how to handle the text component and its position
        new_text_components = {
            "ScreenPosComponent2D": ScreenPosComponent2D(Rect(*text_coords, 1, 1)),
            "ScreenTextComponent": ScreenTextComponent(template=text_content,
                                                       font_obj=SysFont(None, 16)),
            "EntityLabelComponent": EntityLabelComponent("player_position")
        }
        new_text_id = entity_manager.create_entity(new_text_components, instantiated=True)

        # Player forces|acceleration|velocity
        text_coords1 = (0, 20)
        text_content1 = "Player physics || Forces: ({fx:.2f}, {fy:.2f}) | Acceleration: ({ax:.2f}, {ay:.2f}) | Velocity: ({vx:.2f}, {vy:.2f}) | Max Velocity: ({mvx}, {mvy}) | Mass: {m:.2f}"
        # TODO: Figure out how to handle the text component and its position
        new_text_components1 = {
            "ScreenPosComponent2D": ScreenPosComponent2D(Rect(*text_coords1, 1, 1)),
            "ScreenTextComponent": ScreenTextComponent(template=text_content1,
                                                       font_obj=SysFont(None, 16)),
            "EntityLabelComponent": EntityLabelComponent("player_physics")
        }
        new_text_id1 = entity_manager.create_entity(new_text_components1, instantiated=True)

        # Creating the player entity
        player_width, player_height = 50, 25
        player_corner_start_pos = (0, 0)

        player_start_pos = (0 + player_width / 2, 0 + player_height / 2)

        player_movement_force_vectors = {
            pyg_locals.K_UP    : Vector2( 0,-1000 ), 
            pyg_locals.K_DOWN  : Vector2( 0, 1000 ),
            pyg_locals.K_RIGHT : Vector2( 1000, 0 ),
            pyg_locals.K_LEFT  : Vector2(-1000, 0 )
        }

        player_mass = 50  # 50 kg
        # player_max_velocity = Vector2(10, 10)  # 10 m/s
        player_max_velocity = None

        player_text_links = {
            "player_position": new_text_id,
            "player_physics": new_text_id1
        }

        new_player_components = {
            "ImageComponent": ImageComponent(systems["AssetsManagerSystem"].images["TEST_SPACESHIP"]),
            "ScreenPosComponent2D": ScreenPosComponent2D(Rect(player_corner_start_pos, (player_width, player_height))),
            "PositionComponent2D": PositionComponent2D(player_start_pos),
            "ComplexHitboxComponent2D": ComplexHitboxComponent2D(),
            "AbsoluteDirectionalMovementComponent2D": AbsoluteDirectionalMovementComponent2D(player_movement_force_vectors),
            "PhysicsComponent2D": PhysicsComponent2D(player_mass, player_max_velocity),
            "DrawSystemFlagsComponent": DrawSystemFlagsComponent(),
            "EntityLabelComponent": EntityLabelComponent("player"),
            "TextLinkedComponent": TextLinkedComponent(links=player_text_links),
            "MovementFlagsComponent2D": MovementFlagsComponent2D()
        }
        new_player_id = entity_manager.create_entity(new_player_components, instantiated=True)

        systems["DrawSystem"].background_img = systems["AssetsManagerSystem"].images["TEST_BACKGROUND"]

    def cleanup(self, entity_manager: EntityManager, systems: Dict[SystemName, System]) -> None:
        # raise NotImplementedError
        entity_manager.remove_queued_entities()

    def handle_event(self, entity_manager: EntityManager, systems: Dict[SystemName, System], event: "EventType") -> None:
        if event.type == pyg_locals.KEYDOWN:
            systems["PlayerInputsHandlerCombatSystem"].handle_pygame_keydown_event(event)
        elif event.type == pyg_locals.KEYUP:
            systems["PlayerInputsHandlerCombatSystem"].handle_pygame_keyup_event(event)

    def update(self, entity_manager: EntityManager, systems: Dict[SystemName, System], dt: float) -> None:
        entity_manager.remove_queued_entities()
        for event in entity_manager.events.get():
            for system_obj in systems.values():
                system_obj.handle_event(entity_manager, event)
        systems["TextLinksSystem"].handle_text_links()
        systems["MovementApplySystem"].apply_movement_flags()
        systems["PhysicsSimulationSystem"].simulate_physics(entity_manager, dt)

    def draw(self, screen: "Surface", systems: Dict[SystemName, System]) -> None:
        systems["DrawSystem"].draw(screen)
