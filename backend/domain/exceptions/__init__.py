class DomainException(Exception):
    pass


class DeadlineConstraintError(DomainException):
    pass


class ProjectCompletionError(DomainException):
    pass


class TaskNotFoundError(DomainException):
    pass


class ProjectNotFoundError(DomainException):
    pass


class TaskAlreadyLinkedError(DomainException):
    pass
