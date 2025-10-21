class DatabaseException(Exception):
    pass


class UnknownDatabaseType(DatabaseException):
    pass


class DatabaseConnectionError(DatabaseException):
    pass


class AuthenticationException(Exception):
    pass


class UnknownAuthenticationProvider(AuthenticationException):
    pass


class AuthorizationException(Exception):
    pass


class UnauthorizedUser(AuthorizationException):
    pass


class DiscoveryDocumentError(AuthorizationException):
    pass


class ProviderConnectionError(AuthorizationException):
    pass


class InfrapoleException(Exception):
    pass


class UniqueViolationException(Exception):
    pass

