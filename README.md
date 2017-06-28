# ![avant logo](https://avantprod.global.ssl.fastly.net/assets/v3/home2/logo-icon-dark-ddd7488b0288497a8f9ea2c5aa24f65d.png) Loop [![Build Status](https://travis-ci.org/avantcredit/loop.svg?branch=master)](https://travis-ci.org/avantcredit/loop) [![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Hyperparameter optimization as a service

Take a look at
[this](https://github.com/avantcredit/loop/raw/master/BayesianOptimization.pptx)
presentation to see why you might need this.

If you'd like to make a change, or make a request to make a change
(like ask to improve a certain aspect of documentation, or add authentication support, etc.),
please open an issue before you start working on a pull request. This way
we can plan the implementation together and keep the project coherent and useful to a wider community.

## Official clients

Please open an issue if you'd like a new client package to be listed here.

language|link to project                         |comment
--------|:---------------------------------------|--------
R       |https://github.com/kirillseva/loopr     | official R client
python  |your package could be here!             | :bow:

## API reference

### POST /new_model
Kick off a new experiment.

```
# example request payload
{
    "minimize": false,          # i.e. minimize RMSE, maximize AUC
    "chooser": "gp_regressor",  # can choose any from lib/choosers
    "name": "human readable",   # name to be displayed on dashboard
    "params": [                 # define parameter space
        {
            "max": 10,
            "min": 8,
            "name": "x",
            "type": "int"       # integer hyperparameter
        },
        {
            "name": "y",
            "options": [
                "foo",
                "bar"
            ],
            "type": "enum"      # categorical hyperparameter
        },
        {
            "max": 1,
            "min": 0,
            "name": "f",
            "num_points": 4,
            "type": "float"     # continuous hyperparameter
        }
    ]
}

# response
{
    "chooser": "gp_regressor",  # stick to default unless you know what you're doing
    "grid_size": [
        24,
        7
    ],
    "id": "2083ff0f-8a92-4e46-aa3c-5ab31dc305f5", # experiment_id, remember it!
    "minimize": false
}
```

### GET /choosers
List available choosers.

```
# example response
{
    "choosers": [
        "random",
        "random_forest_regressor",
        "gp_regressor"
    ],
    "default": "gp_regressor"
}
```

### GET /new_iteration/{experiment_id}
Get a set of hyperparameters to evaluate.

```
# example response
{
    "loop_id": 11,          # id of a point on hyperparameter grid. you'll need it later
    "params": {             # parameters for training a model
        "f": 1.0,
        "x": 9,
        "y": "foo"
    }
}
```

### POST /report_metric/{experiment_id}
Report results of a model training run.

```
# example request payload
{
    "duration": 42,         # how long it took to build a model
    "loop_id": 11,          # id that you got from POST /new_iteration/***
    "value": 0.1            # metric value, i.e. RMSE
}
```

### GET /grid/{experiment_id}
List grid points corresponding to an experiment.
Can pass an optional query parameter `subset`.
Subset can be one of "complete", "pending" or "candidate".
If you don't specify it the whole grid will be returned.

```
# example response
{
    "grid": "{\"_loop_duration\":{\"1.0\":42.0,\"11.0\":null},\"_loop_id\":{\"1.0\":1,\"11.0\":11},\"_loop_status\":{\"1.0\":\"complete\",\"11.0\":\"complete\"},\"_loop_value\":{\"1.0\":0.1,\"11.0\":0.6},\"f\":{\"1.0\":0.3333333333,\"11.0\":1.0},\"x\":{\"1.0\":8,\"11.0\":9},\"y\":{\"1.0\":\"foo\",\"11.0\":\"foo\"}}",
    "minimize": false
}
```

## Quick Start

```sh
$ pip install -r requirements.txt
$ python manage.py db upgrade
```

You're ready to go!

### Tests

Tests go in /tests and can be run with

```sh
$ python -m unittest discover tests
```
