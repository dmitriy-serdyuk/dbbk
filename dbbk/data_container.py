import gzip
import json
import pandas
import pickle
import yaml
from os.path import isfile
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TableColumn, Button
from bokeh.palettes import Spectral11
from bokeh.themes import Theme

from .widgets import Figure, AddLine, DragDataTable


class DataContainer(object):
    column_names = ['iteration', 'value', 'experiment', 'variable']

    def __init__(self, update_freq, load_state='dbbk_state.jsonl.gz'):
        self.update_freq = update_freq
        self.data_frame = pandas.DataFrame(columns=self.column_names)
        if isfile(load_state):
            self.load_state(load_state)
        else:
            print('.. did not find saved state')
            self.experiments = []  # [(experiment, variable)]

    def save_state(self, name='dbbk_state.jsonl.gz'):
        with open(name, 'wb') as f:
            pickle.dump([self.data_frame, self.experiments], f)
        with gzip.open(name, 'wb') as f:
            f.write(json.dumps({'experiments': self.experiments}).encode())
            f.write('\n'.encode())

            for ind, row in self.data_frame.iterrows():
                f.write(json.dumps(dict(ind=int(ind), data=json.loads(row.to_json()))).encode())
                f.write('\n'.encode())

    def load_state(self, name='dbbk_state.jsonl.gz'):
        with gzip.open(name, 'rb') as f:
            print('.. loading data from ', name)
            for line in f:
                line = json.loads(line.decode())
                if 'experiments' in line:
                    self.experiments = [tuple(exp) for exp in line['experiments']]
                if 'data' in line:
                    data = line['data']
                    self.data_frame.loc[line['ind']] = [data[col] for col in self.column_names]

    def add_data(self, iteration, value, experiment, variable):
        new_data = dict(iteration=iteration, value=value, experiment=experiment, variable=variable)
        self.data_frame.loc[len(self.data_frame)] = new_data
        if (experiment, variable) not in self.experiments:
            self.experiments.append((experiment, variable))

    def get_points(self, experiment, variable):
        filtered = self.data_frame[(self.data_frame.experiment == experiment) &
                                   (self.data_frame.variable == variable)]
        return (filtered['iteration'].as_matrix(),
                filtered['value'].as_matrix())

    def create_line_callback(self, plot, data_sources):
        def callback(ev):
            data = json.loads(ev.data)
            experiment = data['experiment']
            variable = data['variable']

            iteration, value = self.get_points(experiment, variable)
            src = ColumnDataSource(dict(iteration=iteration, value=value))

            plot.yaxis.axis_label = variable
            plot.line('iteration', 'value',
                      line_width=3,
                      source=src,
                      legend="{}: {}".format(experiment, variable),
                      color=Spectral11[self.experiments.index((experiment, variable))])
            plot.legend.click_policy = "hide"
            if plot in data_sources:
                data_sources[plot].append((src, experiment, variable))
            else:
                data_sources[plot] = [(src, experiment, variable)]
        return callback

    def create_add_plot_callback(self, plots_layout, data_sources):
        def callback():
            plot = Figure(x_axis_type='linear',
                          y_axis_label='value',
                          x_axis_label='iteration')
            plot.on_event(AddLine, self.create_line_callback(plot, data_sources))
            plots_layout.children.append(plot)
        return callback

    def add_smoothing_callback(self, source_smooth):
        def callback(attr, old, new):
            # TODO: fix smoothing
            if new == 0:
                data = plot
            else:
                for experiment, variable in self.experiments:
                    data = self.df.rolling(new).mean()
            source_smooth.data = ColumnDataSource(data=data).data
        return callback

    def create_update_data_callback(self, data_sources, datastreams_source):
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
        slider.on_change(
            'value', self.add_smoothing_callback(data_sources))

        columns = [
            TableColumn(field="experiment", title="Experiment"),
            TableColumn(field="variable", title="Variable")]
        data_table = DragDataTable(
            source=datastreams_source, columns=columns, width=400, height=280)

        # TODO: add refresh button
        doc.add_periodic_callback(
            self.create_update_data_callback(data_sources, datastreams_source),
            self.update_freq)
        doc.add_next_tick_callback(self.create_update_data_callback(data_sources, datastreams_source))

        tools_layout = column(slider, data_table)
        add_plot_button = Button(label='Add Plot', button_type="success", name='my_button')
        plots_layout = column(add_plot_button)

        add_plot_button.on_click(
            self.create_add_plot_callback(plots_layout, data_sources))

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