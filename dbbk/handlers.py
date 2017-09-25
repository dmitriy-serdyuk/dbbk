from concurrent.futures import ThreadPoolExecutor

from tornado import gen
from tornado.web import RequestHandler
from bokeh.client import pull_session
from bokeh.embed import server_session

from .utils import render


class MainHandler(RequestHandler):
    default_path = r"/"

    def initialize(self, port):
        self.thread_pool = ThreadPoolExecutor(4)
        self.port = port

    @gen.coroutine
    def get_session(self):
        session = yield self.thread_pool.submit(
            pull_session, url='http://localhost:{}/bkapp'.format(self.port))
        return session

    @gen.coroutine
    def get(self):
        session = yield self.get_session()
        model = session.document.roots[0]
        script = server_session(
            model, session.id,
            url='http://localhost:{}/bkapp'.format(self.port))
        self.write(render("templates/embed.html", script=script, template="Flask"))
        self.finish()


class AddHandler(RequestHandler):
    default_path = r"/add/([^/]+)/([^/]+)/([^/]+)/([^/]+)"

    def initialize(self, data_container):
        self.data_container = data_container

    def get(self, model, variable, x, y):
        x = float(x)
        y = float(y)
        new_data = dict(iteration=x, value=y, model=model, variable=variable)
        self.data_container.data_frame.loc[len(self.data_container.data_frame)] = new_data
        if (model, variable) not in self.data_container.experiments:
            self.data_container.experiments.append((model, variable))
        self.write('ok')
        self.finish()