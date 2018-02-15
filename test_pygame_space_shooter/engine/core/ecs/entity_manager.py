from typing import Set, Dict, Iterable, Mapping, Any, Optional, Type, List, Union, cast
from mypy_extensions import TypedDict
from .events import EntityManagerEvent, RemoveEntity, EntityAdded
from .types import (Entity, EntityID, EntityManagerEventID,
                    ComponentName, ComponentObject, NewComponentInfo)


class ECSError(Exception):
    pass

class InvalidComponentNameError(ECSError):
    pass

class IncompleteNewComponentInfo(ECSError):
    pass

class InvalidComponentTypeError(ECSError):
    pass

class InvalidEntityIDError(ECSError):
    pass


class EntityManagerEventQueue:
    def __init__(self) -> None:
        self.events = []  # type: List[EntityManagerEvent]

    def get(self) -> List[EntityManagerEvent]:
        to_return = self.events.copy()
        self.events.clear()
        return to_return

    def push(self, event_obj: EntityManagerEvent) -> None:
        self.events.append(event_obj)


class EntityManager:
    def __init__(self, to_register: Optional[Dict[ComponentName, Type]] = None) -> None:
        self.entities = {}  # type: Dict[EntityID, Set[ComponentName]]
        self.components = {}  # type: Dict[ComponentName, Dict[EntityID, ComponentObject]]
        self.events = EntityManagerEventQueue()

        self._component_classes = {}  # type: Dict[ComponentName, Type]
        self._entities_to_remove = set()  # type: Set[EntityID]
        self._next_entity_id = 0

        if to_register is not None:
            for component_name, component_cls in to_register.items():
                self.register_component(component_name, component_cls)

    def register_component(self, component_name: ComponentName, component_cls: Type) -> None:
        self._component_classes[component_name] = component_cls
        self.components[component_name] = {}

    @property
    def registered_components(self) -> Set[ComponentName]:
        return set(self._component_classes.keys())

    @property
    def live_entities(self) -> Set[EntityID]:
        return set(self.entities.keys())

    def _is_component_names_valid(self, component_names: Set[ComponentName]) -> bool:
        try:
            return component_names <= self.registered_components
        except TypeError:
            raise ValueError("Function `_is_component_names_valid` requires input to be a set. Got `{}` instead".format(component_names.__class__.__name__))

    def add_component_to_entity(self, entity_id: EntityID, component_name: ComponentName, new_component_info: NewComponentInfo) -> None:
        if entity_id not in self.live_entities:
            raise InvalidEntityIDError("Failed to add component to entity because `entity_id` does not exist ({})".format(entity_id))
        if component_name not in self.registered_components:
            raise InvalidComponentNameError("Failed to add component to entity because `component_name` is not an existing or registered component")

        try:
            args = new_component_info["args"]
            kwargs = new_component_info["kwargs"]
        except KeyError:
            raise IncompleteNewComponentInfo("Failed to add component to entity because `new_component_info` does not have all the required keys: 'args' and 'kwargs'")
        else:
            component_cls = self._component_classes[component_name]
            self.components[component_name][entity_id] = component_cls(*args, **kwargs)

    def create_entity(self, components: Dict[ComponentName, Union[NewComponentInfo, ComponentObject]], instantiated: bool = False) -> EntityID:
        if not self._is_component_names_valid(set(components.keys()))
            raise InvalidComponentNameError("Failed to add new entity to EntityManager because `components` has keys of non-existent components`")

        current_entity_id = self._next_entity_id
        if not instantiated:
            new_components = cast(Dict[ComponentName, NewComponentInfo], components)
            for component_name in components.keys():
                args = new_components[component_name]["args"]
                kwargs = new_components[component_name]["kwargs"]    
                component_cls = self._component_classes[component_name]
                self.components[component_name][current_entity_id] = component_cls(*args, **kwargs)

            self.entities[current_entity_id] = set(components.keys())
            self._next_entity_id += 1

        else:
            # Runtime type-checking
            for new_component_name, new_component_obj in components.items():
                new_component_type = type(new_component_obj)
                expected_type = self._component_classes[new_component_name]
                if new_component_type != expected_type:
                    raise InvalidComponentTypeError("Instantiated component type ({new_component_type}) does not match expected type ({expected_type})".format_map(locals()))
                else:
                    self.components[new_component_name][current_entity_id] = new_component_obj

            self.entities[current_entity_id] = set(components.keys())
            self._next_entity_id += 1

        self.events.push(EntityAdded(info={"entity_id": current_entity_id}))
        return current_entity_id

    def get_matching_entities(self, with_components: Set[ComponentName]) -> Dict[EntityID, Entity]:
        if any(component_name not in self._component_classes for component_name in with_components):
            raise InvalidComponentNameError("Failed to get matching entities because `with_components` has keys of non-existent components")

        entities = {}  # type: Dict[EntityID, Entity]

        # Initialise `entities` with empty dicts for all entities that match `with_components`
        entities_set = set(self.entities.keys())  # type: Set[EntityID]
        components_set = {entity_id for component_name in self.components.keys() for entity_id in self.components[component_name]}  # type: Set[EntityID]
        matching_entities = set.intersection(components_set, entities_set)  # type: Set[EntityID]
        for entity_id in matching_entities:
            entities[entity_id] = {}

        for component_name in with_components:
            for entity_id, component_obj in self.components[component_name].items():
                if entity_id in matching_entities:
                    entities[entity_id][component_name] = component_obj

        return entities

    def get_matching_entity(self, entity_id: EntityID, with_components: Set[ComponentName]) -> Optional[Entity]:
        # Used to get a *specific* entity's *specific* components
        if any(component_name not in self._component_classes for component_name in with_components):
            raise InvalidComponentNameError("Failed to get matching entity because `with_components` has keys of non-existent components")

        try:
            entity_component_names = self.entities[entity_id]
        except KeyError:
            raise InvalidEntityIDError("Failed to get matching entity entity because `entity_id` has {} which does not exist".format(entity_id))
        else:
            matching_components = set.intersection(entity_component_names, with_components)
            if matching_components != with_components:  # Entity does not match pattern
                return None

            entity = {}  # type: Entity
            for component_name in matching_components:
                component_obj = self.components[component_name][entity_id]
                entity[component_name] = component_obj
            return entity

    def get_entity(self, entity_id: EntityID) -> Entity:
        try:
            entity_component_names = self.entities[entity_id]
        except KeyError:
            raise InvalidEntityIDError("Failed to get entity with ID '{}' because does not exist".format(entity_id))
        else:
            entity = {}  # type: Entity
            for component_name in entity_component_names:
                component_obj = self.components[component_name][entity_id]
                entity[component_name] = component_obj
            return entity

    def remove_entity(self, entity_id: EntityID, immediate: bool = True) -> None:
        if entity_id not in self.live_entities:
            raise InvalidEntityIDError("Could not remove entity with ID '{}' because it does not exist".format(entity_id))            

        if immediate:
            self.events.push(RemoveEntity(info={"entity_id": entity_id}))

            for component_name in self.entities[entity_id]:
                del self.components[component_name][entity_id]

            del self.entities[entity_id]
        else:
            self._entities_to_remove.add(entity_id)

    def remove_queued_entities(self) -> None:
        for entity_id in self._entities_to_remove:
            self.remove_entity(entity_id, immediate=True)
        self._entities_to_remove.clear()