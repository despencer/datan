#!/usr/bin/python3
import argparse
import records
import formatter

def dump(args):
    print('Filename:', args.filename)
    print('Structures:', args.structures)
    strdef = records.loadmeta(args.structures, formatter.getdefault() )
    with open(args.filename, 'rb') as datafile:
        obj = strdef.read(datafile)
        if len(args.object) > 0:
            print(eval(args.object, obj.getfields()))
        else:
            print(obj)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File data dump')
    parser.add_argument('filename', help='file to dump')
    parser.add_argument('structures', help='structures YAML file')
    parser.add_argument('--object', default='', required=False)
    args = parser.parse_args()
    dump(args)
