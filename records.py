import yaml
import os
import importlib

class FieldReader:
    def __init__(self):
        pass

    def __repr__(self):
        return self.name

class PlainRecord:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)

class PlainRecordReader:
    def __init__(self):
        self.fields = []

    def read(self, datafile):
        data = PlainRecord(self)
        for f in self.fields:
            setattr(data, f.name, f.reader(datafile))
        return data

    def prettyprint(self, data):
        return self.name + ":\n"+"\n".join( map( lambda x: "    {0}: {1}".format(x.name, x.formatter(getattr(data, x.name))), self.fields) )

    @classmethod
    def loadreader(cls, name, yrec, loader):
        prec = PlainRecordReader()
        prec.name = loader.structure.namespace + name
        for yfield in yrec:
            field = FieldReader()
            field.name = yfield['field']
            field.reader = loader.getreader(yfield['type'], field)
            field.formatter = loader.formatter.get(yfield['type'])
            prec.fields.append(field)
        return prec

    @classmethod
    def skipfree(cls, stream, count):
        stream.seek(count, os.SEEK_CUR)
        return None

    @classmethod
    def readarray(cls, stream, simple, count):
        ret = []
        for i in range(count):
            ret.append( simple(stream) )
        return ret

    def __repr__(self):
        return "Record {0}\n    ".format(self.name) + "\n    ".join( map(str, self.fields) )

class Structure:
    def __init__(self):
        self.records = {}
        self.start = None
        self.module = None

    def read(self, datafile):
        return self.start.read(datafile)

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

class LoaderXRef:
    def __init__(self, field, typename)
        self.field = field
        self.typename = typename

class Loader:
    def __init__(self, filename, formatter):
        self.filename = filename
        self.formatter = formatter
        self.xrefs = []
        self.simple = { 'uint8': lambda x: int.from_bytes(x.read(1)),
            'uint16': lambda x: int.from_bytes(x.read(2), 'little'),
            'uint32': lambda x: int.from_bytes(x.read(4), 'little'),
            'uint64': lambda x: int.from_bytes(x.read(8), 'little') }

    def load(self):
        with open(self.filename) as strfile:
            ystr = yaml.load(strfile, Loader=yaml.Loader)
            self.structure = Structure()
            self.structure.module = self.loadpyfile(self.filename)
            self.structure.namespace = ystr['namespace']+'.' if 'namespace' in ystr else ''
            for yrname, yrec in ystr['types'].items():
                self.structure.records[yrname] = PlainRecordReader.loadreader(yrname, yrec, self)
                if self.structure.start == None:
                    self.structure.start = self.structure.records[yrname]
        for xref in self.xrefs:
            field.reader = self.structure.records[xref.typename]
        return self.structure

    def getreader(self, stype, field):
        if stype.find('[') >=0 :
            return self.getarrayreader(stype)
        if stype in self.simple:
            return self.simple[stype]
        stype = self.structure.namespace + stype
        if stype in self.structure.records:
            return self.structure.records[stype].reader
        self.xrefs.append( LoaderXRef(field, typename) )
        return None

    def getarrayreader(self, stype, field):
        simple = stype[:stype.find('[')]
        count = int( stype[stype.find('[')+1:stype.find(']')] )
        if simple == 'free':
            return lambda x: PlainRecordReader.skipfree(x, count)
        return lambda x: PlainRecordReader.readarray(x, self.getreader(simple, field), count)

    def loadpyfile(self, filename):
        pyfile = os.path.splitext(self.filename)[0] + '.py'
        pymodule = os.path.splitext(self.filename)[0].replace('/','.')
        if os.path.exists(pyfile):
            print(pyfile, 'loaded')
            return importlib.import_module(pymodule)
        else:
            print(pyfile, 'is not exist, skipped')
            return None


def loadmeta(filename, formatter):
    loader = Loader(filename, formatter)
    return loader.load()
