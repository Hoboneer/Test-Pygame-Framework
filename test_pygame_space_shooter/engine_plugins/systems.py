import json
import os
from contextlib import suppress
from typing import Dict, Optional, TYPE_CHECKING, Generator, Tuple, List
from mypy_extensions import TypedDict

from pygame.image import load as pyg_load
import pygame.locals as pyg_locals

if TYPE_CHECKING:
    from pygame import Surface
    from pygame.event import EventType

from vectormath import Vector2

from ..engine.core.ecs import EntityManager
from ..engine.core.ecs.events import EntityManagerEvent, EntityManagerEventID, RemoveEntityID, EntityAddedID
from ..engine.core.ecs.types import EntityID, Entity, System

ImageInfo = TypedDict("ImageInfo",
                     {
                        "name": str,
                        "colorkey": Optional[List[int]]
                     })

class HealthSystem:
    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        ...


class PlayerInputsHandlerCombatSystem:
    def __init__(self) -> None:
        # self.entities = {}  # type: Dict[EntityID, Entity]
        self.player = {}  # type: Entity
        self._player_id = None  # type: int
        self._with_components = {"PositionComponent2D", "PhysicsComponent2D", "AbsoluteDirectionalMovementComponent2D", "EntityLabelComponent", "MovementFlagsComponent2D"}

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        entity_id = event.info["entity_id"]
        if event.id == RemoveEntityID:
            if self._player_id is not None:
                if entity_id == self._player_id:
                    self.player.clear()
        elif event.id == EntityAddedID:
            new_entity = entity_manager.get_matching_entity(entity_id, self._with_components)
            if new_entity is not None:
                if new_entity["EntityLabelComponent"].label == "player":
                    self.player = new_entity
                    self._player_id = entity_id
        else:
            raise RuntimeError("You shouldn't have gotten here!")

    def handle_pygame_keydown_event(self, event: "EventType") -> None:
        movement_flags_comp = self.player["MovementFlagsComponent2D"]
        if event.key == pyg_locals.K_UP:
            movement_flags_comp.moving_up = True
        elif event.key == pyg_locals.K_DOWN:
            movement_flags_comp.moving_down = True
        elif event.key == pyg_locals.K_RIGHT:
            movement_flags_comp.moving_right = True
        elif event.key == pyg_locals.K_LEFT:
            movement_flags_comp.moving_left = True
        elif event.key == pyg_locals.K_SPACE:
            physics_comp = self.player["PhysicsComponent2D"]

            fx, fy = physics_comp._forces
            ax, ay = physics_comp._acceleration
            vx, vy = physics_comp.velocity
            mvx, mvy = physics_comp._max_velocity
            m = physics_comp.mass

            print("Player physics || Forces: ({fx}, {fy}) | Acceleration: ({ax}, {ay}) | Velocity: ({vx}, {vy}) | Max Velocity: ({mvx}, {mvy}) | Mass: {m}".format(**locals()))
            # ...  # shoot or something

    def handle_pygame_keyup_event(self, event: "EventType") -> None:
        movement_flags_comp = self.player["MovementFlagsComponent2D"]
        if event.key == pyg_locals.K_UP:
            movement_flags_comp.moving_up = False
        elif event.key == pyg_locals.K_DOWN:
            movement_flags_comp.moving_down = False
        elif event.key == pyg_locals.K_RIGHT:
            movement_flags_comp.moving_right = False
        elif event.key == pyg_locals.K_LEFT:
            movement_flags_comp.moving_left = False

    def handle_pygame_mouse_button_down_event(self, event: "EventType") -> None:
        ...

    def handle_pygame_mouse_button_up_event(self, event: "EventType") -> None:
        ...


class MovementApplySystem:
    def __init__(self) -> None:
        self.entities = {}  # type: Dict[EntityID, Entity]
        self._with_components = {"AbsoluteDirectionalMovementComponent2D", "MovementFlagsComponent2D", "PhysicsComponent2D"}

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        entity_id = event.info["entity_id"]
        if event.id == RemoveEntityID:
            with suppress(KeyError):
                del self.entities[entity_id]
        elif event.id == EntityAddedID:
            new_entity = entity_manager.get_matching_entity(entity_id, self._with_components)
            if new_entity is not None:
                self.entities[entity_id] = new_entity
        else:
            raise RuntimeError("You shouldn't have gotten here!")

    def apply_movement_flags(self) -> None:
        for entity in self.entities.values():
            movement_comp = entity["AbsoluteDirectionalMovementComponent2D"]
            movement_flags_comp = entity["MovementFlagsComponent2D"]
            physics_comp = entity["PhysicsComponent2D"]

            if movement_flags_comp.moving_up:
                physics_comp.apply_force_vector(movement_comp.movement_force_vectors[pyg_locals.K_UP])
            if movement_flags_comp.moving_down:
                physics_comp.apply_force_vector(movement_comp.movement_force_vectors[pyg_locals.K_DOWN])
            if movement_flags_comp.moving_right:
                physics_comp.apply_force_vector(movement_comp.movement_force_vectors[pyg_locals.K_RIGHT])
            if movement_flags_comp.moving_left:
                physics_comp.apply_force_vector(movement_comp.movement_force_vectors[pyg_locals.K_LEFT])


class TextLinksSystem:
    def __init__(self) -> None:
        self.entities = {}  # type: Dict[EntityID, Entity]
        self.text_entities = {}  # type: Dict[EntityID, Entity]

        self._with_components = {"TextLinkedComponent", "EntityLabelComponent", "PositionComponent2D", "PhysicsComponent2D"}
        self._with_components_text = {"ScreenTextComponent", "EntityLabelComponent"}

    def handle_text_links(self) -> None:
        for entity in self.entities.values():
            text_link_comp = entity["TextLinkedComponent"]
            label_comp = entity["EntityLabelComponent"]
            game_pos_comp = entity["PositionComponent2D"]
            physics_comp = entity["PhysicsComponent2D"]

            if label_comp.label == "player":
                if "player_position" in text_link_comp.links:
                    linked_text_entity = self.text_entities[text_link_comp.links["player_position"]]
                    screen_text_comp = linked_text_entity["ScreenTextComponent"]
                    screen_text_comp.format_text(game_pos_comp.x, game_pos_comp.y)
                if "player_physics" in text_link_comp.links:
                    linked_text_entity = self.text_entities[text_link_comp.links["player_physics"]]
                    screen_text_comp = linked_text_entity["ScreenTextComponent"]
                    try:
                        screen_text_comp.format_text(fx = physics_comp._forces.x,
                                                     fy = physics_comp._forces.y,
                                                     ax = physics_comp._acceleration.x,
                                                     ay = physics_comp._acceleration.y,
                                                     vx = physics_comp.velocity.x,
                                                     vy = physics_comp.velocity.y,
                                                     mvx = physics_comp._max_velocity.x,
                                                     mvy = physics_comp._max_velocity.y,
                                                     m = physics_comp.mass)
                    except AttributeError:
                        screen_text_comp.format_text(fx = physics_comp._forces.x,
                                                     fy = physics_comp._forces.y,
                                                     ax = physics_comp._acceleration.x,
                                                     ay = physics_comp._acceleration.y,
                                                     vx = physics_comp.velocity.x,
                                                     vy = physics_comp.velocity.y,
                                                     mvx = None,
                                                     mvy = None,
                                                     m = physics_comp.mass)

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        entity_id = event.info["entity_id"]
        if event.id == RemoveEntityID:
            with suppress(KeyError):
                del self.entities[entity_id]
                del self.text_entities[entity_id]
        elif event.id == EntityAddedID:
            new_entity = entity_manager.get_matching_entity(entity_id, self._with_components)
            if new_entity is not None:
                self.entities[entity_id] = new_entity
            else:
                new_text_entity = entity_manager.get_matching_entity(entity_id, self._with_components_text)
                if new_text_entity is not None:
                    self.text_entities[entity_id] = new_text_entity
        else:
            raise RuntimeError("You shouldn't have gotten here!")


class DrawSystem:
    def __init__(self) -> None:
        self.entities = {}  # type: Dict[EntityID, Entity]
        self.text_entities = {}  # type: Dict[EntityID, Entity]
        self.background_img = None  # type: Surface
        self._with_components = {"ImageComponent", "ScreenPosComponent2D", "PositionComponent2D", "DrawSystemFlagsComponent", "EntityLabelComponent"}
        self._with_components_text = {"ScreenPosComponent2D", "ScreenTextComponent", "EntityLabelComponent"}

    def clear_entities(self) -> None:
        self.entities.clear()
        self.text_entities.clear()

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        entity_id = event.info["entity_id"]
        if event.id == RemoveEntityID:
            with suppress(KeyError):
                del self.entities[entity_id]
                del self.entities[entity_id]
        elif event.id == EntityAddedID:
            new_entity = entity_manager.get_matching_entity(entity_id, self._with_components)
            if new_entity is not None:
                self.entities[entity_id] = new_entity
            else:
                new_text_entity = entity_manager.get_matching_entity(entity_id, self._with_components_text)
                if new_text_entity is not None:
                    self.text_entities[entity_id] = new_text_entity

        else:
            raise RuntimeError("You shouldn't have gotten here! (in `DrawSystem.handle_event` else-branch)")

    def draw(self, screen: "Surface") -> None:
        screen.fill((255, 255, 255))  # Filled with black
        screen.blit(self.background_img, (0, 0))  # Blitted at the topleft corner of screen (it's assumed it fills the whole thing)
        for entity in self.entities.values():
            game_pos_comp = entity["PositionComponent2D"]
            screen_pos_comp = entity["ScreenPosComponent2D"]
            image_comp = entity["ImageComponent"]
            flags_comp = entity["DrawSystemFlagsComponent"]

            # Correcting screen pos to be what `game_pos_comp` is-- to be an int and updated
            screen_pos_comp.pos.centerx = game_pos_comp.x
            screen_pos_comp.pos.centery = game_pos_comp.y

            screen.blit(image_comp.image, screen_pos_comp.pos)

            if flags_comp.collided:
                # screen.blit(some_explosion_image)
                pass

        for text_entity in self.text_entities.values():
            screen_pos_comp = text_entity["ScreenPosComponent2D"]
            screen_text_comp = text_entity["ScreenTextComponent"]
            label_comp = text_entity["EntityLabelComponent"]
            if label_comp.label == "player_position":
                GREEN = (60, 245, 85)
                new_text_surface, _ = screen_text_comp.font.render(screen_text_comp.text, fgcolor=GREEN)
                screen.blit(new_text_surface, screen_pos_comp.pos)
            elif label_comp.label == "player_physics":
                GREEN = (60, 245, 85)
                new_text_surface, _ = screen_text_comp.font.render(screen_text_comp.text, fgcolor=GREEN)
                screen.blit(new_text_surface, screen_pos_comp.pos)


class PhysicsSimulationSystem:
    def __init__(self) -> None:
        self.entities = {}  # type: Dict[EntityID, Entity]
        self._with_components = {"PositionComponent2D", "PhysicsComponent2D", "ComplexHitboxComponent2D", "DrawSystemFlagsComponent"}

    def clear_entities(self) -> None:
        self.entities.clear()

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        entity_id = event.info["entity_id"]
        if event.id == RemoveEntityID:
            with suppress(KeyError):
                del self.entities[entity_id]
        elif event.id == EntityAddedID:
            new_entity = entity_manager.get_matching_entity(entity_id, self._with_components)
            if new_entity is not None:
                self.entities[entity_id] = new_entity
        else:
            raise RuntimeError("You shouldn't have gotten here! (in `PhysicsSimulationSystem.handle_event` else-branch)")

    def _get_collisions(self) -> Generator[Tuple[EntityID, EntityID], None, None]:
        # entities_as_list = list(self.entities.values())
        sorted_entities = list(sorted(self.entities.items()))
        for entity1_info, entity2_info in zip(sorted_entities, sorted_entities):  # type: Tuple[EntityID, Entity], Tuple[EntityID, Entity]
            hitbox_comp1 = entity1_info[1]["ComplexHitboxComponent2D"]
            hitbox_comp2 = entity2_info[1]["ComplexHitboxComponent2D"]
            if hitbox_comp1.collides_with(hitbox_comp2):
                # Yields the EntityIDs of each entity in collision
                yield (entity1_info[0], entity2_info[0])
            else:
                continue

    def simulate_physics(self, entity_manager: EntityManager, dt: float) -> None:
        for entity in self.entities.values():
            physics_comp  = entity["PhysicsComponent2D"]
            game_pos_comp = entity["PositionComponent2D"]
            hitbox_comp   = entity["ComplexHitboxComponent2D"]

            physics_comp.calculate_acceleration()
            physics_comp.apply_acceleration(dt)
            game_pos_comp += physics_comp.velocity * dt

            # Move the hitbox to its new place
            hitbox_comp.reposition(physics_comp.velocity, dt)

        for entity_id1, entity_id2 in self._get_collisions():
            entity1_draw_system_flags_comp = self.entities[entity_id1]["DrawSystemFlagsComponent"]
            entity2_draw_system_flags_comp = self.entities[entity_id2]["DrawSystemFlagsComponent"]

            entity1_draw_system_flags_comp.collided = True
            entity2_draw_system_flags_comp.collided = True

            # `...collided_at` is their game positions (separate) for now
            entity1_game_pos_comp = self.entities[entity_id1]["PositionComponent2D"]
            entity2_game_pos_comp = self.entities[entity_id2]["PositionComponent2D"]
            entity1_draw_system_flags_comp.collided_at = entity1_game_pos_comp
            entity2_draw_system_flags_comp.collided_at = entity2_game_pos_comp

            entity_manager.remove_entity(entity_id1, immediate=False)
            entity_manager.remove_entity(entity_id2, immediate=False)


class AssetsLoadError(Exception):
    pass

class AssetsManagerSystem:
    def __init__(self,
                 project_folder_name: Optional[str] = None,
                 plugins_folder_name: Optional[str] = None) -> None:
        self.images = {}  # type: Dict[str, Surface]
        self._images_info = {}  # type: Dict[str, ImageInfo]

        self._project_folder_name = project_folder_name if project_folder_name is not None else "."
        self._plugins_folder_name = plugins_folder_name if plugins_folder_name is not None else "."
        self._path_to_images = os.path.join(self._project_folder_name, self._plugins_folder_name, "assets", "images")
        self._info_json_name = "info.json"

    def handle_event(self, entity_manager: EntityManager, event: EntityManagerEvent) -> None:
        pass

    def load_images(self) -> None:
        # with open(os.path.join(self._path_to_images, self._info_json_name), "r") as f:
        #     self._images_info.update(json.load(f))
        try:
            info_json_path = os.path.join(self._path_to_images, self._info_json_name)
            f = open(info_json_path, "r")
        except Exception as e:
            raise AssetsLoadError("Some exception occurred when trying to load {}, with exception {}".format(os.path.split(info_json_path)[1], e))
        else:
            self._images_info.update(json.load(f))
            for image_fname in self._images_info.keys():
                image_name = self._images_info[image_fname]["name"]
                try:
                    self.images[image_name] = pyg_load(os.path.join(self._path_to_images, image_fname))
                except Exception as e:
                    raise AssetsLoadError("Some exception occurred when trying to load {}, with exception {}".format(image_fname, e))
                else:
                    image_colorkey = self._images_info[image_fname]["colorkey"]
                    if image_colorkey is not None:
                        if len(image_colorkey) == 3:
                            self.images[image_name].set_colorkey(image_colorkey)
                        else:
                            raise AssetsLoadError("Could not load image '{}' because key 'colorkey' is not valid- it must be an array of 3 ints OR null".format(image_fname))
                    self.images[image_name] = self.images[image_name].convert()
        finally:
            f.close()