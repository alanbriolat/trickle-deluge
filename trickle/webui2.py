from collections import OrderedDict

from twisted.internet import reactor, defer
from twisted.web import server, resource, static

from deluge.ui.client import client as deluge
from deluge.ui.web.server import Tracker

from trickle.templating import Environment


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


class Root(resource.Resource):
    #isLeaf = True

    def __init__(self):
        resource.Resource.__init__(self)
        #self.putChild('static', static.File('./static'))
        #self.putChild('torrent', Torrent())
        #self.putChild('trackericon', Tracker())

    def getChild(self, name, req):
        if name == '':
            return self
        return request.Request.getChild(self, name, req)

    def render_GET(self, request):
        context = create_context(view_state='All')
        d = get_session_info(context)
        filter_dict = {}
        d.addCallback(get_torrents, filter_dict, SORT_FUNCTIONS[DEFAULT_SORT])
        d.addCallback(show_torrents)
        d.addCallback(request.write)
        d.addCallback(lambda x: request.finish())
        return server.NOT_DONE_YET


class Torrent(resource.Resource):
    pass


def get_torrent(info, hash):
    """Get the information for the torrent identified by *hash* and add it to
    *info*.

    Returns a :class:`Deferred` that fires with an updated *info* dict.
    """
    def got_torrent(torrent):
        info['torrent'] = torrent
        return info

    d = deluge.core.get_torrent_status(torrent_id=hash,
                                       keys=TORRENT_STATUS_KEYS)
    d.addCallback(got_torrent)
    return d


def get_torrents(info, filter_dict, sort):
    """Get torrent information and add it to *info*.

    Returns a :class:`Deferred` that fires with an updated *info* dict.
    """
    def got_torrents(torrents):
        torrents = sorted(torrents.values(),
                          key=sort['key'],
                          reverse=sort['reverse'])
        info['torrents'] = torrents
        return info

    d = deluge.core.get_torrents_status(filter_dict=filter_dict,
                                        keys=TORRENTS_STATUS_KEYS)
    d.addCallback(got_torrents)
    return d


def get_session_info(info):
    """Get session information and add it to *info*.

    Returns a :class:`Deferred` that fires with an updated *info* dict.
    """
    d = defer.Deferred()

    def got_session(session):
        info['session'] = session

    def got_filters(filters):
        info['filters'] = filters

    def on_complete(result):
        d.callback(info)

    d1 = deluge.core.get_session_status(keys=SESSION_STATUS_KEYS)
    d1.addCallback(got_session)

    d2 = deluge.core.get_filter_tree()
    d2.addCallback(got_filters)

    dl = defer.DeferredList([d1, d2])
    dl.addCallback(on_complete)

    return d


def show_torrents(context):
    context['title'] = context['view_state']
    template = tpl.get_template('index.html')
    return template.render(context).encode('utf-8')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('port', type=int)
    parser.add_argument('user')
    parser.add_argument('password')
    args = parser.parse_args()

    deluge.connect(args.host, args.port, args.user, args.password)

    root = Root()
    root.putChild('static', static.File('./static'))
    site = server.Site(root)
    reactor.listenTCP(8809, site)
    reactor.run()
