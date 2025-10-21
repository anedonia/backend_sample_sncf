from enum import StrEnum

class CrudOperation(StrEnum):
    create = "Creating"
    update = "Updating"
    delete = "Deleting"
