import records
import formatter

def load(structure, filename):
    fmt = formatter.getminimal()
    strdef = records.loadmeta(structure, fmt)
    with open(filename, 'rb') as datafile:
        obj = strdef.read(datafile)
        return strdef.gettarget(obj)

