from twisted.internet import defer
from twisted.web.static import File
from klein import Klein
from deluge.ui.client import client as deluge
import jinja2


app = Klein()
tpl = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))


SESSION_STATUS_KEYS = [
        'payload_upload_rate',
        'payload_download_rate',
]


@app.route('/static/')
def static(request):
    return File('./static')


@app.route('/')
def index(request):
    torrents = deluge.core.get_torrents_status(filter_dict={}, keys=[])
    session = deluge.core.get_session_status(keys=SESSION_STATUS_KEYS)
    d = defer.gatherResults([torrents, session])
    d.addCallback(show_torrents)
    return d


def show_torrents(results):
    torrents, session = results
    template = tpl.get_template('index.html')
    return template.render({
        'torrents': torrents.values(),
        'session': session,
    })


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('port', type=int)
    parser.add_argument('user')
    parser.add_argument('password')
    args = parser.parse_args()

    deluge.connect(args.host, args.port, args.user, args.password)
    app.run('localhost', 8808)
