#!/usr/bin/python3
import argparse
import formatter

def dump(args):
    print('Filename:', args.filename)
    fmt = formatter.StreamFormatter()
    fmt.pos = eval(args.pos)
    fmt.size = args.size
    fmt.line = args.line
    with open(args.filename, 'rb') as datafile:
        print(fmt.format(datafile))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File data dump')
    parser.add_argument('filename', help='file to dump')
    parser.add_argument('--pos', default=0, required=False)
    parser.add_argument('--size', default=256, required=False, type=int)
    parser.add_argument('--line', default=16, required=False, type=int)
    args = parser.parse_args()
    dump(args)
