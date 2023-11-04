
class Transformer:
    def __init__(self):
        pass

    def perform(self, environ):
        obj = eval(self.context, environ)
        func = getattr(obj, self.action)
        for op in eval(self.operands, environ):
            func(op)

def loadtransformer(ymeta, module):
    trans = Transformer()
    trans.context = ymeta['transform']
    trans.operands = ymeta['for']
    trans.action = ymeta['do']
    return trans