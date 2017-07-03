from __future__ import print_function
import json
from flask import Flask, render_template
import pandas
import yaml

from tornado.ioloop import IOLoop

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.embed import autoload_server
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider
from bokeh.server.server import Server
from bokeh.themes import Theme
import numpy
from bokeh.models.widgets import TableColumn, Button

from dbbk import AddLine, Figure, DragDataTable


class DataContainer(object):
    def __init__(self):
        self.data_frame = pandas.DataFrame(
            columns=['iteration', 'value', 'model', 'experiment'])
        self.experiments = []

    def get_points(self, model, experiment):
        filtered = self.data_frame[(self.data_frame.model == model) &
                                   (self.data_frame.experiment == experiment)]
        return (filtered['iteration'].as_matrix(),
                filtered['value'].as_matrix())

    def add_line_callback(self, plot, data_sources):
        def callback(ev):
            data = json.loads(ev.data)
            model = data['model']
            experiment = data['experiment']

            iteration, value = self.get_points(model, experiment)
            src = ColumnDataSource(dict(iteration=iteration, value=value))

            plot.line('iteration', 'value', source=src)
            if plot in data_sources:
                data_sources[plot].append((src, model, experiment))
            else:
                data_sources[plot] = [(src, model, experiment)]
        return callback

    def add_plot_callback(self, plots_layout, data_sources):
        def callback():
            plot = Figure(x_axis_type='linear', y_range=(0, 25),
                          y_axis_label='Temperature (Celsius)',
                          title="Sea Surface Temperature at 43.18, -70.43")
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
                for source, model, experiment in plot_properties:
                    new_data = {}
                    iteration, value = self.get_points(model, experiment)
                    len_diff = (len(iteration) -
                                len(source.data['iteration']))
                    if len_diff > 0:
                        new_data['iteration'] = iteration[-len_diff:]
                        new_data['value'] = value[-len_diff:]
                        source.stream(new_data)
            len_diff = (len(self.experiments) -
                        len(datastreams_source.data['model']))
            if len_diff > 0:
                new_data = {
                    'model':
                        [model for model, _ in self.experiments[-len_diff:]],
                    'experiment': [experiment for _, experiment
                                   in self.experiments[-len_diff:]]}
                datastreams_source.stream(new_data)
        return update_data

    def modify_doc(self, doc):
        data_sources = {}
        datastreams_source = ColumnDataSource(
            dict(model=[], experiment=[]))
        slider = Slider(start=0, end=30, value=0, step=1, title="Smoothing")
        # TODO: uncomment when smoothing is fixed
        #slider.on_change(
        #    'value', self.add_smoothing_callback(source_smooth, plot))

        columns = [
            TableColumn(field="model", title="Model"),
            TableColumn(field="experiment", title="Experiment")]
        data_table = DragDataTable(
            source=datastreams_source, columns=columns, width=400, height=280)

        # TODO: make interval configurable, add refresh button
        doc.add_periodic_callback(
            self.add_update_data_callback(data_sources, datastreams_source),
            6000)

        tools_layout = column(slider, data_table)
        add_plot_button = Button(label='Add Plot', button_type="success")
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

# TODO: make port configurable
PORT = 8080


flask_app = Flask(__name__)


data_container = DataContainer()
bokeh_app = Application(FunctionHandler(data_container.modify_doc))

io_loop = IOLoop.current()

server = Server({'/bkapp': bokeh_app}, io_loop=io_loop, 
                allow_websocket_origin=["localhost:{}".format(PORT)], port=PORT)

server.start()


@flask_app.route('/', methods=['GET'])
def bkapp_page():
    script = autoload_server(url='http://localhost:{}/bkapp'.format(PORT))
    return render_template("embed.html", script=script, template="Flask")


@flask_app.route('/add/<model>/<experiment>/<x>/<y>', methods=['GET'])
def add_data(model, experiment, x, y):
    new_data = dict(iteration=x, value=y, model=model, experiment=experiment)
    data_container.data_frame.loc[len(data_container.data_frame)] = new_data
    if (model, experiment) not in data_container.experiments:
        data_container.experiments.append((model, experiment))
    return "", 200


if __name__ == '__main__':
    from tornado.wsgi import WSGIContainer
    from tornado.web import FallbackHandler
    from bokeh.util.browser import view

    print('Start server on http://localhost:{}/'.format(PORT))

    server._tornado.add_handlers(
        r".*", 
        [("^(?!/bkapp|/static).*$", FallbackHandler, 
         dict(fallback=WSGIContainer(flask_app)))])

    io_loop.add_callback(view, "http://localhost:{}/".format(PORT))
    io_loop.start()
