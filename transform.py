import parser
import records

class Transformer:
    def __init__(self):
        self.operands = None

    def transform(self, environ, data=None, operands=None):
        obj = eval(self.context, environ)
        if self.operands != None:
            for op in eval(self.operands, environ):
                self.action(obj, op)
        else:
            self.action(obj, None)

class TransformerActions:
    def __init__(self):
        self.actions = []

    def perform(self, tobj, op):
        for action in self.actions:
            if isinstance(action, str):
                func = getattr(tobj, action)
                func(op)
            else:
                action(tobj.getfields, data=tobj, operands=op)

class TransformerSetter:
    def __init__(self, field):
        self.field = field

    def perform(self, tobj, op):
        self.field.read(op, tobj)

class TransformLoader:
    @classmethod
    def loadactions(cls, ymeta, module):
        ''' parsing "do" branch in yaml '''
        trans = TransformerActions()
        if isinstance(ymeta, list):
            for ydo in ymeta:
                if isinstance(ydo, str):
                    trans.actions.append(ydo)
                else:
                    trans.actions.append( cls.load(ydo, module).transform )
        else:
            trans.actions.append(ymeta)
        return trans

    @classmethod
    def load (cls, ymeta, module):
        if 'do' in ymeta:
            trans = Transformer()
            trans.context = ymeta['transform']
            if 'with' in ymeta:
                trans.operands = ymeta['with']
            trans.action = cls.loadactions(ymeta['do'], module).perform
            return trans
        elif 'set' in ymeta:
            trans = Transformer()
            trans.action = TransformerSetter( records.loadfieldreader(ymeta, module) )
            return trans
        elif 'parse' in ymeta:
            return parser.loadparser(ymeta, module)
        raise Exception('Unknown transformer method at' + str(ymeta))

def loadtransformer(ymeta, module):
    return TransformLoader.load(ymeta, module)
