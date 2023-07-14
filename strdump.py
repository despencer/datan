#!/usr/bin/python3
import argparse
import yaml

def dump(args):
    print('Filename:', args.filename)
    print('Structures:', args.structures)
    with open(args.structures) as strfile:
        print(yaml.load(strfile, Loader=yaml.Loader))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='File data dump')
    parser.add_argument('filename', help='file to dump')
    parser.add_argument('structures', help='structures YAML file')
    args = parser.parse_args()
    dump(args)
