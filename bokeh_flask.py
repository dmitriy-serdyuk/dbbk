from __future__ import print_function
import os
import os.path
from flask import Flask, render_template
import pandas
import yaml

from tornado.ioloop import IOLoop
from tornado import gen

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.embed import autoload_server
from bokeh.layouts import column, row
from bokeh.models import ColumnDataSource, Slider
from bokeh.models.plots import Plot
from bokeh.plotting import figure, Figure
from bokeh.server.server import Server
from bokeh.themes import Theme
from bokeh.plotting import curdoc
import numpy
from bokeh.models.widgets import DataTable, DateFormatter, TableColumn, Button
from bokeh.models import CustomJS
from bokeh.events import Event


class MyDataTable(DataTable):
    __implementation__ = 'my_data_table.coffee'


class MyPlot(Plot):
    __implementation__ = os.path.dirname(os.path.realpath(__file__)) + '/my_plot.coffee'


class AddLine(Event):
    event_name = 'add_line'
    def __init__(self, model, data):
        super(AddLine, self).__init__(model=model)
        self.data = data


from bokeh.model import MetaModel
del MetaModel.model_class_reverse_map['Figure']
Figure = type('Figure', (MyPlot, Figure), dict(Figure.__dict__))
Figure.__view_model__ = "MyPlot"


class DataContainer(object):
    data_url = ("http://www.neracoos.org/erddap/tabledap/B01_sbe37_all.csvp?"
                "time,temperature&depth=1&temperature_qc=0&time>=2016-02-15")
    
    def __init__(self):
        print('.. downloading data')
        #df = pandas.read_csv(self.data_url, parse_dates=['time'], 
        #                     names=['time', 'temperature'], 
        #                     dtype={'time': 'str', 'temperature': 'float64'},
        #                     skiprows=1)
        data = dict(time=[1, 2, 3, 4], 
                    temperature=[10, 15, 10, 12])
        df = pandas.DataFrame.from_dict(data, orient='columns')

        self.df = df
    
    def modify_doc(self, doc):
        source = ColumnDataSource(dict(time=self.df['time'].as_matrix(),
                                       temperature=self.df['temperature'].as_matrix()))
        doc.source = source
        source_smooth = ColumnDataSource(data=self.df)

        plot = Figure(x_axis_type='linear', y_range=(0, 25), 
                      y_axis_label='Temperature (Celsius)',
                      title="Sea Surface Temperature at 43.18, -70.43")
        plot.line('time', 'temperature', source=source, 
                  line_color='grey', alpha=0.5)
        plot.line('time', 'temperature', source=source_smooth, line_width=2.)

        plot.on_event(AddLine, lambda ev: print(80, ev.data))

        def callback(attr, old, new):
            if new == 0:
                data = self.df
            else:
                data = self.df.rolling(new).mean()
            source_smooth.data = ColumnDataSource(data=data).data

        slider = Slider(start=0, end=30, value=0, step=1, 
                        title="Smoothing by N Days")
        slider.on_change('value', callback)

        columns = [
                TableColumn(field="time", title="Date"),
                TableColumn(field="temperature", title="Downloads"),
                ]
        data_table = MyDataTable(source=source, columns=columns, 
                               width=400, height=280)
        #.js_on_change('tap', callback)
        #data_table.js_on_event('start', callback)
        #doc.add_next_tick_callback(callback)

        def update_data():
            new_data = {}
            need_update = False
            for key in self.df:
                len_diff = len(self.df[key]) - len(source.data[key])
                if len_diff > 0:
                    new_data[key] = self.df[key][-len_diff:]
                    need_update = True
                else:
                    new_data[key] = numpy.array([])
            if need_update:
                source.stream(new_data)
                slider.update()

        doc.add_periodic_callback(update_data, 60000)

        tools_layout = column(slider, data_table)
        add_plot_button = Button(label='press me', button_type="success")
        plots_layout = column(plot, add_plot_button)
        def add_plot_callback():
            plots_layout.children.append(Figure())
        add_plot_button.on_click(add_plot_callback)

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


@flask_app.route('/add/<name>/<x>/<y>', methods=['GET'])
def add_data(name, x, y):
    #x = numpy.datetime64('2016-02-15T00:00:00.000000000')
    new_data = dict(time=x, temperature=y)
    #data_container.df.append(pandas.DataFrame.from_dict(new_data))
    data_container.df.loc[len(data_container.df)] = new_data
    return "", 200


if __name__ == '__main__':
    from tornado.httpserver import HTTPServer
    from tornado.wsgi import WSGIContainer
    from tornado.web import FallbackHandler
    from bokeh.util.browser import view

    print('Opening Flask app with embedded Bokeh application on http://localhost:8080/')

    # This uses Tornado to server the WSGI app that flask provides. Presumably the IOLoop
    # could also be started in a thread, and Flask could server its own app directly
    server._tornado.add_handlers(
        r".*", 
        [("^(?!/bkapp|/static).*$", FallbackHandler, 
         dict(fallback=WSGIContainer(flask_app)))])

    io_loop.add_callback(view, "http://localhost:{}/".format(PORT))
    io_loop.start()
