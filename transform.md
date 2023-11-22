# Transformation rules

* Case 1: a single transformation *
```yaml
transform: object
with: args
do: funcname
```
Here the function *funcname* of every object of *object* (it can be iterable) is called for every object of *args*:
* object1.funcname(arg1)
* object1.funcname(arg2)
* ...
* object1.funcname(argM)
* object2.funcname(arg1)
* object2.funcname(arg2)
* ...
* objectN.funcname(argM)

This transformation is performed by *Transformer* class.

* Case 2: a serial transformation *
```yaml
transform: object
with: args
do:
   - funcname1
   - funcname2
   - funcname3
```
Here the functions *funcnameXX* of every object of *object* (it can be iterable) are called sequential for every object of *args*:
* object1.funcname1(arg1)
* object1.funcname2(arg1)
* ...
* object1.funcnameK(arg1)
* object1.funcname1(arg2)
* ...
* object1.funcnameK(argM)
* object2.funcname1(arg1)
* object2.funcname2(arg2)
* ...
* objectN.funcnameK(argM)

This transformation is performed by *Transformer* class.