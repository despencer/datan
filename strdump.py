#!/usr/bin/python3
import argparse
import records
import formatter

def makeformat(fmt, args, strdef):
    if len(args.formatter) > 0:
        fmt.load(args.formatter, strdef)
    if len(args.formatsize) > 0:
        fmt.parameters['stream'].size = eval(args.formatsize)
    if len(args.formatpos) > 0:
        fmt.parameters['stream'].pos = eval(args.formatpos)

def dump(args):
    print('Filename:', args.filename)
    print('Structures:', args.structures)
    fmt = formatter.getdefault()
    strdef = records.loadmeta(args.structures, fmt)
    makeformat(fmt, args, strdef)
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
    parser.add_argument('--formatpos', default='', required=False)
    parser.add_argument('--formatsize', default='', required=False)
    parser.add_argument('--formatter', default='', required=False)
    args = parser.parse_args()
    dump(args)
