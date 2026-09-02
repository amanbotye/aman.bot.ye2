from enum import IntEnum


class CustomerState(IntEnum):
    NAME_INPUT = 1
    COMPANY_SELECTION = 2
    PHONE_INPUT = 3
    PHONE_CONFIRMATION = 4
