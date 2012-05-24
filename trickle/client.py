"""
Wrapper functions for interacting with the Deluge client.

The Deluge client library doesn't lend itself to being isolated and
encapsulated, so all the helpers for interacting with Deluge are just functions
that make use of the global Deluge client object, in the same way all the other
Deluge UIs do.

Most of these functions make API calls to Deluge and return :class:`Deferred`s
that fire with dicts containing the requested information.
"""

from collections import OrderedDict

from twisted.internet import defer

from deluge.ui.client import client as deluge


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


def create_context(extra={}):
    """Create a default context, updated with *extra*.
    """
    context = {
            'sort_methods': SORT_FUNCTIONS,
    }
    context.update(extra)
    return context


def result_to_dict(result, key):
    """Turn *result* into a single-key dict.

    This is mainly useful as a :class:`Deferred` callback used in combination
    with :func:`merge_results`.
    """
    return {key: result}


def merge_results(results):
    """Turn *results*, an iterable of ``(success, dict)``, into a single dict.

    This is mainly useful as a :class:`DeferredList` callback to merge results
    from several different calls.
    """
    result = {}
    [result.update(d) for s, d in results if s is True]
    return result


def add_context(context):
    """Create a :class:`Deferred` that yields *context* immediately.

    This is a convenience method for use with :func:`collect` to allow a
    API results and constant context data to be merged together.
    """
    d = defer.Deferred()
    d.callback(context)
    return d


def collect(*deferreds):
    """A convenience function for collecting API call results.
    
    Takes any number of :class:`Deferred`s that are expected to result in a
    dict and wraps them in a :class:`DeferredList` that applies
    :func:`merge_results`.
    """
    dl = defer.DeferredList(deferreds)
    dl.addCallback(merge_results)
    return dl


def get_session_info():
    """Retrieve session information.

    Returns a :class:`Deferred` that fires with a dict containing the *session*
    and *filters* keys.
    """
    d1 = deluge.core.get_session_status(keys=[
        'payload_upload_rate',
        'payload_download_rate',
    ])
    d1.addCallback(result_to_dict, 'session')

    d2 = deluge.core.get_filter_tree()
    d2.addCallback(result_to_dict, 'filters')

    dl = defer.DeferredList([d1, d2])
    dl.addCallback(merge_results)
    return dl


def get_torrents(filter_dict, sort):
    """Retrieve torrent information for many torrents.

    Returns a :class:`Deferred` that fires with a dict containing the
    *torrents* key.  The torrents will be filtered by *filter_dict* and sorted
    by *sort*.

    .. seealso:: :data:`SORT_FUNCTIONS`
    """
    # Sanitise filter_dict a bit
    filters = filter_dict.copy()
    if 'state' in filters and filters['state'] in ('', 'All'):
        del filters['state']
    if 'tracker_host' in filters and filters['tracker_host'] in ('', 'All'):
        del filters['tracker_host']

    print filter_dict
    print filters

    def got_torrents(torrents):
        return {'torrents': sorted(torrents.values(),
                                   key=sort['key'],
                                   reverse=sort['reverse'])}

    # keys=[] returns *all* torrent information
    d = deluge.core.get_torrents_status(filter_dict=filters, keys=[])
    d.addCallback(got_torrents)
    return d


def get_torrent(hash):
    """Retrieve information about a single torrent.

    Returns a :class:`Deferred` that fires with a dict containing the *torrent*
    key.
    """
    # keys=[] returns *all* torrent information
    d = deluge.core.get_torrent_status(torrent_id=hash, keys=[])
    d.addCallback(result_to_dict, 'torrent')
    return d
