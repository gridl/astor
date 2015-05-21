"""
Part of the astor library for Python AST manipulation

License: 3-clause BSD

Copyright (c) 2014 Berker Peksag
"""

import ast
import sys
import textwrap

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import astor


def canonical(srctxt):
    return textwrap.dedent(srctxt).strip()

class CodegenTestCase(unittest.TestCase):

    def assertAstEqual(self, srctxt):
        """This asserts that the reconstituted source
           code can be compiled into the exact same AST
           as the original source code.
        """
        srctxt = canonical(srctxt)
        srcast = ast.parse(srctxt)
        dsttxt = astor.to_source(srcast)
        dstast = ast.parse(dsttxt)
        srcdmp = astor.dump_tree(srcast)
        dstdmp = astor.dump_tree(dstast)
        self.assertEqual(dstdmp, srcdmp)

    def assertAstEqualIfAtLeastVersion(self, source, min_should_work,
                                                max_should_error=None):
        if max_should_error is None:
            max_should_error = min_should_work[0], min_should_work[1] - 1
        if sys.version_info >= min_should_work:
            self.assertAstEqual(source)
        elif sys.version_info <= max_should_error:
            self.assertRaises(SyntaxError, ast.parse, source)

    def assertAstSourceEqual(self, srctxt):
        """This asserts that the reconstituted source
           code is identical to the original source code.
           This is a much stronger statement than assertAstEqual,
           which may not always be appropriate.
        """
        srctxt = canonical(srctxt)
        self.assertEqual(astor.to_source(ast.parse(srctxt)), srctxt)

    def assertAstSourceEqualIfAtLeastVersion(self, source, min_should_work,
                                                max_should_error=None):
        if max_should_error is None:
            max_should_error = min_should_work[0], min_should_work[1] - 1
        if sys.version_info >= min_should_work:
            self.assertAstSourceEqual(source)
        elif sys.version_info <= max_should_error:
            self.assertRaises(SyntaxError, ast.parse, source)

    def test_imports(self):
        source = "import ast"
        self.assertAstSourceEqual(source)
        source = "import operator as op"
        self.assertAstSourceEqual(source)
        source = "from math import floor"
        self.assertAstSourceEqual(source)
        source = "from .. import foobar"
        self.assertAstSourceEqual(source)
        source = "from ..aaa import foo, bar as bar2"
        self.assertAstSourceEqual(source)

    def test_dictionary_literals(self):
        source = "{'a': 1, 'b': 2}"
        self.assertAstSourceEqual(source)
        another_source = "{'nested': ['structures', {'are': 'important'}]}"
        self.assertAstSourceEqual(another_source)

    def test_try_expect(self):
        source = """
        try:
            'spam'[10]
        except IndexError:
            pass"""
        self.assertAstEqual(source)

        source = """
        try:
            'spam'[10]
        except IndexError as exc:
            sys.stdout.write(exc)"""
        self.assertAstEqual(source)

        source = """
        try:
            'spam'[10]
        except IndexError as exc:
            sys.stdout.write(exc)
        else:
            pass
        finally:
            pass"""
        self.assertAstEqual(source)

    def test_del_statement(self):
        source = "del l[0]"
        self.assertAstSourceEqual(source)
        source = "del obj.x"
        self.assertAstSourceEqual(source)

    def test_arguments(self):
        source = """
        j = [1, 2, 3]

        def test(a1, a2, b1=j, b2='123', b3={}, b4=[]):
            pass"""
        self.assertAstSourceEqual(source)

    def test_pass_arguments_node(self):
        source = canonical("""
        j = [1, 2, 3]

        def test(a1, a2, b1=j, b2='123', b3={}, b4=[]):
            pass""")
        root_node = ast.parse(source)
        arguments_node = [n for n in ast.walk(root_node)
                          if isinstance(n, ast.arguments)][0]
        self.assertEqual(astor.to_source(arguments_node),
                         "a1, a2, b1=j, b2='123', b3={}, b4=[]")
        source = """
        def call(*popenargs, timeout=None, **kwargs):
            pass"""
        # Probably also works on < 3.4, but doesn't work on 2.7...
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 4), (2, 7))

    def test_matrix_multiplication(self):
        for source in ("(a @ b)", "a @= b"):
            self.assertAstEqualIfAtLeastVersion(source, (3, 5))

    def test_multiple_call_unpackings(self):
        source = """
        my_function(*[1], *[2], **{'three': 3}, **{'four': 'four'})"""
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 5))

    def test_right_hand_side_dictionary_unpacking(self):
        source = """
        our_dict = {'a': 1, **{'b': 2, 'c': 3}}"""
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 5))

    def test_async_def_with_for(self):
        source = """
        async def read_data(db):
            async with connect(db) as db_cxn:
                data = await db_cxn.fetch('SELECT foo FROM bar;')
            async for datum in data:
                if quux(datum):
                    return datum"""
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 5))

    def test_class_definition_with_starbases_and_kwargs(self):
        source = """
        class TreeFactory(*[FactoryMixin, TreeBase], **{'metaclass': Foo}):
            pass"""
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 0))

    def test_yield(self):
        source = "yield"
        self.assertAstEqual(source)
        source = """
        def dummy():
            yield"""
        self.assertAstEqual(source)
        source = "foo((yield bar))"
        self.assertAstEqual(source)
        source = "(yield bar)()"
        self.assertAstEqual(source)
        source = "return (yield 1)"
        self.assertAstEqual(source)
        source = "return (yield from sam())"
        self.assertAstEqualIfAtLeastVersion(source, (3, 3))

    def test_with(self):
        source = """
            with foo:
                pass
        """
        self.assertAstSourceEqual(source)
        source = """
            with foo as bar:
                pass
        """
        self.assertAstSourceEqual(source)
        source = """
            with foo as bar, mary, william as bill:
                pass
        """
        self.assertAstSourceEqualIfAtLeastVersion(source, (3, 3), (1, 0))

    def test_inf(self):
        source = """
            (1e1000) + (-1e1000) + (1e1000j) + (-1e1000j)
        """
        self.assertAstEqual(source)

    def test_unary(self):
        source = """
            -(1) + ~(2) + +(3)
        """
        self.assertAstEqual(source)

    def test_pow(self):
        source = """
            (-2) ** (-3)
        """
        self.assertAstEqual(source)
        source = """
            (+2) ** (+3)
        """
        self.assertAstEqual(source)
        source = """
            2 ** 3 ** 4
        """
        self.assertAstEqual(source)
        source = """
            -2 ** -3
        """
        self.assertAstEqual(source)
        source = """
            -2 ** -3 ** -4
        """
        self.assertAstEqual(source)

if __name__ == '__main__':
    unittest.main()
