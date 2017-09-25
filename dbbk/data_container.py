import json

import pandas
import pickle
import yaml
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TableColumn, Button
from bokeh.themes import Theme

from .widgets import Figure, AddLine, DragDataTable


class DataContainer(object):
    column_names = ['iteration', 'value', 'experiment', 'variable']

    def __init__(self):
        self.data_frame = pandas.DataFrame(columns=self.column_names)
        self.experiments = []

    def save_state(self, name='dbbk_state.pkl'):
        with open(name, 'wb') as f:
            pickle.dump([self.data_frame, self.experiments], f)

    def load_state(self, name='dbbk_state.pkl'):
        with open(name, 'rb') as f:
            self.data_frame, self.experiments = pickle.load(f)

    def get_points(self, experiment, variable):
        filtered = self.data_frame[(self.data_frame.experiment == experiment) &
                                   (self.data_frame.variable == variable)]
        return (filtered['iteration'].as_matrix(),
                filtered['value'].as_matrix())

    def add_line_callback(self, plot, data_sources):
        def callback(ev):
            data = json.loads(ev.data)
            experiment = data['experiment']
            variable = data['variable']

            iteration, value = self.get_points(experiment, variable)
            src = ColumnDataSource(dict(iteration=iteration, value=value))

            plot.line('iteration', 'value', source=src,
                      legend="{}: {}".format(experiment, variable))
            plot.legend.click_policy = "hide"
            if plot in data_sources:
                data_sources[plot].append((src, experiment, variable))
            else:
                data_sources[plot] = [(src, experiment, variable)]
        return callback

    def add_plot_callback(self, plots_layout, data_sources):
        def callback():
            plot = Figure(x_axis_type='linear', y_range=(0, 25),
                          y_axis_label='value',
                          x_axis_label='iteration')
            plot.on_event(AddLine, self.add_line_callback(plot, data_sources))
            plots_layout.children.append(plot)
        return callback

    def add_smoothing_callback(self, source_smooth, plot):
        def callback(attr, old, new):
            # TODO: fix smoothing
            if new == 0:
                data = plot
            else:
                data = self.df.rolling(new).mean()
            source_smooth.data = ColumnDataSource(data=data).data
        return callback

    def add_update_data_callback(self, data_sources, datastreams_source):
        def update_data():
            for plot, plot_properties in data_sources.items():
                for source, experiment, variable in plot_properties:
                    new_data = {}
                    iteration, value = self.get_points(experiment, variable)
                    len_diff = (len(iteration) -
                                len(source.data['iteration']))
                    if len_diff > 0:
                        new_data['iteration'] = iteration[-len_diff:]
                        new_data['value'] = value[-len_diff:]
                        source.stream(new_data)
            len_diff = (len(self.experiments) -
                        len(datastreams_source.data['experiment']))
            if len_diff > 0:
                new_data = {
                    'experiment':
                        [experiment for experiment, _ in self.experiments[-len_diff:]],
                    'variable': [variable for _, variable
                                 in self.experiments[-len_diff:]]}
                datastreams_source.stream(new_data)
        return update_data

    def modify_doc(self, doc):
        data_sources = {}
        datastreams_source = ColumnDataSource(dict(experiment=[], variable=[]))
        slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing")
        # TODO: uncomment when smoothing is fixed
        #slider.on_change(
        #    'value', self.add_smoothing_callback(source_smooth, plot))

        columns = [
            TableColumn(field="experiment", title="Experiment"),
            TableColumn(field="variable", title="Variable")]
        data_table = DragDataTable(
            source=datastreams_source, columns=columns, width=400, height=280)

        # TODO: make interval configurable, add refresh button
        doc.add_periodic_callback(
            self.add_update_data_callback(data_sources, datastreams_source),
            6000)

        tools_layout = column(slider, data_table)
        add_plot_button = Button(label='Add Plot', button_type="success", name='my_button')
        plots_layout = column(add_plot_button)

        add_plot_button.on_click(
            self.add_plot_callback(plots_layout, data_sources))

        main_layout = row(tools_layout, plots_layout)
        doc.add_root(main_layout)

        doc.theme = Theme(json=yaml.load("""
            attrs:
                Figure:
                    background_fill_color: "#DDDDDD"
                    outline_line_color: white
                    toolbar_location: above
                    height: 500
                Grid:
                    grid_line_dash: [6, 4]
                    grid_line_color: white
        """))