from enum import Enum

GIT_DIR = '.testgit'

MAIN_BRANCH = 'main'


class DataType(Enum):
    OBJECT: str = 'object'
    COMMIT: str = 'commit'
    TREE: str = 'tree'
    BLOB: str = 'blob'

    def value_members(cls):
        return [m.value for m in cls.__class__]


