class DomainException(Exception):
    """Base exception for domain business rule violations."""
    pass


class TableNotFoundError(DomainException):
    def __init__(self, message: str = "Table not found"):
        super().__init__(message)


class TableAlreadyOccupiedError(DomainException):
    def __init__(self, message: str = "Table is currently occupied with an active session"):
        super().__init__(message)


class CustomerAlreadyHasActiveSessionError(DomainException):
    def __init__(self, message: str = "Customer already has an active dining session"):
        super().__init__(message)


class SessionNotFoundError(DomainException):
    def __init__(self, message: str = "Dining session not found"):
        super().__init__(message)


class SessionNotActiveError(DomainException):
    def __init__(self, message: str = "Dining session is not active"):
        super().__init__(message)


class OrderNotFoundError(DomainException):
    def __init__(self, message: str = "Order not found"):
        super().__init__(message)


class InvalidOrderStatusTransitionError(DomainException):
    def __init__(self, message: str = "Invalid order status transition"):
        super().__init__(message)
