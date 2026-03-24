from abc import ABC, abstractmethod

from domain.events import DomainEvent
from domain.models.task import Task


class NotificationPort(ABC):
    """Port — contract that the application layer depends on for notifications.
    Concrete adapters (in-memory logger, file logger, …) implement this interface."""

    @abstractmethod
    def dispatch(self, event: DomainEvent) -> None: ...

    @abstractmethod
    def dispatch_all(self, events: list) -> None: ...

    @abstractmethod
    def check_deadline_approaching(self, task: Task) -> None: ...
