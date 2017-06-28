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


import numpy as np
import numpy.random as npr
import pandas as pd
import scipy.stats as sps
import sklearn.ensemble
import sklearn.ensemble.forest


class RandomForestRegressorWithVariance(sklearn.ensemble.RandomForestRegressor):
    def predict(self, X):
        # borrowed from
        # https://github.com/JasperSnoek/spearmint/blob/master/spearmint/spearmint/chooser/RandomForestEIChooser.py
        # A very elegant way to demonstrate the power of the framework
        X = np.atleast_2d(X)
        all_y_hat = [tree.predict(X) for tree in self.estimators_]
        y_hat = sum(all_y_hat) / self.n_estimators
        y_var = np.var(all_y_hat, axis=0, ddof=1)
        return y_hat, y_var


def next(grid, candidates, pending, complete, completed_values):
    # some sensible defaults
    rf = RandomForestRegressorWithVariance(n_estimators=50,
                                           max_depth=None,
                                           min_samples_split=1,
                                           max_features="auto",
                                           n_jobs=1,
                                           random_state=None)
    rf.fit(_encode_categorical_df(complete, grid), completed_values)
    if pending.shape[0]:
        # Generate fantasies for pending
        mean, variance = rf.predict(_encode_categorical_df(pending, grid))
        pending_value_estimation = pd.Series(mean + np.sqrt(variance) * npr.randn(mean.shape[0]))
        rf.fit(_encode_categorical_df(complete.append(pending), grid),
               completed_values.append(pending_value_estimation))

    # Predict the marginal means and variances at candidates.
    mean, variance = rf.predict(_encode_categorical_df(candidates, grid))
    best = np.min(completed_values)

    # Expected improvement
    # this is the part that I don't fully understand yet
    # will have to read this: http://arxiv.org/pdf/1012.2599.pdf
    func_s = np.sqrt(variance) + 0.0001
    Z = (best - mean) / func_s
    ncdf = sps.norm.cdf(Z)
    npdf = sps.norm.pdf(Z)
    ei = func_s * (Z * ncdf + npdf)

    best_cand = np.argmax(ei)
    return (best_cand, grid)


def _encode_categorical_df(df, fullgrid):
    all_columns = [x for x in pd.get_dummies(fullgrid).columns.values.tolist()
                   if not x.startswith("_loop")]
    encoded_df = pd.get_dummies(df)
    for cl in all_columns:
        if cl not in encoded_df.columns.values:
            encoded_df[cl] = 0
    return encoded_df
