import jinja2


class Environment(jinja2.Environment):
    def __init__(self, template_dir):
        jinja2.Environment.__init__(self,
                loader=jinja2.FileSystemLoader(template_dir),
                extensions=('jinja2.ext.autoescape',),
                autoescape=True)

        # Enable if using the Twitter Bootstrap fluid grid (instead of static)
        #self.globals['fluid'] = '-fluid'

        self.filters['format_unix_epoch'] = format_unix_epoch
        # TODO: remove this when a new version of Jinja2 is released - this is
        # currently using a copy of the latest code for this filter to work
        # around the fact that in Jinja 2.6 it's completely broken.
        self.filters['filesizeformat'] = do_filesizeformat


def format_unix_epoch(value, format):
    import datetime
    dt = datetime.datetime.fromtimestamp(value)
    return dt.strftime(format)


def do_filesizeformat(value, binary=False):
    """Format the value like a 'human-readable' file size (i.e. 13 kB,
    4.1 MB, 102 Bytes, etc).  Per default decimal prefixes are used (Mega,
    Giga, etc.), if the second parameter is set to `True` the binary
    prefixes are used (Mebi, Gibi).
    """
    bytes = float(value)
    base = binary and 1024 or 1000
    prefixes = [
        (binary and 'KiB' or 'kB'),
        (binary and 'MiB' or 'MB'),
        (binary and 'GiB' or 'GB'),
        (binary and 'TiB' or 'TB'),
        (binary and 'PiB' or 'PB'),
        (binary and 'EiB' or 'EB'),
        (binary and 'ZiB' or 'ZB'),
        (binary and 'YiB' or 'YB')
    ]
    if bytes == 1:
        return '1 Byte'
    elif bytes < base:
        return '%d Bytes' % bytes
    else:
        for i, prefix in enumerate(prefixes):
            unit = base ** (i + 2)
            if bytes < unit:
                return '%.1f %s' % ((base * bytes / unit), prefix)
        return '%.1f %s' % ((base * bytes / unit), prefix)
