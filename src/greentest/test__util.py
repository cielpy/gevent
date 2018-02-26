# -*- coding: utf-8 -*-
# Copyright 2018 gevent contributes
# See LICENSE for details.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import greentest

import gevent
from gevent import util
from gevent import local

class MyLocal(local.local):
    def __init__(self, foo):
        self.foo = foo

@greentest.skipOnPyPy("5.10.x is *very* slow formatting stacks")
class TestFormat(greentest.TestCase):

    def test_basic(self):
        lines = util.format_run_info()

        value = '\n'.join(lines)
        self.assertIn('Threads', value)
        self.assertIn('Greenlets', value)

        # because it's a raw greenlet, we have no data for it.
        self.assertNotIn("Spawned at", value)
        self.assertNotIn("Parent greenlet", value)
        self.assertNotIn("Spawn Tree Locals", value)

    def test_with_Greenlet(self):
        rl = local.local()
        rl.foo = 1
        def root():
            l = MyLocal(42)
            assert l
            gevent.getcurrent().spawn_tree_locals['a value'] = 42
            g = gevent.spawn(util.format_run_info)
            g.join()
            return g.value

        g = gevent.spawn(root)
        g.name = 'Printer'
        g.join()
        value = '\n'.join(g.value)

        self.assertIn("Spawned at", value)
        self.assertIn("Parent:", value)
        self.assertIn("Spawn Tree Locals", value)
        self.assertIn("Greenlet Locals:", value)
        self.assertIn('MyLocal', value)
        self.assertIn("Printer", value) # The name is printed

@greentest.skipOnPyPy("See TestFormat")
class TestTree(greentest.TestCase):

    def test_tree(self):
        import re
        glets = []
        l = MyLocal(42)
        assert l

        def t1():
            raise greentest.ExpectedException()

        def t2():
            l = MyLocal(16)
            assert l
            return gevent.spawn(t1)

        s1 = gevent.spawn(t2)
        s1.join()

        glets.append(gevent.spawn(t2))

        def t3():
            return gevent.spawn(t2)

        s3 = gevent.spawn(t3)
        s3.spawn_tree_locals['stl'] = 'STL'
        s3.join()

        s4 = gevent.spawn(util.GreenletTree.current_tree)
        s4.join()

        tree = s4.value
        self.assertTrue(tree.root)

        self.assertNotIn('Parent', str(tree)) # Simple output
        value = tree.format(details={'stacks': False})
        hexobj = re.compile('0x[0123456789abcdef]+L?', re.I)
        value = hexobj.sub('X', value)
        value = value.replace('epoll', 'select')
        value = value.replace('test__util', '__main__')

        self.maxDiff = None
        expected = """\
<greenlet.greenlet object at X>
 :    Greenlet Locals:
 :      Local <class '__main__.MyLocal'> at X
 :        {'foo': 42}
 +--- <QuietHub at X select default pending=0 ref=0>
 :          Parent: <greenlet.greenlet object at X>
 +--- <Greenlet "Greenlet-0" at X: _run>; finished with value <Greenlet "Greenlet-4" at X
 :          Parent: <QuietHub at X select default pending=0 ref=0>
 |    +--- <Greenlet "Greenlet-4" at X: _run>; finished with exception ExpectedException()
 :                Parent: <QuietHub at X select default pending=0 ref=0>
 +--- <Greenlet "Greenlet-1" at X: _run>; finished with value <Greenlet "Greenlet-5" at X
 :          Parent: <QuietHub at X select default pending=0 ref=0>
 :          Spawn Tree Locals
 :          {'stl': 'STL'}
 |    +--- <Greenlet "Greenlet-5" at X: _run>; finished with value <Greenlet "Greenlet-6" at X
 :                Parent: <QuietHub at X select default pending=0 ref=0>
 |         +--- <Greenlet "Greenlet-6" at X: _run>; finished with exception ExpectedException()
 :                      Parent: <QuietHub at X select default pending=0 ref=0>
 +--- <Greenlet "Greenlet-2" at X: _run>; finished with value <gevent.util.GreenletTree obje
 :          Parent: <QuietHub at X select default pending=0 ref=0>
 +--- <Greenlet "Greenlet-3" at X: _run>; finished with value <Greenlet "Greenlet-7" at X
            Parent: <QuietHub at X select default pending=0 ref=0>
      +--- <Greenlet "Greenlet-7" at X: _run>; finished with exception ExpectedException()
                  Parent: <QuietHub at X select default pending=0 ref=0>
        """.strip()
        self.assertEqual(value, expected)

if __name__ == '__main__':
    greentest.main()
