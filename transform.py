import parser
import records

class Transformer:
    def __init__(self):
        trans.operands = None

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
                action(obj.getfields, data=tobj, operands=op)

class TrasformerSetter:
    def __init__(self, field):
        self.field = field

    def perform(self, tobj, op):
        self.field.read(op, tobj)

class TransformLoader:
    @classmethod
    def loadactions(cls, ymeta, module):
        ''' parsing "do" branch in yaml '''
        trans = TransformerActions()
        if isinstance(ymeta['do'], list):
            for ydo in ymeta['do']:
                if isinstance(ydo, str):
                    trans.actions.append(ydo)
                else:
                    trans.actions.append( cls.load(ydo, module).transform )
        else:
            trans.actions.append(ymeta['do'])

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
        elif 'parse' in ymeta:
            return parser.loadparser(ymeta, module)
        raise Exception('Unknown transformer method at' + ymeta)


def loadtransformer(ymeta, module):
    return TransformLoader.load(ymeta, module)
