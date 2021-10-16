from lightgbm import LGBMRegressor, LGBMClassifier
from pandas import DataFrame


def train_regression(features: DataFrame, targets: DataFrame, params: dict = None):
    if params is None:
        params = {"n_estimators": 2000,
                  "learning_rate": 0.01,
                  "max_depth": 5,
                  "num_leaves": 2 ** 5,
                  "colsample_bytree": 0.1}

    model = LGBMRegressor(**params)
    model.fit(features, targets)
    return model


def train_classification(features: DataFrame, labels: DataFrame, params: dict):
    if params is None:
        params = {"n_estimators": 2000,
                  "learning_rate": 0.01,
                  "max_depth": 5,
                  "num_leaves": 2 ** 5,
                  "colsample_bytree": 0.1}

    model = LGBMClassifier(**params)
    model.fit(features, targets)
    return model