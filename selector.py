
class Selector:
    def __init__(self):
        self.selector = None
        self.mapping = {}

    def select(self, datafile, pos, context):
        key = eval(self.selector, vars(context))
        if key not in self.mapping:
            raise Exception(f'Selector {key:X} not found in the mapping at {pos}')
        datafile.seek(pos)
        return self.mapping[key].read(datafile)

    @classmethod
    def load(cls, ymeta, module):
        selector = cls()
        selector.selector = ymeta['selector']
        selector.mapping = module.loadtypemapper(ymeta['mapping'])
        return selector

def loadselector(ymeta, module):
    return Selector.load(ymeta, module)
