import gzip
import json
import pandas
import pickle
import yaml
from os.path import isfile
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider, TableColumn, Button, Band
from bokeh.palettes import Spectral11
from bokeh.themes import Theme

from .widgets import Figure, AddLine, DragDataTable


def smooth_frame(source, slider_value):
    df = pandas.DataFrame(data=source.data).sort_values(by="iteration")
    df = df[['iteration', 'value']]
    total_length = len(df)
    window_size = int(float(total_length) / 100. * slider_value)
    if window_size > 1:
        series = df.value.rolling(window_size)
        means = series.mean().fillna(method='bfill').reset_index()['value'].rename('value_mean')
        stds = series.std().fillna(method='bfill').reset_index()['value'].rename('value_std')
    else:
        means = df['value'].rename('value_mean')
        stds = (df['value'] * 0).rename('value_std')
    df = pandas.concat([df, means, stds], axis=1)

    df['lower'] = df.value_mean - df.value_std
    df['upper'] = df.value_mean + df.value_std

    source = ColumnDataSource({k: v.as_matrix() for k, v in df.to_dict(orient='series').items()})
    return source


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

    def create_line_callback(self, plot, data_sources, slider):
        def callback(ev):
            data = json.loads(ev.data)
            experiment = data['experiment']
            variable = data['variable']

            iteration, value = self.get_points(experiment, variable)
            src = ColumnDataSource(dict(iteration=iteration, value=value))
            src = smooth_frame(src, int(slider.value))

            plot.yaxis.axis_label = variable
            color = Spectral11[self.experiments.index((experiment, variable))]
            line_mean = plot.line(
                'iteration', 'value_mean',
                line_width=5,
                source=src,
                legend="{}: {}".format(experiment, variable),
                color=color)
            line = plot.line(
                'iteration', 'value',
                line_width=1,
                alpha=0.2,
                source=src,
                color=color)

            band = Band(base='iteration', lower='lower', upper='upper', source=src, level='underlay',
                        fill_alpha=0.3, line_width=0, line_color=color, fill_color=color)
            plot.add_layout(band)

            def flip_visible(attr, old, new):
                line.visible = new
                band.visible = new

            line_mean.on_change('visible', flip_visible)

            plot.legend.click_policy = "hide"
            if plot in data_sources:
                data_sources[plot].append((src, experiment, variable))
            else:
                data_sources[plot] = [(src, experiment, variable)]
        return callback

    def create_add_plot_callback(self, plots_layout, data_sources, slider):
        def callback():
            plot = Figure(x_axis_type='linear',
                          y_axis_label='value',
                          x_axis_label='iteration')
            plot.on_event(AddLine, self.create_line_callback(plot, data_sources, slider))
            plots_layout.children.append(plot)
        return callback

    def add_smoothing_callback(self, data_sources):
        def callback(attr, old, new):
            for plot, plot_properties in data_sources.items():
                for source, experiment, variable in plot_properties:
                    source.data = smooth_frame(source, int(new)).data

        return callback

    def create_update_data_callback(self, data_sources, datastreams_source, slider):
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

                        new_data['value_mean'] = value[-len_diff:]
                        new_data['value_std'] = value[-len_diff:]
                        new_data['upper'] = value[-len_diff:]
                        new_data['lower'] = value[-len_diff:]

                        source.stream(new_data)
                    source.data = smooth_frame(source, int(slider.value)).data
            len_diff = (len(self.experiments) -
                        len(datastreams_source.data['experiment']))
            if len_diff > 0:
                new_data = {
                    'experiment':
                        [experiment for experiment, _ in self.experiments[-len_diff:]],
                    'variable':
                        [variable for _, variable in self.experiments[-len_diff:]]}
                datastreams_source.stream(new_data)
        return update_data

    def modify_doc(self, doc):
        data_sources = {}
        datastreams_source = ColumnDataSource(dict(experiment=[], variable=[]))
        slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing")

        columns = [
            TableColumn(field="experiment", title="Experiment"),
            TableColumn(field="variable", title="Variable")]
        data_table = DragDataTable(
            source=datastreams_source, columns=columns, width=400, height=280)

        # TODO: add refresh button
        doc.add_periodic_callback(
            self.create_update_data_callback(data_sources, datastreams_source, slider),
            self.update_freq)
        doc.add_next_tick_callback(self.create_update_data_callback(data_sources, datastreams_source, slider))

        tools_layout = column(slider, data_table)
        add_plot_button = Button(label='Add Plot', button_type="success", name='my_button')
        plots_layout = column(add_plot_button)
        slider.on_change('value', self.add_smoothing_callback(data_sources))

        add_plot_button.on_click(
            self.create_add_plot_callback(plots_layout, data_sources, slider))

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
