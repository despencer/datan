import os
import streams
import parser
import formatter
from functools import cached_property

class Workbook:
    def __init__(self):
        self.sheets = {}

    def addsheet(self, name):
        self.sheets[name] = Sheet(name)
        return self.sheets[name]

class Cell:
    def __init__(self, value):
        self.value = value

class Row:
    def __init__(self):
        self.cells = []

class Sheet:
    def __init__(self, name):
        self.name = name
        self.rows = []

class SheetLoader:
    def __init__(self, sheet, wbrawstream, offset):
        self.sheet = sheet
        self.wbrawstream = wbrawstream
        self.bookoffset = offset

    def addcell(self, rk):
        pass

class WorkbookLoader:
    def __init__(self, rawstream):
        self.rawstream = rawstream
        self.target = Workbook()
        self.sheets = []

    def collector(self, first):
        return parser.collector(first)

    def setstringtable(self, recs):
        bufs = [ recs[0].record.rawstrings ]
        for rd in recs[1:]:
            bufs.append(rd.record.rawdata)
        self.rawstringstream = streams.CombinedStream.fromstreams(bufs, self.rawstream._meta)

    def addsheet(self, biff8):
        self.sheets.append( SheetLoader( self.target.addsheet(biff8.record.name), self.rawstream, biff8.record.startpos ))

class Biff8Record:
    def __init__(self, rectype, size, reader):
        self.rectype = rectype
        self.size = size
        self.reader = reader

    def __repr__(self):
        if self.record == None:
            return "BIFF8 {:04X} of size {:04X}".format(self.rectype, self.size)
        return str(self.record)

    @cached_property
    def record(self):
        return self.reader.readrecord(self)

class Biff8RecordReader:
    def __init__(self):
        self.bytereader = streams.ByteStreamReader()

    def read(self, datafile):
        header = datafile.read(4)
        if len(header) < 4:
            return None
        record = Biff8Record(int.from_bytes(header[0:2], 'little'), int.from_bytes(header[2:4], 'little'), self)
        record.raw = datafile.read(record.size)
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

    def readrecord(self, record):
        if record.rectype in self.mapping:
            return self.mapping[record.rectype].read(self.bytereader.from_bytes(record.raw))
        return None

class Biff8StreamFormatter(formatter.StreamFormatter):
    def __init__(self, yoptions):
        super().__init__()
        self.lookup = yoptions['lookups']['wbtypes']

    def format(self, datafile, record=None):
        ret = ''
        for pos, data in datafile.selectrange(self.pos+self.size, self.pos):
            ret += '{0:08X} {1:08X}'.format(pos, data.rectype)
            if data.rectype in self.lookup:
                ret += ' ' + self.lookup[data.rectype]
            ret += '\n'
        return ret

def bookloader(rawstream):
    return WorkbookLoader(rawstream)

def longmsunicode(rawdata):
    method = 'ascii' if (rawdata[2] & 0x80) == 0 else 'utf-16'
    size = int.from_bytes(rawdata[0:2], 'little')
    return rawdata[3:3+size].decode(method)

def shortmsunicode(rawdata):
    method = 'ascii' if (rawdata[1] & 0x1) == 0 else 'utf-16'
    size = rawdata[0]
    if method == 'utf-16':
        size *= 2
    return rawdata[2:2+size].decode(method)

def loadmeta(module):
    module.addtypes( { 'biff8': Biff8RecordReader.getreader } )
    module.addfunctions( {'longmsunicode': longmsunicode, 'shortmsunicode': shortmsunicode, 'bookloader': bookloader } )

def loadformatters(fmt, yoptions):
    fmt.addformatters( {'wbstream': Biff8StreamFormatter(yoptions) } )
