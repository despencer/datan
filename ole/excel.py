import os
import streams

class Biff8Record:
    def __init__(self, rectype, size):
        self.rectype = rectype
        self.size = size
        self.record = None

    def __repr__(self):
        if self.record == None:
            return "BIFF8 {:04X} of size {:04X}".format(self.rectype, self.size)
        return str(self.record)

class Biff8RecordReader:
    def __init__(self):
        self.bytereader = streams.ByteStreamReader()

    def read(self, datafile):
        header = datafile.read(4)
        record = Biff8Record(int.from_bytes(header[0:2], 'little'), int.from_bytes(header[2:4], 'little') )
        record.raw = datafile.read(record.size)
        if record.rectype in self.mapping:
            record.record = self.mapping[record.rectype].read(self.bytereader.from_bytes(record.raw))
        return record

    def readsize(self, datafile):
        header = datafile.read(4)
        size = int.from_bytes(header[2:4], 'little')
        datafile.seek(size, os.SEEK_CUR)
        return size

    @classmethod
    def getreader(cls, module):
        reader = cls()
        reader.mapping = module.gettypemapper('biff8')
        return reader

def msunicode(rawdata):
    method = 'ascii' if (rawdata[2] & 0x80) == 0 else 'utf-16'
    size = int.from_bytes(rawdata[0:2], 'little')
    return rawdata[3:3+size].decode(method)

def loadmeta(module):
    module.addtypes( { 'biff8': Biff8RecordReader.getreader } )
    module.addfunctions( {'msunicode': msunicode } )
