#!/usr/bin/python3
import argparse
import yaml
import records
import formatter

def dump(args):
    print('Filename:', args.filename)
    print('Structures:', args.structures)
    with open(args.structures) as strfile:
        strdef = records.loadmeta(yaml.load(strfile, Loader=yaml.Loader), formatter.getdefault())
        with open(args.filename, 'rb') as datafile:
            print(strdef.extract(datafile))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File data dump')
    parser.add_argument('filename', help='file to dump')
    parser.add_argument('structures', help='structures YAML file')
    args = parser.parse_args()
    dump(args)
