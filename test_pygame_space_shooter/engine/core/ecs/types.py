from typing import NewType, Any, Mapping, Iterable, Dict, TYPE_CHECKING
from typing_extensions import Protocol
from mypy_extensions import TypedDict

if TYPE_CHECKING:
    from .events import EntityManagerEvent
    from .entity_manager import EntityManager

EntityID = int
EntityManagerEventID = int

ComponentName = str
ComponentObject = Any
NewComponentInfo = TypedDict("NewComponentInfo",
                            {
                                "args": Iterable[Any],
                                "kwargs": Mapping[str, Any]
                            })

Entity = Dict[ComponentName, ComponentObject]


class System(Protocol):
    def handle_event(self, entity_manager: "EntityManager", event: "EntityManagerEvent") -> None:
        raise NotImplementedError

SystemName = str