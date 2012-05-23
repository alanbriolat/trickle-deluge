from twisted.web import server, resource, static

from deluge.ui.web.server import Tracker as DelugeTrackerIcon

import trickle.client as client


class WebUIResource(resource.Resource):
    def __init__(self, ui):
        resource.Resource.__init__(self)
        self.ui = ui


def first_arg_value(request, arg, default):
    values = filter(id, request.args.get(arg, [])) + [default]
    return values[0]


class TorrentIndex(WebUIResource):
    """Top level resource: torrent list.
    """

    def getChild(self, path, request):
        """Allow this node to sit at the root but still be renderable.

        :meth:`getChild` is always called for the top-level resource, so this
        allows the top-level resource to have its own content *and* have
        children.  A request for ``/`` will result in an empty *path*.
        """
        if path == '':
            return self
        else:
            return resource.Resource.getChild(self, path, request)

    def render_GET(self, request):
        print request.args
        filter_dict = {
                'state': first_arg_value(request, 'state', 'All'),
                'tracker_host': first_arg_value(request, 'tracker', 'All'),
        }

        sort_method = first_arg_value(request, 'sort', 'added_desc')
        sort = client.SORT_FUNCTIONS[sort_method]

        context = client.create_context({
                'filter_state': filter_dict['state'],
                'filter_tracker': filter_dict['tracker_host'],
                'sort_method': sort_method,
        })

        d = client.collect(client.add_context(context),
                           client.get_session_info(),
                           client.get_torrents(filter_dict, sort))
        d.addCallback(self.ui.show_torrents, request)
        return server.NOT_DONE_YET


class ShowTorrentRoot(WebUIResource):
    """A virtual directory resource for viewing individual torrents.
    """

    def getChild(self, path, request):
        """Direct children of this resource are individual torrents.
        """
        return ShowTorrent(self.ui, path)


class ShowTorrent(WebUIResource):
    isLeaf = True

    def __init__(self, ui, torrent_hash):
        WebUIResource.__init__(self, ui)
        self.torrent_hash = torrent_hash

    def render_GET(self, request):
        context = client.create_context()
        d = client.collect(client.add_context(context),
                           client.get_session_info(),
                           client.get_torrent(self.torrent_hash))
        d.addCallback(self.ui.show_torrent, request)
        return server.NOT_DONE_YET


class TrackerList(WebUIResource):
    isLeaf = True

    def render_GET(self, request):
        context = client.create_context()
        d = client.collect(client.add_context(context),
                           client.get_session_info())
        d.addCallback(self.ui.show_trackers, request)
        return server.NOT_DONE_YET


def build_resource_tree(root, resources):
    """A recursive shortcut for assembling a resource tree.
    """
    for name in resources.iterkeys():
        root.putChild(name, build_resource_tree(*resources[name]))
    return root


class Site(server.Site):
    def __init__(self, ui):
        self.webui = ui
        self.toplevel = build_resource_tree(TorrentIndex(ui), {
            'static': (static.File('static'), {
                'theme': (static.File('themes/default'), {}),
            }),
            'trackericon': (DelugeTrackerIcon(), {}),
            'torrent': (ShowTorrentRoot(ui), {}),
            'trackers': (TrackerList(ui), {}),
        })

        server.Site.__init__(self, self.toplevel)
