from typing import Dict, Any
from functools import partial

from .types import EntityManagerEventID

class EntityManagerEvent:
    def __init__(self, event_id: EntityManagerEventID, info: Dict[str, Any]) -> None:
        self.id = event_id
        self.info = info

RemoveEntityID = 0
RemoveEntity = partial(EntityManagerEvent, RemoveEntityID)

EntityAddedID = 1
EntityAdded = partial(EntityManagerEvent, EntityAddedID)