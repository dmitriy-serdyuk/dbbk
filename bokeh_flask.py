#!/usr/bin/env python
from __future__ import print_function

import argparse

from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.util.browser import view
from tornado.ioloop import IOLoop

from dbbk.data_container import DataContainer
from dbbk.handlers import MainHandler, AddHandler
from dbbk.utils import ExtendedServer


def main(host, port, open_browser):
    data_container = DataContainer()
    bokeh_app = Application(FunctionHandler(data_container.modify_doc))

    io_loop = IOLoop.current()

    server = ExtendedServer(
        {'/bkapp': bokeh_app}, io_loop=io_loop,
        allow_websocket_origin=["{}:{}".format(host, port)],
        port=port)

    server.start()

    print('Start server on http://{}:{}/'.format(host, port))

    server.add_handlers(
        r".*",
        [(MainHandler.default_path, MainHandler),
         (AddHandler.default_path, AddHandler, {'data_container': data_container}),
         ])

    if open_browser:
        io_loop.add_callback(view, "http://{}:{}/".format(host, port))
    io_loop.start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run dbbk server")
    
    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=int, default=8080)

    parser.add_argument('--open-browser', dest='open_browser', action='store_true')
    parser.add_argument('--no-open-browser', dest='open_browser', action='store_false')
    parser.set_defaults(open_browser=True)

    args = parser.parse_args()
    main(**args.__dict__)
