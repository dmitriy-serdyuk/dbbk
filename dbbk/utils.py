import os

import jinja2
from bokeh.server.server import Server


class ExtendedServer(Server):
    def add_handlers(self, *args, **kwargs):
        self._tornado.add_handlers(*args, **kwargs)


def render(tpl_path, **context):
    path, filename = os.path.split(tpl_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)