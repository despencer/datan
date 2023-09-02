import yaml
import os
import importlib
import streams

class FieldReader:
    def __init__(self):
        self.preread = []
        self.postread = []

    def __repr__(self):
        return self.name

class PlainRecord:
    def __init__(self, meta):
        self._meta = meta

    def __repr__(self):
        return self._meta.prettyprint(self)

    def getfields(self):
        return self._meta.getfields(self)

class PlainRecordReader:
    def __init__(self):
        self.fields = []

    def read(self, datafile):
        data = PlainRecord(self)
        for f in self.fields:
            for pr in f.preread:
                pr(data)
            fvalue = f.reader.read(datafile)
            for pr in f.postread:
                pr(data, fvalue)
            setattr(data, f.name, fvalue)
        return data

    def prettyprint(self, data):
        return self.name + ":\n"+"\n".join( map( lambda x: "    {0}: {1}".format(x.name, self.printfield(x, getattr(data, x.name)) ), self.fields) )

    def printfield(self, field, data):
        ff = field.formatter(data)
        if '\n' in ff:
            return '\n'.join(  map(lambda x: '    '+x, ff.split('\n'))  )[4:]
        return ff

    def getfields(self, data):
        ret = {}
        for f in self.fields:
            if hasattr(data, f.name):
                ret[f.name] = getattr(data, f.name)
        return ret

    def getsize(self):
        size = 0
        for f in self.fields:
            size += f.reader.getsize()
        return size

    @classmethod
    def loadreader(cls, name, yrec, loader):
        prec = PlainRecordReader()
        prec.name = loader.structure.namespace + name
        for yfield in yrec:
            field = FieldReader()
            field.name = yfield['field']
            if 'function' in yfield:
                field.reader = FunctionReader(yfield['function'])
                field.preread.append( lambda context: field.reader.setcontext(context) )
                field.formatter = str
            else:
                field.reader = loader.getreader(yfield['type'], LoaderXRef(field, 'reader'))
                field.formatter = loader.formatter.get(yfield['type'])
                if 'params' in yfield:
                    cls.loadparam(loader, field, yfield['params'])
                if hasattr(field.reader, 'loadmeta'):
                    field.reader.loadmeta(loader, yfield)
            prec.fields.append(field)
        return prec

    @classmethod
    def loadparam(cls, loader, field, yparams):
        grx = ReaderXRef()
        lrx = LocalRef()
        for yparam in yparams:
            if 'global' in yparam and yparam['global']:
                grx.addparam(yparam['name'], yparam['reference'])
            else:
                lrx.addparam(yparam['name'], yparam['reference'])
        if len(lrx) > 0:
            if len(grx) > 0:
                field.postread.append( lambda context, instance: lrx.resolve(context, instance, False) )
            else:
                field.postread.append( lambda context, instance: lrx.resolve(context, instance, True) )
        if len(grx) > 0:
            loader.addreadxref(grx)
            field.postread.append( lambda context, instance: rx.addinstance(instance) )

class FreeReader:
    def __init__(self, count):
        self.count = count

    def read(self, stream):
        stream.seek(self.count, os.SEEK_CUR)
        return None

    def getsize(self):
        return self.count

class BytesReader:
    def __init__(self, count):
        self.count = count

    def read(self, stream):
        return stream.read(self.count)

    def getsize(self):
        return self.count

class ArrayReader:
    def __init__(self, count):
        self.count = count

    def read(self, stream):
        ret = []
        for i in range(self.count):
            ret.append( self.simple.read(stream) )
        return ret

class Structure:
    def __init__(self):
        self.records = {}
        self.start = None
        self.module = None
        self.xrefs = []

    def read(self, datafile):
        root = self.start.read(datafile)
        rf = root.getfields()
        for rx in self.xrefs:
            rx.resolve(rf)
        return root

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

class LoaderXRef:
    def __init__(self, field, reader):
        self.field = field
        self.reader = reader

    def resolve(self, records):
        if self.typename not in records:
            raise Exception('Type ' + self.typename + ' not found')
        setattr(self.field, self.reader, records[self.typename])

class LocalRef:
    def __init__(self):
        self.params = {}

    def addparam(self, name, xref):
        self.params[name] = xref

    def resolve(self, instance, field, reset):
        context = instance.getfields()
        for name, xref in self.params.items():
            value = eval(xref, context)
            setattr(field, name, value)
        if reset:
            field.reset()

    def __len__(self):
        return len(self.params)

class ReaderXRef:
    def __init__(self):
        self.params = {}
        self.instances = []

    def addparam(self, name, xref):
        self.params[name] = xref

    def addinstance(self, instance):
        self.instances.append(instance)

    def resolve(self, root):
        for name, xref in self.params.items():
            value = eval(xref, root)
            for instance in self.instances:
                setattr(instance, name, value)
        for instance in self.instances:
            instance.reset()
        self.instances.clear()

    def __len__(self):
        return len(self.params)


class IntReader:
    def __init__(self, size):
        self.size = size

    def read(self, datafile):
        return int.from_bytes(datafile.read(self.size), 'little')

    def getsize(self):
        return self.size

class FunctionReader:
    def __init__(self, func):
        self.func = func

    def setcontext(self, instance):
        self.context = instance.getfields()

    def read(self, datafile):
        return eval(self.func, self.context)

    def getsize(self):
        return 0


class Loader:
    def __init__(self, filename, formatter):
        self.filename = filename
        self.formatter = formatter
        self.xrefs = []
        self.simple = { 'uint8': IntReader(1), 'uint16': IntReader(2),
            'uint32': IntReader(4), 'uint64': IntReader(8) }

    def load(self):
        with open(self.filename) as strfile:
            ystr = yaml.load(strfile, Loader=yaml.Loader)
            self.structure = Structure()
            self.structure.namespace = ystr['namespace']+'.' if 'namespace' in ystr else ''
            self.loadtypes()
            self.structure.module = self.loadpyfile(self.filename)
            if self.structure.module != None:
                self.structure.module.loadtypes(self)
            for yrname, yrec in ystr['types'].items():
                reader = PlainRecordReader.loadreader(yrname, yrec, self)
                self.structure.records[reader.name] = reader
                if self.structure.start == None:
                    self.structure.start = reader
        for xref in self.xrefs:
            xref.resolve(self.structure.records)
        return self.structure

    def loadtypes(self):
        streams.loadtypes(self)

    def getreader(self, stype, xref):
        if stype.find('[') >=0 :
            return self.getarrayreader(stype)
        if stype in self.simple:
            return self.simple[stype]
        stype = self.structure.namespace + stype
        if stype in self.structure.records:
            return self.structure.records[stype](self)
        xref.typename = stype
        self.xrefs.append(xref)
        return None

    def getarrayreader(self, stype):
        simple = stype[:stype.find('[')]
        count = int( stype[stype.find('[')+1:stype.find(']')] )
        if simple == 'free':
            return FreeReader(count)
        elif simple == 'bytes':
            return BytesReader(count)
        array = ArrayReader(count)
        array.simple = self.getreader(simple, LoaderXRef(array, 'simple'))
        return array

    def addtypes(self, readers):
        for typename, loader in readers.items():
            self.structure.records[self.structure.namespace + typename] = loader

    def addreadxref(self, rx):
        self.structure.xrefs.append(rx)

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
