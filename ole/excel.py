import os

class Biff8Record:
    def __init__(self, rectype, size):
        self.rectype = rectype
        self.size = size

    def __repr__(self):
        return "BIFF8 {:04X} of size {:04X}".format(self.rectype, self.size)

class Biff8RecordReader:
    def read(self, datafile):
        header = datafile.read(4)
        record = Biff8Record(int.from_bytes(header[0:2], 'little'), int.from_bytes(header[2:4], 'little') )
        record.raw = datafile.read(record.size)
        return record

    def readsize(self, datafile):
        header = datafile.read(4)
        size = int.from_bytes(header[2:4], 'little')
        datafile.seek(size, os.SEEK_CUR)
        return size

    @classmethod
    def getreader(cls, loader):
        reader = cls()
        return reader


def loadtypes(loader):
    loader.addtypes( { 'biff8': Biff8RecordReader.getreader } )
