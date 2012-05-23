from collections import OrderedDict

from twisted.internet import reactor, defer
from twisted.web import server, resource, static

from deluge.ui.client import client as deluge
from deluge.ui.web.server import Tracker

from trickle.templating import Environment
from trickle.server import Site


tpl = Environment('templates')


SESSION_STATUS_KEYS = [
        'payload_upload_rate',
        'payload_download_rate',
]

TORRENTS_STATUS_KEYS = []

TORRENT_STATUS_KEYS = []

#: Available sort keys
SORT_FUNCTIONS = OrderedDict()
SORT_FUNCTIONS['added_desc'] = {
        'key': lambda t: t['time_added'],
        'reverse': True,
        'description': 'date added, newest first',
}
SORT_FUNCTIONS['added_asc'] = {
        'key': lambda t: t['time_added'],
        'reverse': False,
        'description': 'date added, oldest first',
}

DEFAULT_SORT = 'added_desc'


def create_context(**extra):
    context = {
        'available_sorts': [(k, f['description'])
                            for k, f in SORT_FUNCTIONS.iteritems()],
    }
    context.update(extra)
    return context


def show_torrents(context):
    context['title'] = context.get('current_filter', {}).get('state', 'All')
    template = tpl.get_template('index.html')
    return template.render(context).encode('utf-8')


class WebUI(object):
    def __init__(self):
        self.site = Site(self)
        self.tpl = Environment('templates')

    def render_to_request(self, template, context, request, finish=True):
        template = self.tpl.get_template(template)
        request.write(template.render(context).encode('utf-8'))
        if finish:
            request.finish()

    def show_torrents(self, context, request):
        context['title'] = context['filter_state']
        self.render_to_request('index.html', context, request)

    def show_torrent(self, context, request):
        context['title'] = context['torrent']['name']
        self.render_to_request('torrent.html', context, request)

    def show_trackers(self, context, request):
        self.render_to_request('trackers.html', context, request)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='localhost',
                        help='deluged host [default: %(default)s]')
    parser.add_argument('--port', '-p', type=int, default=58846,
                        help='deluged port [default: %(default)s]')
    parser.add_argument('user')
    parser.add_argument('password')
    args = parser.parse_args()

    deluge.connect(args.host, args.port, args.user, args.password)

    webui = WebUI()

    reactor.listenTCP(8809, webui.site)
    reactor.run()
