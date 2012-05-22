from collections import OrderedDict

from twisted.internet import defer
from twisted.web import server, http
from twisted.web.static import File
from klein import Klein
from deluge.ui.client import client as deluge
from deluge.ui.tracker_icons import TrackerIcons

from trickle.templating import Environment


app = Klein()
tpl = Environment('templates')
trackericons = TrackerIcons('static/img/trackers')


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


@app.route('/static/')
def static(request):
    return File('./static')


@app.route('/')
def view_all(request):
    return view_by_state(request, 'All')


@app.route('/state/<state>')
def view_by_state(request, state):
    filter_dict = {}
    if state != 'All':
        filter_dict['state'] = state
    context = create_context(view_state=state)
    d = get_session_info(context)
    d.addCallback(get_torrents, filter_dict, SORT_FUNCTIONS[DEFAULT_SORT])
    d.addCallback(show_torrents)
    return d


@app.route('/torrent/<hash>')
def view_torrent(request, hash):
    context = create_context()
    d = get_session_info(context)
    d.addCallback(get_torrent, hash=hash)
    d.addCallback(show_torrent)
    return d


@app.route('/trackers/')
def view_trackers(request):
    context = create_context(page='trackers')
    d = get_session_info(context)
    d.addCallback(show_trackers)
    return d


@app.route('/trackericon/<tracker>')
def get_trackericon(request, tracker):
    """Based on ``deluge.ui.web.server.Tracker``.
    """
    def on_got_icon(icon, request):
        if icon:
            request.setHeader('cache-control',
                              'public, must-revalidate, max-age=86400')
            request.setHeader('content-type', icon.get_mimetype())
            request.write(icon.get_data())
            request.setResponseCode(http.OK)
            request.finish()
        else:
            request.setResponseCode(http.NOT_FOUND)
            request.finish()

    d = trackericons.get(tracker)
    d.addCallback(on_got_icon, request)
    return server.NOT_DONE_YET


def show_torrents(context):
    context['title'] = context['view_state']
    template = tpl.get_template('index.html')
    return template.render(context)


def show_torrent(context):
    context['title'] = context['torrent']['name']
    template = tpl.get_template('torrent.html')
    return template.render(context)


def show_trackers(context):
    template = tpl.get_template('trackers.html')
    return template.render(context)


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


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('port', type=int)
    parser.add_argument('user')
    parser.add_argument('password')
    args = parser.parse_args()

    deluge.connect(args.host, args.port, args.user, args.password)
    app.run('0.0.0.0', 8808)
