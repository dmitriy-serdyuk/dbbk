from os.path import split
from concurrent.futures import ThreadPoolExecutor

from tornado import gen
from tornado.web import RequestHandler, asynchronous
from bokeh.client import pull_session
from bokeh.embed import server_session

from .utils import render


class MainHandler(RequestHandler):
    default_path = r"/"

    def initialize(self, bokeh_server):
        self.thread_pool = ThreadPoolExecutor(2)
        self.bokeh_server = bokeh_server

    @gen.coroutine
    def get_session(self):
        session = yield self.thread_pool.submit(
            pull_session, url=self.bokeh_server)
        return session

    @gen.coroutine
    def get(self):
        session = yield self.get_session()
        root_model = session.document.roots[0]
        script = server_session(
            root_model, session.id,
            url=self.bokeh_server)
        self.write(render(split(__file__)[0] + "/templates/embed.html", script=script, template="Flask"))
        self.finish()


class AddHandler(RequestHandler):
    default_path = r"/add/([^/]+)/([^/]+)/([^/]+)/([^/]+)"

    def initialize(self, data_container):
        self.data_container = data_container

    @gen.coroutine
    def add_data(self, iteration, value, experiment, variable):
        self.data_container.add_data(iteration=iteration, value=value, experiment=experiment, variable=variable)

    @asynchronous
    @gen.engine
    def get(self, experiment, variable, x, y):
        x = float(x)
        y = float(y)
        self.add_data(iteration=x, value=y, experiment=experiment, variable=variable)
        self.write('ok')
        self.finish()
