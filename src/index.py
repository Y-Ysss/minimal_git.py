import struct
import zlib
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple, Union
from binascii import unhexlify
from common import is_windows
from file_system import git_dir


# @dataclass
# class index_header():
#     data_type: str = 'DIRC'
#     version: int = 2
#     entry_num: int = 0

#     def __init__(self, num) -> None:
#         self.entry_num = num

#     def binary_data(self) -> bytes:
#         return self.data_type.encode() + struct.pack('>II', self.version, self.entry_num)


@dataclass
class IndexEntry():
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
    hash: str = None
    assume_flag: int = None
    extended_flag: int = None
    reserved_flag: int = None # future use
    skip_worktree_flag: int = None
    intent_to_add_flag: int = None
    filename: str = None

    def from_file(self, file: Path, assume_unchanged=False, index_version=0, skip_worktree_flag=0, intent_to_add_flag=0) -> None:
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
        with file.open(mode='rb') as f:
            self.hash, _ = hash_object(f.read().decode())

        self.assume_flag = 0b0 if not assume_unchanged else 0b1  # Default 0
        self.extended_flag = 0b0 if index_version < 3 else 0b1  # Default 0
        self.skip_worktree_flag = skip_worktree_flag if self.extended_flag else 0b0
        self.intent_to_add_flag = intent_to_add_flag if self.extended_flag else 0b0
        self.filename = file.name
        return self

    def binary_data(self) -> bytes:
        optional_flag = (self.assume_flag << 15) | (self.extended_flag << 14)
        flag = optional_flag | len(self.filename)

        data = struct.pack('>IIIIIIIIII20sH',
                           self.ctime, self.ctime_ns, self.mtime, self.mtime_ns,
                           self.dev, self.ino, self.mode, self.uid, self.gid,
                           self.size, bytes.fromhex(self.hash), flag)
        if self.extended_flag:
            extended_optional_flag = (self.reserved_flag << 15) | (self.skip_worktree_flag << 14) | (self.intent_to_add_flag << 13)
            data += struct.pack('>H', extended_optional_flag)
        data += self.filename.encode()
        padding = 8 - len(data) % 8
        return data + struct.pack(f'{padding}s', b'\x00')


@dataclass
class IndexObject():
    # header: index_header
    # entries: List[index_entry]
    data_type: str = 'DIRC'
    version: int = 2
    entry_num: int = 0
    entries: Dict[str, IndexEntry] = None

    def __init__(self, data_type: str = 'DIRC', version: int = 2, entries=None) -> None:
        self.data_type = data_type
        self.version = version
        self.entries = entries if entries else {}
        self.entry_num = len(entries) if self.entries else 0
    #     self.header = index_header(len(files))
    #     self.entries = [index_entry(file) for file in files]

    def update(self, file: Path):
        self.entries[file] = IndexEntry().from_file(file)
        self.entry_num = len(self.entries)

    def binary_data(self) -> bytes:
        data = struct.pack('>4sII', self.data_type.encode(), self.version, len(self.entries)) + \
            b''.join([entry.binary_data() for entry in self.entries.values()])
        return data + bytes.fromhex(sha1(data).hexdigest())


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


def update_ref(ref: str, value: str):
    print('@ update_ref', value)
    with open(git_dir().joinpath(ref), 'w') as f:
        f.write(f'ref: {value}')

def glob(patterns:List[str]) -> Generator:
    for pattern in patterns:
        for path in Path().glob(pattern):
            yield path

def add(patterns: List[str]) -> None:
    # obj = IndexObject()
    obj, hash = parse_index()
    for path in glob(patterns):
        # path = Path(file)
        if not path.exists():
            print(f'@File not found ({path})')
            continue
        with path.open(mode='r') as f:
            data = f.read()
        write_object(data)
        obj.update(path)
    update_index(obj)

def reset_add(patterns: List[str]) -> None:
    update_index(IndexObject())

def update_index(obj: IndexObject) -> None:
    print(obj)
    print('@ update_index')
    with git_dir().joinpath('index').open(mode='wb') as f:
        f.write(obj.binary_data())


def parse_index() -> Tuple[IndexObject, str]:
    with git_dir().joinpath('index').open(mode='rb') as f:

        def read(format: str) -> Union[Tuple, Any]:
            d = struct.unpack(format, f.read(struct.calcsize(format)))
            return d if len(d) else d[0]

        data_type, version, entry_num = read('>4sII')
        entries = {}
        for _ in range(entry_num):
            format = '>IIIIIIIIII20sH'
            entry_size = struct.calcsize(format)
            ct, ctns, mt, mtns, dev, ino, mode, uid, gid, size, hash, flag = read(format)
            asmflg = (flag >> 15) & 0x01
            extflg = (flag >> 14) & 0x01
            if extflg:
                extoptflg = read('>H')
                rsvflg = (extoptflg >> 15) & 0x01
                skpflg = (extoptflg >> 14) & 0x01
                addflg = (extoptflg >> 13) & 0x01
            else:
                rsvflg = skpflg = addflg = 0
            fname = ''
            if (fn_len := int(flag & 0xFFF)) < 0xFFF:
                fname = f.read(fn_len)
                entry_size += fn_len
            else:
                while (char := f.read(1)) != b'\x00':
                    fname += char
                    entry_size += 1

            f.read((8 - (entry_size % 8)) or 8)
            entries[fname] = IndexEntry(ct, ctns, mt, mtns, dev, ino, mode, uid, gid,
                                         size, hash.hex(), asmflg, extflg, rsvflg, skpflg, addflg,
                                         fname.decode("utf-8", "replace"))

        obj = IndexObject(data_type.decode(), version, entries)
        index_hash = read('20s')
        print('@', obj)
        print('@', index_hash[0].hex())
        return obj, index_hash[0].hex()


if __name__ == "__main__":
    import os
    os.chdir('workspace')

    parse_index()
    # print(format((0b0|1)<<1,'016b'))
    # a = (0b1000000000000101 >> 15) & 0x01
    # b = (0b0000000000000101 >> 14) & 0x01

    # print(format(a, '016b'))
    # print(a)
    # print(format(b, '016b'))
    # print(b)
