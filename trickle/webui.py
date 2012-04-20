from twisted.internet import defer
from twisted.web.static import File
from klein import Klein
from deluge.ui.client import client as deluge

from trickle.templating import Environment


app = Klein()
tpl = Environment('templates')


SESSION_STATUS_KEYS = [
        'payload_upload_rate',
        'payload_download_rate',
]

TORRENTS_STATUS_KEYS = []

TORRENT_STATUS_KEYS = []


@app.route('/static/')
def static(request):
    return File('./static')


@app.route('/')
def index(request):
    torrents = deluge.core.get_torrents_status(filter_dict={},
                                               keys=TORRENTS_STATUS_KEYS)
    session = deluge.core.get_session_status(keys=SESSION_STATUS_KEYS)
    d = defer.gatherResults([torrents, session])
    d.addCallback(show_torrents, context={
        'title': 'All torrents',
    })
    return d


@app.route('/torrent/<hash>')
def torrent(request, hash):
    torrent = deluge.core.get_torrent_status(torrent_id=hash,
                                             keys=TORRENT_STATUS_KEYS)
    session = deluge.core.get_session_status(keys=SESSION_STATUS_KEYS)
    d = defer.gatherResults([torrent, session])
    d.addCallback(show_torrent, context={})
    return d


def show_torrents(results, context):
    torrents, session = results
    context.update({
        'torrents': torrents.values(),
        'session': session,
    })
    template = tpl.get_template('index.html')
    return template.render(context)


def show_torrent(results, context):
    torrent, session = results
    context.update({
        'torrent': torrent,
        'session': session,
        'title': torrent['name'],
    })
    template = tpl.get_template('torrent.html')
    return template.render(context)


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
