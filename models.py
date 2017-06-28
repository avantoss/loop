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


import pandas as pd
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app import db


class ModelGrid(db.Model):
    __tablename__ = 'model_grids'

    id = db.Column(db.String(), primary_key=True, index=True)
    grid = db.Column(JSONB)
    name = db.Column(db.String())
    chooser = db.Column(db.String())
    minimize = db.Column(db.Boolean)
    submissions = relationship("Submission", backref="model_grids", order_by="Submission.created_at")

    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    def __init__(self, id, grid, chooser, name=None, minimize=False):
        self.id = id
        self.name = name
        self.grid = grid
        self.minimize = minimize
        self.chooser = chooser

    def get_grid(self):
        return pd.read_json(self.grid)

    def best_value(self):
        values = [x.value for x in self.submissions]
        which = min if self.minimize else max
        try:
            best = which(values)
        except:
            best = None
        return best

    def __repr__(self):
        return '<model_grid {} of cardinality {}>'.format(self.id, pd.read_json(self.grid).shape)


class Submission(db.Model):
    __tablename__ = 'submissions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    model_id = db.Column(db.String(), ForeignKey('model_grids.id'), index=True)
    loop_id = db.Column(db.Integer())
    value = db.Column(db.Float())

    created_at = db.Column(DateTime, default=datetime.utcnow)
    updated_at = db.Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, model_id, loop_id, value):
        self.loop_id = loop_id
        self.model_id = model_id
        self.value = value

    def __repr__(self):
        return '<Submission id: <{}> for model grid {} of value {} for row {}>'.format(self.id,
                                                                                       self.model_id,
                                                                                       self.value,
                                                                                       self.loop_id)
