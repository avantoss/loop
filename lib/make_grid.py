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


import math
import numpy as np
import pandas as pd
import itertools as it


def make_grid(payload):
    values = list()
    for variable in payload.get("params"):
        _check_presense(["name", "type"], variable)
        if variable.get("type") == "int":
            _check_inclusion(["min", "max"], variable)
            if variable.get("num_points"):
                grid_points = np.rint(np.linspace(variable.get("min"),
                                          variable.get("max"),
                                          variable.get("num_points"))).tolist()
            else:
                grid_points = list(range(variable.get("min"), variable.get("max") + 1))
            values.append({"name": variable.get("name"),
                           "values": grid_points})
        elif variable.get("type") == "float":
            _check_inclusion(["min", "max", "num_points"], variable)
            values.append({"name": variable.get("name"),
                           "values": list(np.linspace(variable.get("min"), variable.get("max"),
                                          variable.get("num_points"), endpoint=True))})
        elif variable.get("type") == "enum":
            _check_inclusion(["options"], variable)
            values.append({"name": variable.get("name"), "values": variable.get("options")})
        else:
            error_string = "Variable {} has incorrect type. Must be one of: int, float, enum"
            raise TypeError(error_string.format(variable.get("name")))

    return _expand_grid({x.get("name"): x.get("values") for x in values})


def _raise_type_error(missing):
    raise TypeError("All variables must have a {}".format(missing))


def _check_presense(keys, dictionary):
    for key in keys:
        if key not in dictionary:
            _raise_type_error(key)


def _check_inclusion(keys, variable):
    for key in keys:
        if key not in variable:
            error_string = "Variable {} of type {} must have <{}> key associated with it"
            raise TypeError(error_string.format(variable.get("name"), variable.get("type"), key))


def _expand_grid(value_hash):
    grid = pd.DataFrame(list(it.product(*[y for x, y in value_hash.items()])),
                        columns=[x for x in value_hash])
    grid['_loop_status'] = "candidate"
    grid['_loop_value'] = math.nan
    grid['_loop_duration'] = math.nan
    grid['_loop_id'] = range(grid.shape[0])
    return grid
