import yaml
import os
import sys
import importlib
import formatter
import streams
import transform
import parser
import selector

class FieldReader:
    def __init__(self):
        self.preread = []
        self.postread = []

    def __repr__(self):
        return self.name

    def read(self, datafile, data):
        for pr in self.preread:
            pr(data)
        fvalue = self.reader.read(datafile)
        for pr in self.postread:
            pr(data, fvalue)
        setattr(data, self.name, fvalue)


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
        self.transforms = []
        self.selector = None

    def read(self, datafile):
        pos = datafile.getpos()
        data = PlainRecord(self)
        for f in self.fields:
            f.read(datafile, data)
        for t in self.transforms:
            t.transform(self.getfields(data))
        if self.selector != None:
            data = self.selector.select(datafile, pos, data)
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

    def getreader(self, loader):
        return self

    @classmethod
    def loadreader(cls, name, yrec, module):
        prec = PlainRecordReader()
        prec.name = module.namespace + name
        for yfield in yrec:
            if 'field' in yfield or 'set' in yfield:
                prec.fields.append( cls.loadfield(yfield, module)  )
            elif 'transform' in yfield:
                prec.transforms.append( transform.loadtransformer(yfield, module) )
            elif 'parse' in yfield:
                prec.transforms.append( parser.loadparser(yfield, module) )
            elif 'selection' in yfield:
                prec.selector = selector.loadselector(yfield['selection'], module)
        return prec

    @classmethod
    def loadfield(cls, yfield, module):
        field = FieldReader()
        field.name = yfield['field'] if 'field' in yfield else yfield['set']
        if 'function' in yfield:
            field.reader = FunctionReader(yfield['function'], module.getfunctions())
            field.preread.append( field.reader.setcontext )
            field.formatter = str
        else:
            field.reader = module.getreader(yfield['type'], LoaderXRef(field, 'reader', meta=yfield))
            field.formatter = module.loader.formatter.get(yfield['type'])
            if 'count' in yfield:
                reader = ArrayReader(0)
                field.preread.append( lambda context: reader.evalcount(yfield['count'], context) )
                reader.simple = field.reader
                basefmt = field.formatter
                field.formatter = lambda x: formatter.arrayformatter(x, basefmt)
                field.reader = reader
            else:
                if 'params' in yfield:
                    cls.loadparam(module.loader, field, yfield['params'])
                if hasattr(field.reader, 'loadmeta'):
                    field.reader.loadmeta(module, yfield)
        return field

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

    def evalcount(self, ecount, context):
        self.count = eval(ecount, vars(context))

class Structure:
    def __init__(self):
        self.records = {}
        self.functions = {}
        self.start = None
        self.pymodules = {}
        self.xrefs = []
        self.target = None

    def read(self, datafile):
        if not hasattr(datafile, 'getpos'):
            setattr(datafile, 'getpos', lambda: datafile.tell())
        root = self.start.read(datafile)
        rf = root.getfields()
        for rx in self.xrefs:
            rx.resolve(rf)
        return root

    def gettarget(self, obj):
        if self.target == None:
            return obj
        return eval(self.target, obj.getfields())

    def __repr__(self):
        return '\n'.join( map(str, self.records.values()) )

class LoaderXRef:
    def __init__(self, field, reader, meta=None):
        self.field = field
        self.reader = reader
        self.meta = meta

    def resolve(self):
        resolved = None
        records = self.module.loader.structure.records
        if self.typename in records:
            resolved = records[self.typename]
        else:
            if '.' in self.typename:
                typename = self.typename.split('.')[-1]
                if typename in records:
                    resolved = records[typename]
        if resolved is None:
            raise Exception('Type ' + self.typename + ' not found')
        reader = resolved.getreader()
        if self.meta is not None and hasattr(reader, 'loadmeta'):
            reader.loadmeta(self.module, self.meta)
        setattr(self.field, self.reader, reader )

class LocalRef:
    def __init__(self):
        self.params = {}

    def addparam(self, name, xref):
        self.params[name] = xref

    def resolve(self, instance, field, reset):
        if hasattr(instance, 'getfields'):
            context = instance.getfields()
        else:
            context = vars(instance)
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

class TypeMapperItem:
    pass

class TypeMapper:
    def __init__(self):
        self.mapper = {}

    def add(self, key, item):
        self.mapper[key] = item

    def __getitem__(self, key):
        return self.mapper[key].reader

    def __contains__(self, key):
        return key in self.mapper

class IntReader:
    def __init__(self, size):
        self.size = size

    def read(self, datafile):
        return int.from_bytes(datafile.read(self.size), 'little')

    def getsize(self):
        return self.size

class FunctionReader:
    def __init__(self, func, statctx):
        self.func = func
        self.statctx = statctx

    def setcontext(self, instance):
        self.context = instance.getfields()

    def read(self, datafile):
        return eval(self.func, self.context, self.statctx)

    def getsize(self):
        return 0

class FillReader:
    def __init__(self, module):
        self.bytemeta = streams.ByteStreamReader()
        self.bytemeta.formatter = module.getformatter('stream')

    def read(self, datafile):
        return self.bytemeta.from_bytes( datafile.read(len(datafile) - datafile.getpos()) )

    @classmethod
    def getreader(cls, module):
        return cls(module)

class TypeLoader:
    def __init__(self, readermaker, module):
        self.readermaker = readermaker
        self.module = module

    def getreader(self):
        return self.readermaker(self.module)

class LoaderModule:
    def __init__(self, loader, ymeta):
        self.loader = loader
        self.ymeta = ymeta
        self.namespace = self.ymeta['namespace']+'.' if 'namespace' in self.ymeta else ''

    def addtypes(self, readers):
        for typename, reader in readers.items():
            self.loader.structure.records[self.namespace + typename] = TypeLoader(reader, self)

    def addfunctions(self, funcs):
        for funcname, func in funcs.items():
            self.loader.structure.functions[(self.namespace + funcname).replace('.','_')] = func

    def getreader(self, stype, xref):
        if stype.find('[') >=0 :
            return self.getarrayreader(stype)
        if stype in self.loader.simple:
            return self.loader.simple[stype]
        fqtype = self.namespace + stype
        if fqtype in self.loader.structure.records:
            return self.loader.structure.records[fqtype].getreader()
        xref.typename = fqtype
        xref.module = self
        self.loader.xrefs.append(xref)
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

    def loadtypemapper(self, ymeta):
        mapper = TypeMapper()
        for ykey, yreader in ymeta.items():
            item = TypeMapperItem()
            item.reader = self.getreader(yreader, LoaderXRef(item, 'reader'))
            mapper.add(ykey, item)
        return mapper

    def gettypemapper(self, name):
        return self.loadtypemapper(self.ymeta['mappings'][name])

    def getformatter(self, name):
        return self.loader.formatter.get(name)

    def getfunctions(self):
        return self.loader.structure.functions

class Loader:
    def __init__(self, fmt):
        self.formatter = fmt
        self.xrefs = []
        self.simple = { 'uint8': IntReader(1), 'uint16': IntReader(2),
            'uint32': IntReader(4), 'uint64': IntReader(8) }
        self.structure = Structure()
        self.modules = [ LoaderModule(self, {}) ]
        self.loadtypes( self.modules[-1] )

    def load(self, filename):
        self.loadfile(filename, True)
        for xref in self.xrefs:
            xref.resolve()
        return self.structure

    def loadfile(self, filename, toplevel):
        with open(filename) as strfile:
            ystr = yaml.load(strfile, Loader=yaml.Loader)
            if 'imports' in ystr:
                self.loadimports(ystr, filename)
            module = LoaderModule(self, ystr)
            self.modules.append(module)
            module.module = loadpyfile(self.structure, filename)
            if module.module != None:
                module.module.loadmeta(module)
            if 'records' in ystr:
                self.loadrecords(ystr, module, toplevel)
            if toplevel and 'target' in ystr:
                self.structure.target = ystr['target']

    def loadrecords(self, ystr, module, toplevel):
        for yrname, yrec in ystr['records'].items():
            reader = PlainRecordReader.loadreader(yrname, yrec, module)
            self.structure.records[reader.name] = TypeLoader(reader.getreader, module)
            if toplevel and self.structure.start == None:
                self.structure.start = reader

    def loadimports(self, ystr, filename):
        for yimport in ystr['imports']:
            importfile = yimport + '.struct'
            path = os.path.dirname(filename)
            if path != '':
                importfile = path + '/' + importfile
            print('import', importfile)
            self.loadfile(importfile, False)

    def loadtypes(self, module):
        module.addtypes( { 'filler': FillReader.getreader } )
        streams.loadmeta(module)

    def addreadxref(self, rx):
        self.structure.xrefs.append(rx)

def loadpyfile(structure, filename):
    pyfile = os.path.splitext(filename)[0] + '.py'
    if os.path.exists(pyfile):
        if pyfile in structure.pymodules:
            print(pyfile, 'already loaded')
        else:
            print(pyfile, 'loaded')
            sys.path.append(os.path.dirname(pyfile))
            structure.pymodules[pyfile] = importlib.import_module(os.path.basename(pyfile)[:-3])
        return structure.pymodules[pyfile]
    else:
        print(pyfile, 'is not exist, skipped')
        return None

def loadfieldreader(yfield, module):
    return PlainRecordReader.loadfield(yfield, module)

def loadmeta(filename, fmt):
    loader = Loader(fmt)
    return loader.load(filename)
