from twisted.web.static import File
from twisted.web.template import Element, XMLFile, renderer
from klein import Klein
from deluge.ui.client import client as deluge


app = Klein()


@app.route('/static/')
def static(request):
    return File('./static')


@app.route('/')
def home(request):
    #return deluge.core.get_torrents_status(filter_dict={}, keys=[]).addCallback(str)
    return deluge.core.get_torrents_status(filter_dict={}, keys=[]).addCallback(TheWholePage)


class TheWholePage(Element):
    loader = XMLFile('templates/index.html')

    def __init__(self, data):
        self._data = data

    @renderer
    def torrents(self, request, tag):
        for tid, torrent in self._data.iteritems():
            yield tag.clone().fillSlots(**{
                'hash': torrent['hash'],
                'name': torrent['name'],
                'upload_payload_rate': str(torrent['upload_payload_rate']),
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
