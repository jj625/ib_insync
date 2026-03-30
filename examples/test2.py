# example to test function attribute

class MyClass():
    # add slots to avoid __dict__
    # __slots__ = ['counter']
    def __init__(self):
        self.counter = 0
        # self._my_state: int = None
    
    def foo(self, x):
        # if not hasattr(self, "_my_state"):
        #     setattr(self, "_my_state", {})
        #     assert self._my_state == {}
        
        func = type(self).foo
        if not hasattr(func, "_my_state"):
            # the next two lines are equivalent
            setattr(func, "_my_state", {})
            # func._my_state = {} # directly set attribute
            
            assert func._my_state == {}
            func._my_state.setdefault('y', 100)
        func._my_state['y'] -= x
        print(f"Counter: {self.counter}, x: {x}, my_state: {func._my_state}")
        self.counter += 1
        # attempt to set an attribute on self
        self._my_state = x * 2

obj = MyClass()
# list attributes of MyClass instance
print(dir(obj))

# list attributes of foo
print(dir(type(obj).foo))
obj.foo(10)
print(dir(type(obj).foo))
obj.foo(20)
obj.foo(30)