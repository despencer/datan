# datan
Data analysis

### Cross-reference resolving
The cross-references of objects created at run-time are defined by *params* node in a field description. The object responsible for
setting the parameter is an owner of a parametrized object. For example, the reader of a *header* object with a *stream* field registers
all parameters that are to be set in the *stream* field in a register (maintained by the loader). After the loader has read all objects
the procedure of resolving references starts. A *reset* function is called for every *instance* of parametrized objects. This function
is called only once disregard of how many parameters an object has.
