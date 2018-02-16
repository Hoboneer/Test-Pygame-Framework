from typing import (
    Set, Dict, List,
    Iterable, Iterator, Mapping, Callable, AbstractSet,
    Any, Optional, Type, Union,
    cast
)
from mypy_extensions import TypedDict
from .events import EntityManagerEvent, RemoveEntity, EntityAdded
from .types import (
    Entity, EntityID, EntityManagerEventID,
    ComponentName, ComponentObject, NewComponentInfo
)
from .aspect import Aspect


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

    def _is_component_names_valid(self, component_names: AbstractSet[ComponentName]) -> bool:
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
        if not self._is_component_names_valid(set(components.keys())):
            raise InvalidComponentNameError("Failed to add new entity to EntityManager because `components` has keys of non-existent components`")

        current_entity_id = self._next_entity_id
        if not instantiated:
            new_components = cast(Dict[ComponentName, NewComponentInfo], components)
            for component_name in new_components.keys():
                try:
                    args = new_components[component_name]["args"]
                    kwargs = new_components[component_name]["kwargs"]
                except KeyError:
                    raise IncompleteNewComponentInfo("Failed to add component named '{component_name}' to entity because new component info does not have all the required keys: 'args' and 'kwargs'".format_map(locals()))
                else:
                    component_cls = self._component_classes[component_name]
                    self.components[component_name][current_entity_id] = component_cls(*args, **kwargs)

            self.entities[current_entity_id] = set(new_components.keys())
            self._next_entity_id += 1

        else:
            # Runtime type-checking
            new_components = cast(Dict[ComponentName, ComponentObject], components)
            for new_component_name, new_component_obj in new_components.items():
                new_component_type = type(new_component_obj)
                expected_type = self._component_classes[new_component_name]
                if new_component_type != expected_type:
                    raise InvalidComponentTypeError("Instantiated component type ({new_component_type}) does not match expected type ({expected_type})".format_map(locals()))
                else:
                    self.components[new_component_name][current_entity_id] = new_component_obj

            self.entities[current_entity_id] = set(new_components.keys())
            self._next_entity_id += 1

        self.events.push(EntityAdded(info={"entity_id": current_entity_id}))
        return current_entity_id

    def _group_entity_pattern_match(self, pattern: Aspect) -> Set[EntityID]:
        filter_func = (lambda c, p: self._is_component_names_valid(c | p) and c >= p)  # type: Callable[[AbstractSet[ComponentName], AbstractSet[ComponentName]], bool]

        matching_mandatory_entities = {entity_id for entity_id, component_names in self.entities.items() if filter_func(component_names, pattern.mandatory)}  # type: Set[EntityID]
        matching_xor_entities = {entity_id for entity_id, component_names in self.entities.items() if all(pattern._xor(component_names))}  # type: Set[EntityID]

        matching_entities = matching_mandatory_entities & matching_xor_entities
        return matching_entities

    def get_matching_entities(self, pattern: Aspect) -> Dict[EntityID, Entity]:
        if not self._is_component_names_valid(pattern.all):
            raise InvalidComponentNameError("Failed to get matching entities because `pattern` has keys of non-existent components")

        matching_entities = self._group_entity_pattern_match(pattern)

        entity_views = {entity_id:self._get_matching_entity_no_optional(entity_id, pattern) for entity_id in matching_entities}  # type: Dict[EntityID, Entity]

        return entity_views

    def get_matching_entity(self, entity_id: EntityID, pattern: Aspect) -> Optional[Entity]:
        # Used to get a *specific* entity's *specific* components
        if not self._is_component_names_valid(pattern.all):
            raise InvalidComponentNameError("Failed to get matching entity because `pattern` has keys of non-existent components")

        try:
            entity_component_names = self.entities[entity_id]  # type: Set[ComponentName]
        except KeyError:
            raise InvalidEntityIDError("Failed to get matching entity because `entity_id` is {}, which does not exist".format(entity_id))
        else:
            if pattern.is_matched(entity_component_names):
                # try replace this one below with 1 or 2 set operations (if too slow)
                # This does `s1 | s2` because we already know that it has the mandatory components, but any optionals are OK
                entity_view = {name:(self.components[name][entity_id]) for name in entity_component_names if name in pattern.mandatory | pattern.optional or name in pattern.xor(entity_component_names)}  # type: Entity

                return entity_view
            else:
                return None            

    def _get_matching_entity_no_optional(self, entity_id: EntityID, pattern: Aspect) -> Entity:
        # Used by `get_matching_entities` to avoid a type check error when constructing entity view
        try:
            entity_component_names = self.entities[entity_id]
        except KeyError:
            # Raise `RuntimeError` instead, to indicate that it shouldn't have happened?
            raise InvalidEntityIDError("Failed to get matching entity because `entity_id` is {}, which does not exist (You should not have gotten here!)".format(entity_id))
        else:
            # try replace this one below with 1 or 2 set operations (if too slow)
            # This does `s1 | s2` because we already know that it has the mandatory components, but any optionals are OK
            entity_view = {name:(self.components[name][entity_id]) for name in entity_component_names if name in pattern.mandatory | pattern.optional or name in pattern.xor(entity_component_names)}

            return entity_view

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