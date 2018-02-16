from typing import Iterable, FrozenSet, Set, Generator, TYPE_CHECKING
from itertools import chain

from .types import ComponentName


class Aspect:
    def __init__(self,
                 mandatory: Iterable[ComponentName],
                 optional : Iterable[ComponentName] = (),
                 either_or: Iterable[Iterable[ComponentName]] = ((),)) -> None:
        self._and_components = frozenset(mandatory)
        self._optional_components = frozenset(optional)
        self._xor_components = frozenset(frozenset(options) for options in either_or)
        # should this check if all sets in xor are disjoint with each other?

    @property
    def mandatory(self) -> FrozenSet[ComponentName]:
        return self._and_components

    @property
    def optional(self) -> FrozenSet[ComponentName]:
        return self._optional_components

    @property
    def either_or(self) -> FrozenSet[FrozenSet[ComponentName]]:
        return self._xor_components

    @property
    def flat_either_or(self) -> FrozenSet[ComponentName]:
        return frozenset(chain.from_iterable(self._xor_components))

    @property
    def all(self) -> FrozenSet[ComponentName]:
        return self.mandatory | self.optional | self.flat_either_or

    def is_matched(self, component_names: Set[ComponentName]) -> bool:
        # There are no checks against optional components because it's not needed
        # it (the set of components) should only be required by the entity manager to retrieve entities that also have it
        return component_names >= self._and_components and all(self._xor(component_names))

    def _xor(self, component_names: Set[ComponentName]) -> Generator[bool, None, None]:
        for options in self._xor_components:
            intersect = component_names & options
            yield len(intersect) == 1

    def xor(self, component_names: Set[ComponentName]) -> Generator[ComponentName, None, None]:
        for options in self._xor_components:
            intersect = component_names & options
            if len(intersect) == 1:
                yield intersect.pop()  # The only element in `intersect` should be yielded
            else:
                continue

    def __hash__(self) -> int:
        return hash(self._and_components | self._optional_components | self._xor_components)

    def __eq__(self, other: object) -> bool:
        # I'd really like to enable ducktyping here though... why, mypy
        if isinstance(other, Aspect):
            this_intersects = self.mandatory | self.optional | self.either_or 
            other_intersects = other.mandatory | other.optional | other.either_or
            return this_intersects == other_intersects
        else:
            # A dirty hack to trick mypy into thinking this method is OK and complies
            # with the type signature-- even though `NotImplemented` should be OK here.
            # Though it looks like they're dealing with it. Reference:
            # https://github.com/python/mypy/issues/4534
            if TYPE_CHECKING:
                return False
            else:
                # This is returned at runtime
                return NotImplemented
            

    def __repr__(self) -> str:
        return "<class Aspect ({}|{}|{})>".format(len(self.mandatory), len(self.optional), len(self.either_or))

