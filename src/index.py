import struct
import zlib
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from struct import pack as structpack
from typing import List, Tuple
from binascii import unhexlify
from common import is_windows
from file_system import git_dir


@dataclass
class index_header():
    data_type: str = 'DIRC'
    version: int = 2
    entry_num: int = 0

    def __init__(self, num) -> None:
        self.entry_num = num

    def binary_data(self) -> bytes:
        return self.data_type.encode() + structpack('>II', self.version, self.entry_num)


@dataclass
class index_entry():
    ctime: int = None
    ctime_ns: int = None
    mtime: int = None
    mtime_ns: int = None
    dev: int = None
    ino: int = None
    mode: int = None
    uid: int = None
    gid: int = None
    size: int = None

    def __init__(self, file: Path, assume_unchanged=False) -> None:
        info = file.stat()
        self.ctime = int(info.st_ctime)
        self.ctime_ns = info.st_ctime_ns % 1_000_000_000
        self.mtime = int(info.st_mtime)
        self.mtime_ns = info.st_mtime_ns % 1_000_000_000
        self.dev = 0 if is_windows() else info.st_dev
        self.ino = 0 if is_windows() else info.st_ino
        self.mode = 0x81A4 if is_windows() else info.st_mode
        self.uid = 0 if is_windows() else info.st_uid
        self.gid = 0 if is_windows() else info.st_gid
        self.size = info.st_size
        with file.open(mode='r') as f:
            self.hash, _ = hash_object(f.read())

        assume_flag = 0b0 if not assume_unchanged else 0b1  # Default 0
        extended_flag = 0b0  # if index_version < 3 else 0b1 # Default 0
        optional_flag = (((0b0 | assume_flag) << 1) | extended_flag) << 14
        self.flag_assume = optional_flag | len(file.name)
        self.filename = file.name

    def binary_data(self) -> bytes:
        data = structpack('>IIIIIIIIII20sH',
                          self.ctime, self.ctime_ns, self.mtime, self.mtime_ns,
                          self.dev, self.ino, self.mode, self.uid, self.gid,
                          self.size, bytes.fromhex(self.hash), self.flag_assume)
        data += self.filename.encode()
        padding = 8 - len(data) % 8
        return data + structpack(f'{padding}s', b'\x00')


@dataclass
class index_object():
    header: index_header
    entries: List[index_entry]

    def __init__(self, files: List[Path]) -> None:
        self.header = index_header(len(files))
        self.entries = [index_entry(file) for file in files]

    def binary_data(self) -> bytes:
        data = self.header.binary_data() + b''.join([entry.binary_data() for entry in self.entries])
        return data + bytes.fromhex(sha1(data).hexdigest())
        return data


def write_object(data: str) -> str:
    oid, obj = hash_object(data)
    dir = git_dir().joinpath('objects', oid[:2])
    dir.mkdir(parents=True, exist_ok=True)
    with dir.joinpath(oid[2:]).open('wb') as f:
        f.write(zlib.compress(obj))
    return oid


def hash_object(data: str, obj_type: str = 'blob') -> Tuple[str, bytes]:
    obj = f'{obj_type} {len(data)}\x00{data}'.encode()
    oid = sha1(obj).hexdigest()
    return oid, obj


def update_ref(ref, value):
    print('@ update_ref', value)
    with open(git_dir().joinpath(ref), 'w') as f:
        f.write(f'ref: {value}')


def add(files: List[Path]) -> None:
    for file in files:
        path = Path(file)
        if not path.exists():
            print(f'@File not found ({path})')
            continue
        with path.open(mode='r') as f:
            data = f.read()
        write_object(data)
    update_index(files)


def update_index(files: List[Path]) -> None:
    print('@ update_index')
    with git_dir().joinpath('index').open(mode='wb') as f:
        f.write(index_object(files).binary_data())

