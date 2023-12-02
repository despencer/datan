import os
import struct
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

    def getsheet(self, name):
        return self.sheets[name]

class Cell:
    def __init__(self, value):
        self.value = value
        self.formula = None

class Row:
    def __init__(self):
        self.cells = []

class Sheet:
    def __init__(self, name):
        self.name = name
        self.rows = []

    def getcell(self, row, column):
        if not (0 <= row and row < len(self.rows)):
            return None
        if not (0 <= column and column < len(self.rows[row].cells)):
            return None
        return self.rows[row].cells[column]

class SheetLoader:
    def __init__(self, wbloader, sheet, offset):
        self.wbloader = wbloader
        self.sheet = sheet
        self.wbrawstream = wbloader.rawstream
        self.bookoffset = offset

    def addcell(self, biff8):
        while len(self.sheet.rows) <= biff8.record.row:
            self.sheet.rows.append(Row())
        row = self.sheet.rows[biff8.record.row]
        while len(row.cells) <= biff8.record.column:
            row.cells.append( Cell(None) )
        return row.cells[biff8.record.column]

    def addrkcell(self, biff8):
        self.addcell(biff8).value = self.readrknum(biff8.record.rknum)

    def addmulrkcell(self, biff8):
        lastcol = int.from_bytes( bytes(biff8.record.rawvalue[-2:]) , 'little')
        ipos = 2
        if (lastcol-biff8.record.column+1)*6 != len(biff8.record.rawvalue)-2:
            raise Exception(f'Bad mulrk record')
        while biff8.record.column <= lastcol:
            self.addcell(biff8).value = self.readrknum( int.from_bytes( bytes(biff8.record.rawvalue[ipos:ipos+4]) , 'little') )
            biff8.record.column += 1
            ipos += 6

    def addformulacell(self, biff8):
        cell = self.addcell(biff8)
        if biff8.record.value[6] == 0xFF and biff8.record.value[7] == 0xFF:
            if biff8.record.value[0] == 0 or biff8.record.value[0] == 2:
                value = None
                self.lastformula = cell
            else:
                raise Exception(f'Unknown formula value type {biff8.record.value[0]} at row {biff8.record.row} column {biff8.record.column}')
        else:
            value = getdouble(biff8.record.value)
        cell.value = value
#        print(biff8.record.rawformulastream)
#        if (biff8.record.status & 0x08) == 0x08:
#            raise Exception("Can't yet parse shared formulas")
        cell.formula = biff8.record.formulastream.readall()

    def addformulastring(self, biff8):
        self.lastformula.value = biff8.record.value
        self.lastformula = None

    def addsstcell(self, biff8):
        self.addcell(biff8).value = self.wbloader.stringtable[biff8.record.isst]

    def readrknum(self, rknum):
        if (rknum & 0x02) == 0x02:
            value = int(rknum >> 2)
        else:
            value = bytes([0,0,0,0])+(rknum & 0xFFFFFFF7).to_bytes(4, 'little')
            [value] = struct.unpack('d', value)
        if (rknum & 0x01) == 0x01:
            value = value / 100
        return value

class WorkbookLoader:
    def __init__(self, rawstream):
        self.rawstream = rawstream
        self.target = Workbook()
        self.sheets = []
        self.stringtable = []

    def collector(self, first):
        return parser.collector(first)

    def setstringtable(self, recs):
        irecord = 0
        data = recs[0].record.rawstrings
        while True:
            charnum = int.from_bytes(data.read(2), 'little')
            strmod = int.from_bytes(data.read(1), 'little')
            if (strmod & 0x0F6) != 0:
                ipos = data.getpos()-3
                raise Exception(f'Not yet implemented modifier {strmod:X} at {irecord:X}/{ipos:X}')
            if (strmod & 0x1) == 1:
                method = 'utf-16'
                size = 2*charnum
            else:
                method = 'ascii'
                size = charnum
            if (strmod & 0x08) == 0x08:
                formatsize = int.from_bytes(data.read(2), 'little') * 4
            else:
                formatsize = 0
            string = ''
            if data.getpos()+size > len(data):
                size = len(data)-data.getpos()
                string += data.read(size).decode(method)
                charnum -= size//2 if method == 'utf-16' else size
                irecord += 1
                data = recs[irecord].record.rawdata
                data.seek(0)
                strmod = int.from_bytes(data.read(1), 'little')
                if (strmod & 0x1) == 1:
                    method = 'utf-16'
                    size = 2*charnum
                else:
                    method = 'ascii'
                    size = charnum
            string += data.read(size).decode(method)
            self.stringtable.append(string)
            if data.getpos()+formatsize > len(data):
                formatsize -= len(data)-data.getpos()
                data.seek(len(data)-data.getpos(), os.SEEK_CUR)
            else:
                data.seek(formatsize, os.SEEK_CUR)
                formatsize = 0
            if data.getpos() >= len(data):
                irecord += 1
                if irecord >= len(recs):
                    break
                data = recs[irecord].record.rawdata
                data.seek(0)
            data.seek(formatsize, os.SEEK_CUR)

    def addsheet(self, biff8):
        self.sheets.append( SheetLoader( self, self.target.addsheet(biff8.record.name), biff8.record.startpos ))

class Biff8Record:
    def __init__(self, rectype, size, reader):
        self.rectype = rectype
        self.size = size
        self.reader = reader
        self.raw = []

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
            return Biff8Record(0, 0, self)
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
            ret += '{0:08X} {1:04X} size {2:08X}'.format(pos, data.rectype, data.size)
            if data.rectype in self.lookup:
                ret += ' ' + self.lookup[data.rectype]
            ret += '\n'
        return ret

class Biff8String:
    def __init__(self, type):
        self.type = type

    def read(self, datafile):
        if self.type == 'short':
            return self.readshort(datafile)
        return ''

    def readshort(self, datafile):
        [count] = datafile.read(1)
        [method] = datafile.read(1)
        if (method & 0x1) == 0x1:
            return bytes(datafile.read(2*count)).decode('utf-16')
        else:
            return bytes(datafile.read(count)).decode('ascii')

    @classmethod
    def getshortreader(cls, module):
        reader = cls('short')
        return reader

def bookloader(rawstream):
    return WorkbookLoader(rawstream)

def getdouble(rawvalue):
    [value] = struct.unpack('d', bytes(rawvalue))
    return value

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
    module.addtypes( { 'biff8': Biff8RecordReader.getreader, 'shortmsunicode': Biff8String.getshortreader } )
    module.addfunctions( {'longmsunicode': longmsunicode, 'shortmsunicode': shortmsunicode, 'bookloader': bookloader,
                           'getdouble': getdouble } )

def loadformatters(fmt, yoptions):
    fmt.addformatters( {'wbstream': Biff8StreamFormatter(yoptions) } )
