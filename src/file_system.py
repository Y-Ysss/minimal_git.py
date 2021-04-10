# import os
from pathlib import Path
from data_objects import GIT_DIR
import os
import re
from pathlib import Path
from typing import Generator

from data_objects import GIT_DIR
from gitignore_parser import parse_gitignore


def iter_pathes() -> Generator:

    def is_git_ignored():
        if Path('.gitignore').exists:
            return parse_gitignore('.gitignore')
        else:
            return False

    def is_ignored(path: str) -> bool:
        if GIT_DIR in path.split(os.path.sep) or is_git_ignored(path):
            return True

    for root, dirnames, filenames in os.walk('.'):
        for filename in filenames:
            path = os.path.relpath(os.path.join(root, filename))
            if is_ignored(path) or not os.path.isfile(path):
                continue
            yield path
        for dirname in dirnames:
            path = os.path.relpath(os.path.join(root, dirname))
            if is_ignored(path):
                continue
            yield path


def get_path(path=None) -> Path:
    return Path.cwd() if path is None else Path(path)


def git_dir(path=None) -> Path:
    return get_path(path).joinpath(GIT_DIR)


def up_one_level(path=None) -> Path:
    return get_path(path).parent


def has_git_dir(path) -> bool:
    return True if list(Path(path).glob(GIT_DIR)) else False


def get_git_dir(path) -> Path:
    if has_git_dir(path):
        return git_dir(path)
    else:
        return get_git_dir(up_one_level(path))


def make_base_dirs() -> None:
    g = git_dir()
    print('@', g)
    g.mkdir()
    g.joinpath('objects').mkdir()
    g.joinpath('objects', 'info').mkdir()
    g.joinpath('objects', 'pack').mkdir()
    g.joinpath('refs').mkdir()
    g.joinpath('refs', 'heads').mkdir()
    g.joinpath('refs', 'tags').mkdir()


if __name__ == '__main__':
    print(git_dir())
