import requests


class Stream(object):
    def __init__(self, experiment_name, host='localhost', port=8080):
        self.experiment_name = experiment_name
        self.host = host
        self.port = port

    def send(self, variable_name, iteration, value):
        send_value(self.experiment_name, variable_name, iteration, value, self.host, self.port)


def send_value(experiment_name, variable_name, iteration, value, host='localhost', port=8080):
    r = requests.get('http://{}:{}/add/{}/{}/{}/{}'.format(
        host, port, experiment_name, variable_name, iteration, value))
    if r.status_code != 200:
        raise requests.RequestException
