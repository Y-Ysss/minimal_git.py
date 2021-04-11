import difflib


def read_bytes(file, chunksize=8192):
    with open(file, mode='rb') as f:
        while (chunk := f.read(chunksize)):
            for b in chunk:
                yield b

def dump(file):
    address = 0
    ascii = ''
    data = f'File    : {file}\n'
    data += 'Offset  : 00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F  DecodeText(ASCII)\n'
    data += '--------- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --  ----------------\n'
    for byte in read_bytes(file):
        ascii += chr(byte) if 33 <= byte <= 126 else '.' # 33(!) - 126(~)
        if address % 16 == 0:
            data += f'{address:08X}: '

        data += f'{byte:02x} '

        if address % 16 == 15:
            data += f' {ascii}\n'
            ascii = ''
        address += 1
    return data + '\n'


if __name__ == '__main__':
    a = dump('workspace/.git/index')
    b = dump('workspace/.testgit/index')
    print(a)
    print(b)
    print('--- Diff ---')
    line = ''
    for line in difflib.unified_diff(a.splitlines()[1:], b.splitlines()[1:], n=0, lineterm=''):
        print(line)
    if not line:
        print('  No differences!')