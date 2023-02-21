'''
Copyright (C) 2021 S[&]T, The Netherlands.

This tool reads a JobOrder <src>, replaces File_Name elements containing
wildcards with the actual file names, then writes the result to <dst>.

Patch: File names that cannot be resolved are replaced by 'dummy' to avoid a
crash (due to an invalid name) in procsim.

Usage:
resolve_wildcards.py <src> <dst>
'''

import glob
import sys
from xml.etree import ElementTree as et


def main():
    argv = sys.argv[1:]
    if len(argv) != 2:
        print('Usage: resolve_wildcards.py <src> <dst>')
        sys.exit(1)
    src = argv[0]
    dest = argv[1]
    print('Read {}'.format(src))
    tree = et.parse(src)
    for el in tree.findall('List_of_Tasks/Task/List_of_Inputs/Input/List_of_Selected_Inputs/Selected_Input/List_of_File_Names/File_Name'):
        if el.text is not None:
            files = glob.glob(el.text)
            if len(files) != 1:
                el.text = 'dummy'
            else:
                print('resolved {} to {}'.format(el.text, files[0]))
                el.text = files[0]
    print('Write {}'.format(dest))
    tree.write(dest)
    print()


if __name__ == '__main__':
    main()
