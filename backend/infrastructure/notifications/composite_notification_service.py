"""
Composite notification adapter — fans out every event to multiple adapters.
Both the in-memory logger and the file logger receive every notification,
keeping each adapter focused on a single concern.
"""

from domain.events import DomainEvent
from domain.models.task import Task
from domain.ports.notification_port import NotificationPort


class CompositeNotificationService(NotificationPort):
    """Dispatches events to all registered notification adapters."""

    def __init__(self, *adapters: NotificationPort) -> None:
        self._adapters = adapters

    def dispatch(self, event: DomainEvent) -> None:
        for adapter in self._adapters:
            adapter.dispatch(event)

    def dispatch_all(self, events: list) -> None:
        for event in events:
            self.dispatch(event)

    def check_deadline_approaching(self, task: Task) -> None:
        for adapter in self._adapters:
            adapter.check_deadline_approaching(task)
