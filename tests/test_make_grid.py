# The MIT License (MIT)
#
# Copyright (c) 2014-2017 Avant, Kirill Sevastyanenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


import unittest
import pandas

from lib.make_grid import make_grid


class MakeGridTestCase(unittest.TestCase):
    """Test converting a user described payload into a grid of values
    """
    def test_happy_case(self):
        payload = {'params': [{'max': 10, 'name': 'x', 'min': 8, 'type': 'int'},
                              {'options': ['foo', 'bar'], 'name': 'y', 'type': 'enum'},
                              {'max': 1, 'name': 'f', 'min': 0, 'type': 'float', 'num_points': 4}]}
        grid = make_grid(payload)
        self.assertTrue(isinstance(grid, pandas.core.frame.DataFrame))
        self.assertEqual(grid.shape, (24, 7))


if __name__ == '__main__':
    unittest.main()
