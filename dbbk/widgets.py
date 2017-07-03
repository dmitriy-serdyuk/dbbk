from os.path import dirname, realpath

from bokeh.events import Event
from bokeh.model import MetaModel
from bokeh.models.plots import Plot
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, Button
from bokeh.plotting import Figure


class DragDataTable(DataTable):
    __implementation__ = '../coffee/drag_data_table.coffee'


class DropPlot(Plot):
    __implementation__ = (dirname(realpath(__file__)) +
                          '/../coffee/drop_plot.coffee')


class AddLine(Event):
    event_name = 'add_line'

    def __init__(self, model, data):
        super(AddLine, self).__init__(model=model)
        self.data = data


del MetaModel.model_class_reverse_map['Figure']
Figure = type('Figure', (DropPlot, Figure), dict(Figure.__dict__))
Figure.__view_model__ = "DropPlot"
