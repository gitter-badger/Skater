"""Partial Dependence class"""
from itertools import cycle
import numpy as np
import pandas as pd

from ...data import DataManager
from .base import BaseGlobalInterpretation
from ...util.plotting import COLORS
from ...util.exceptions import *


class FeatureImportance(BaseGlobalInterpretation):
    """Contains methods for feature importance. Subclass of BaseGlobalInterpretation"""

    @staticmethod
    def _build_fresh_metadata_dict():
        return {
            'pdp_cols': {},
            'sd_col': '',
            'val_cols': []
        }


    def feature_importance(self, model_instance, ascending=True, y_true=None):

        """
        Computes feature importance of all features related to a model instance.
        Supports classification, multi-class classification, and regression.

        Parameters
        ----------
        model_instance: lynxes.model.model.Model subtype
            the machine learning model "prediction" function to explain, such that
            predictions = predict_fn(data).
        ascending: boolean, default True
            Helps with ordering Ascending vs Descending
        y_true: Target values, if available

        Returns
        -------
        importances : Sorted Series


        Examples
        --------
            >>> from lynxes.model import InMemoryModel
            >>> from lynxes.core.explanations import Interpretation
            >>> from sklearn.ensemble import RandomForestClassier
            >>> rf = RandomForestClassier()
            >>> rf.fit(X,y)
            >>> model = InMemoryModel(rf, examples = X)
            >>> interpreter = Interpretation()
            >>> interpreter.load_data(X)
            >>> interpreter.feature_importance.feature_importance(model)
        """

        importances = {}
        original_predictions = model_instance.predict(self.data_set.data) if y_true is None else y_true
        n = original_predictions.shape[0]

        # import pdb
        # pdb.set_trace()
        # instead of copying the whole dataset, should we copy a column, change column values,
        # revert column back to copy?
        copy_of_data_set = DataManager(self.data_set.data,
                                       feature_names=self.data_set.feature_ids,
                                       index=self.data_set.index)

        for feature_id in self.data_set.feature_ids:
            # collect perturbations
            samples = self.data_set.generate_column_sample(feature_id, n_samples=n, method='random-choice')
            copy_of_data_set[feature_id] = samples

            # get size of perturbations
            # feature_perturbations = self.data_set[feature_id] - copy_of_data_set[feature_id]

            # predict based on perturbed values
            new_predictions = model_instance.predict(copy_of_data_set.data)

            # evaluated entropy of scaled changes.
            changes_in_predictions = new_predictions - original_predictions
            importance = np.mean(np.std(changes_in_predictions, axis=0))
            importances[feature_id] = importance

            # reset copy
            copy_of_data_set[feature_id] = self.data_set[feature_id]

        importances = pd.Series(importances).sort_values(ascending=ascending)
        importances = importances / importances.sum()
        return importances


    def plot_feature_importance(self, predict_fn, y_true=None, ascending=True, ax=None):
        """Computes feature importance of all features related to a model instance,
        then plots the results. Supports classification, multi-class classification, and regression.


        Parameters
        ----------
        predict_fn: lynxes.model.model.Model subtype
            estimator "prediction" function to explain the predictive model. Could be probability estimates
            or target values
        y_true: Target values, if available
        ascending: boolean, default True
            Helps with ordering Ascending vs Descending
        ax: matplotlib.axes._subplots.AxesSubplot
            existing subplot on which to plot feature importance. If none is provided,
            one will be created.

        Examples
        --------
            >>> from lynxes.model import InMemoryModel
            >>> from lynxes.core.explanations import Interpretation
            >>> from sklearn.ensemble import RandomForestClassier
            >>> rf = RandomForestClassier()
            >>> rf.fit(X,y)
            >>> model = InMemoryModel(rf, examples = X)
            >>> interpreter = Interpretation()
            >>> interpreter.load_data(X)
            >>> interpreter.feature_importance.plot_feature_importance(model, ascending=True, ax=ax)
            """
        try:
            global pyplot
            from matplotlib import pyplot
        except ImportError:
            raise (MatplotlibUnavailableError("Matplotlib is required but unavailable on your system."))
        except RuntimeError:
            raise (MatplotlibDisplayError("Matplotlib unable to open display"))

        importances = self.feature_importance(predict_fn, ascending=ascending, y_true=y_true)

        if ax is None:
            f, ax = pyplot.subplots(1)
        else:
            f = ax.figure

        colors = cycle(COLORS)
        color = next(colors)
        # Below is a weirdness because of how pandas plot is behaving. There might be a better way
        # to resolve the issuse of sorting based on axis
        if ascending is True:
            importances.sort_values(ascending=False).plot(kind='barh', ax=ax, color=color)
        else:
            importances.sort_values(ascending=True).plot(kind='barh', ax=ax, color=color)
        return f, ax
