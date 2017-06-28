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


import os
import operator
import math
import re
import json
import uuid
import pandas as pd
import numpy as np

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.uuid import FlaskUUID
from collections import Counter
from sqlalchemy import desc
from sklearn.manifold import TSNE

from lib.make_grid import make_grid
from lib.choosers import *
from lib.utils import *


app = Flask(__name__)
FlaskUUID(app)
app.config.from_object(os.getenv('APP_SETTINGS') or 'config.DevelopmentConfig')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import *


@app.route('/', methods=['GET'])
def index():
    try:
        modelgrids = db.session.query(ModelGrid).order_by(desc(ModelGrid.updated_at)).limit(10)
    except:
        return jsonify(exception="Cannot connect to the database.")
    return render_template('index.html', modelgrids=modelgrids)


@app.route('/model/<uuid:id>/')
def default_model_view(id):
    return redirect(url_for('.view_model', id=str(id), path='table'))


@app.route('/model/<uuid:id>/<path>', methods=['GET'])
def view_model(id, path):
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
        grid = modelgrid.get_grid()
        complete = grid.loc[grid._loop_status == "complete", :]
        complete = complete.sort_values(by="_loop_value", ascending=modelgrid.minimize)
        pending = grid.loc[grid._loop_status == "pending", :]
        columns = [x for x in list(grid.columns.values) if not x.startswith("_loop")]
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    try:
        return render_template('model_{}.html'.format(path),
                               modelgrid=modelgrid,
                               grid=grid,
                               complete=complete,
                               pending=pending,
                               columns=columns)
    except:
        return render_template('404.html', model_id=str(id)), 404


@app.route("/new_model", methods=['POST'])
def new_model():
    data = request.get_json() or {}
    if not data:
        return jsonify(exception="Invalid data POSTed to /new_model")
    try:
        grid = make_grid(data)
        new_model_id = uuid.uuid4()
        minimize = data.get("minimize") or False
        chooser = data.get("chooser") or DEFAULT_CHOOSER
        name = data.get("name") or "An experiment has no name"
        if chooser not in list(LIST_OF_CHOOSERS.keys()):
            error_string = """The chooser <{}> that you've supplied is not yet implemented.
                You can find the list of available choosers by querying /choosers endpoint."""
            return jsonify(exception=error_string.format(chooser))
        db.session.add(ModelGrid(new_model_id, grid.to_json(), chooser, name, minimize))
        db.session.commit()
    except:
        return jsonify(exception="Unable to add item to database.")
    return jsonify(id=new_model_id, grid_size=grid.shape, chooser=chooser, minimize=minimize)


@app.route("/report_metric/<uuid:id>", methods=['POST'])
def report_metric(id):
    data = request.get_json() or {}
    if not data:
        return jsonify(exception="Invalid data POSTed to /report_metric")
    if "value" not in data:
        return jsonify(exception="Must supply a <value> to /report_metric route")
    if "loop_id" not in data:
        return jsonify(exception="Must supply a <loop_id> to /report_metric route")
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
        candidates = modelgrid.get_grid()

        if not candidates.loc[candidates._loop_id == data.get('loop_id'), :].shape[0]:
            error_string = "No set of parameters corresponding to your id of {} found."
            return jsonify(exception=error_string.format(data.get('loop_id')))
        if not math.isnan(candidates.loc[candidates._loop_id == data.get('loop_id'), "_loop_value"]):
            error_string = "There is already a score of {} associated with this set of parameters"
            score = candidates.loc[candidates._loop_id == data.get('loop_id'), "_loop_value"]
            return jsonify(exception=error_string.format(round(float(score), 2)))

        candidates.loc[candidates._loop_id == data.get('loop_id'), "_loop_value"] = data.get("value")
        candidates.loc[candidates._loop_id == data.get('loop_id'), "_loop_status"] = "complete"
        if data.get("duration"):
            candidates.loc[candidates._loop_id == data.get('loop_id'),
                           "_loop_duration"] = data.get("duration")

        modelgrid.grid = candidates.to_json()
        # also record a submission
        db.session.add(Submission(str(id), int(data.get('loop_id')), float(data.get("value"))))
        db.session.commit()
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    return jsonify(status="ok")


@app.route("/choosers", methods=['GET', 'POST'])
def choosers():
    return jsonify(choosers=list(LIST_OF_CHOOSERS.keys()), default=DEFAULT_CHOOSER)


@app.route("/new_iteration/<uuid:id>", methods=['GET', 'POST'])
def new_point(id):
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
        full_grid = modelgrid.get_grid()
        candidates, pending, complete = slice_df(full_grid)
        values = complete["_loop_value"] * (-1)**(modelgrid.minimize + 1)
        if not candidates.shape[0]:
            return jsonify(exception="There are no more candidates left in the grid.")
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))

    acquisition_function = LIST_OF_CHOOSERS[modelgrid.chooser]
    # if we don't have any data to model with - use random search
    if complete.shape[0] < (app.config['RANDOM_SEARCH_THRESHOLD'] or 2):
        acquisition_function = LIST_OF_CHOOSERS["random"]
    relevant_columns = [x for x in full_grid.columns.values.tolist() if not x.startswith("_loop")]
    selected_row, new_grid = acquisition_function(full_grid,
                                                  candidates[relevant_columns],
                                                  pending[relevant_columns],
                                                  complete[relevant_columns],
                                                  values)

    selected_row = int(candidates.iloc[selected_row]["_loop_id"])
    new_grid.loc[new_grid._loop_id == selected_row, "_loop_status"] = "pending"
    params = new_grid.loc[new_grid._loop_id == selected_row, :].to_dict(orient='records')[0]
    params = {k: v for k, v in params.items() if not k.startswith('_loop')}

    try:
        modelgrid.grid = new_grid.to_json()
        db.session.commit()
    except:
        error_string = "Unable to update the model grid in the database for an unknown reason."
        return jsonify(exception=error_string)
    return jsonify(params=params, loop_id=selected_row)


@app.route("/grid/<uuid:id>", methods=['GET'])
def view_grid(id):
    ALLOWED_SUBSET_TYPES = [
        "complete",
        "pending",
        "candidate"
    ]
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    grid = modelgrid.get_grid()
    subset = request.args.get('subset')
    if subset:
        if subset in ALLOWED_SUBSET_TYPES:
            grid = grid.loc[grid._loop_status == subset, :]
        else:
            return jsonify(exception="Unknown subset type <{}>".format(subset))
    return jsonify(grid=grid.to_json(), minimize=modelgrid.minimize)


@app.route("/last_values/<uuid:id>", methods=['GET'])
def last_values(id):
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    values = [x.value for x in modelgrid.submissions]
    return jsonify(values=values[-20:])


@app.route("/partial_dependency_data/<uuid:id>/<column>", methods=['GET'])
def partial_dependency_data(id, column):
    try:
        grid = db.session.query(ModelGrid).filter_by(id=str(id)).first().get_grid()
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    aggregate = grid.loc[grid._loop_status == "complete", :]
    aggregate = aggregate.groupby(column)
    aggregate = aggregate.groups
    aggregate = {str(k): grid.loc[v, '_loop_value'].values.tolist() for k, v in aggregate.items()}
    return jsonify(data=aggregate)


@app.route("/tsne_data/<uuid:id>/", methods=['GET'])
def tsne_data(id):
    NUM_CATEGORIES = 5
    try:
        modelgrid = db.session.query(ModelGrid).filter_by(id=str(id)).first()
        grid = modelgrid.get_grid().sort_values(by="_loop_id")
    except:
        return jsonify(exception="Unable to find a model with uuid {} in the database.".format(id))
    columns = [x for x in list(grid.columns.values) if not x.startswith("_loop")]
    coords = grid.loc[:, columns]
    metric = request.args.get('metric') if request.args.get('metric') else 'mahalanobis'
    model = TSNE(random_state=0, n_iter_without_progress=30, metric=metric)
    try:
        projection = model.fit_transform(coords)
    except ValueError as err:
        return jsonify(exception="Unable to fit TSNE for model with uuid {} because: {}".format(id, err))
    # subdivide into array of arrays based on _loop_value
    classes = grid.groupby(pd.cut(grid._loop_value, NUM_CATEGORIES)).groups
    missing = grid.loc[grid._loop_value.isnull()].index.tolist()
    # find best point for the chart
    submissions = modelgrid.submissions
    values = [x.value for x in submissions]
    which_best = np.argmin(values) if modelgrid.minimize else np.argmax(values)
    which_best = [x.loop_id for x in submissions][which_best]
    # split and highlight points
    points = {}
    which_missing = [int(x) for x in missing]
    points['unsampled'] = {
        'coordinates': projection[which_missing].tolist(),
        'tooltip': coords.loc[which_missing].to_json(),
        'loop_id': which_missing,
        'value': ['NaN' for x in which_missing]
    }

    for k in classes.keys():
        which = [int(x) for x in classes[k]]
        if which_best in which:
            best_point = {
                'coordinates': projection[which_best].tolist(),
                'tooltip': coords.loc[which_best].to_json(),
                'loop_id': which_best,
                'value': grid.loc[which_best]._loop_value
            }
        else:
            best_point = False
        coordinates = projection[which].tolist()
        tooltip = coords.loc[which].to_json()
        points[k] = {
            'coordinates': coordinates,
            'tooltip': tooltip,
            'loop_id': which,
            'value': list(grid.loc[which]._loop_value.values),
            'best_point': best_point
        }
    return jsonify(projection=points, best_point=best_point)


@app.errorhandler(404)
def page_not_found(e):
    try:
        model_id = db.session.query(ModelGrid).order_by(desc(ModelGrid.updated_at)).first().id
    except:
        model_id = ''

    return render_template('404.html', model_id=model_id), 404


@app.errorhandler(500)
def page_not_found(e):
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run()
