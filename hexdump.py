#!/usr/bin/python3
import argparse

def dump(args):
    print('Filename:', args.filename)
    with open(args.filename, 'rb') as datafile:
        datafile.seek(args.pos)
        data = datafile.read(args.size)
        for i in range( min(args.size,len(data)) ):
            if i%args.line == 0:
                print('{:08X}'.format(args.pos+i), end='')
            if i%4 == 0:
                print(' ', end='')
            print(' {:02X}'.format(data[i]), end='')
            if i%args.line == (args.line-1):
                print('')
        print('')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File data dump')
    parser.add_argument('filename', help='file to dump')
    parser.add_argument('--pos', default=0, required=False, type=lambda x: int(x, 0) )
    parser.add_argument('--size', default=256, required=False, type=int)
    parser.add_argument('--line', default=16, required=False, type=int)
    args = parser.parse_args()
    dump(args)
