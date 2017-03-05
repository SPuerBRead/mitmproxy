import argparse
import os

from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import platform
from mitmproxy.utils import human
from mitmproxy.net import tcp
from mitmproxy import version
from mitmproxy.addons import view


CONFIG_PATH = os.path.join(options.CA_DIR, "config.yaml")


class ParseException(Exception):
    pass


def get_common_options(args):
    stickycookie, stickyauth = None, None
    if args.stickycookie_filt:
        stickycookie = args.stickycookie_filt

    if args.stickyauth_filt:
        stickyauth = args.stickyauth_filt

    stream_large_bodies = args.stream_large_bodies
    if stream_large_bodies:
        stream_large_bodies = human.parse_size(stream_large_bodies)

    if args.streamfile and args.streamfile[0] == args.rfile:
        if args.streamfile[1] == "wb":
            raise exceptions.OptionsError(
                "Cannot use '{}' for both reading and writing flows. "
                "Are you looking for --afile?".format(args.rfile)
            )
        else:
            raise exceptions.OptionsError(
                "Cannot use '{}' for both reading and appending flows. "
                "That would trigger an infinite loop."
            )

    # Proxy config
    certs = []
    for i in args.certs or []:
        parts = i.split("=", 1)
        if len(parts) == 1:
            parts = ["*", parts[0]]
        certs.append(parts)

    body_size_limit = args.body_size_limit
    if body_size_limit:
        try:
            body_size_limit = human.parse_size(body_size_limit)
        except ValueError as e:
            raise exceptions.OptionsError(
                "Invalid body size limit specification: %s" % body_size_limit
            )

    # Establish proxy mode
    c = 0
    mode, upstream_server = "regular", None
    if args.transparent_proxy:
        c += 1
        if not platform.original_addr:
            raise exceptions.OptionsError(
                "Transparent mode not supported on this platform."
            )
        mode = "transparent"
    if args.socks_proxy:
        c += 1
        mode = "socks5"
    if args.reverse_proxy:
        c += 1
        mode = "reverse"
        upstream_server = args.reverse_proxy
    if args.upstream_proxy:
        c += 1
        mode = "upstream"
        upstream_server = args.upstream_proxy
    if c > 1:
        raise exceptions.OptionsError(
            "Transparent, SOCKS5, reverse and upstream proxy mode "
            "are mutually exclusive. Read the docs on proxy modes "
            "to understand why."
        )
    if args.add_upstream_certs_to_client_chain and not args.upstream_cert:
        raise exceptions.OptionsError(
            "The no-upstream-cert and add-upstream-certs-to-client-chain "
            "options are mutually exclusive. If no-upstream-cert is enabled "
            "then the upstream certificate is not retrieved before generating "
            "the client certificate chain."
        )

    if args.quiet:
        args.verbose = 0

    return dict(
        onboarding=args.onboarding,
        onboarding_host=args.onboarding_host,
        onboarding_port=args.onboarding_port,

        anticache=args.anticache,
        anticomp=args.anticomp,
        client_replay=args.client_replay,
        replay_kill_extra=args.replay_kill_extra,
        no_server=args.no_server,
        refresh_server_playback=args.refresh_server_playback,
        server_replay_use_headers=args.server_replay_use_headers,
        rfile=args.rfile,
        replacements=args.replacements,
        replacement_files=args.replacement_files,
        setheaders=args.setheaders,
        keep_host_header=args.keep_host_header,
        server_replay=args.server_replay,
        scripts=args.scripts,
        stickycookie=stickycookie,
        stickyauth=stickyauth,
        stream_large_bodies=stream_large_bodies,
        showhost=args.showhost,
        streamfile=args.streamfile[0] if args.streamfile else None,
        streamfile_append=True if args.streamfile and args.streamfile[1] == "a" else False,
        verbosity=args.verbose,
        server_replay_nopop=args.server_replay_nopop,
        server_replay_ignore_content=args.server_replay_ignore_content,
        server_replay_ignore_params=args.server_replay_ignore_params,
        server_replay_ignore_payload_params=args.server_replay_ignore_payload_params,
        server_replay_ignore_host=args.server_replay_ignore_host,

        auth_nonanonymous = args.auth_nonanonymous,
        auth_singleuser = args.auth_singleuser,
        auth_htpasswd = args.auth_htpasswd,
        add_upstream_certs_to_client_chain = args.add_upstream_certs_to_client_chain,
        body_size_limit = body_size_limit,
        cadir = args.cadir,
        certs = certs,
        ciphers_client = args.ciphers_client,
        ciphers_server = args.ciphers_server,
        clientcerts = args.clientcerts,
        ignore_hosts = args.ignore_hosts,
        listen_host = args.addr,
        listen_port = args.port,
        upstream_bind_address = args.upstream_bind_address,
        mode = mode,
        upstream_cert = args.upstream_cert,
        spoof_source_address = args.spoof_source_address,

        http2 = args.http2,
        http2_priority = args.http2_priority,
        websocket = args.websocket,
        rawtcp = args.rawtcp,

        upstream_server = upstream_server,
        upstream_auth = args.upstream_auth,
        ssl_version_client = args.ssl_version_client,
        ssl_version_server = args.ssl_version_server,
        ssl_insecure = args.ssl_insecure,
        ssl_verify_upstream_trusted_cadir = args.ssl_verify_upstream_trusted_cadir,
        ssl_verify_upstream_trusted_ca = args.ssl_verify_upstream_trusted_ca,
        tcp_hosts = args.tcp_hosts,
    )


def basic_options(parser, opts):
    parser.add_argument(
        '--version',
        action='store_true',
        dest='version',
    )
    parser.add_argument(
        '--shortversion',
        action='version',
        help="show program's short version number and exit",
        version=version.VERSION
    )
    opts.make_parser(parser, "anticache")
    parser.add_argument(
        "--cadir",
        action="store", type=str, dest="cadir",
        help="Location of the default mitmproxy CA files. (%s)" % options.CA_DIR
    )
    opts.make_parser(parser, "showhost")
    parser.add_argument(
        "-q", "--quiet",
        action="store_true", dest="quiet",
        help="Quiet."
    )
    parser.add_argument(
        "-r", "--read-flows",
        action="store", dest="rfile",
        help="Read flows from file."
    )
    parser.add_argument(
        "-s", "--script",
        action="append", type=str, dest="scripts",
        metavar='"script.py --bar"',
        help="""
            Run a script. Surround with quotes to pass script arguments. Can be
            passed multiple times.
        """
    )
    parser.add_argument(
        "-t", "--stickycookie",
        action="store",
        dest="stickycookie_filt",
        metavar="FILTER",
        help="Set sticky cookie filter. Matched against requests."
    )
    parser.add_argument(
        "-u", "--stickyauth",
        action="store", dest="stickyauth_filt", metavar="FILTER",
        help="Set sticky auth filter. Matched against requests."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_const", dest="verbose", const=3,
        help="Increase log verbosity."
    )
    streamfile = parser.add_mutually_exclusive_group()
    streamfile.add_argument(
        "-w", "--wfile",
        action="store", dest="streamfile", type=lambda f: (f, "w"),
        help="Write flows to file."
    )
    streamfile.add_argument(
        "-a", "--afile",
        action="store", dest="streamfile", type=lambda f: (f, "a"),
        help="Append flows to file."
    )
    opts.make_parser(parser, "anticomp")
    parser.add_argument(
        "-Z", "--body-size-limit",
        action="store", dest="body_size_limit",
        metavar="SIZE",
        help="Byte size limit of HTTP request and response bodies."
             " Understands k/m/g suffixes, i.e. 3m for 3 megabytes."
    )
    parser.add_argument(
        "--stream",
        action="store", dest="stream_large_bodies",
        metavar="SIZE",
        help="""
            Stream data to the client if response body exceeds the given
            threshold. If streamed, the body will not be stored in any way.
            Understands k/m/g suffixes, i.e. 3m for 3 megabytes.
         """
    )


def proxy_modes(parser, opts):
    group = parser.add_argument_group("Proxy Modes")
    group.add_argument(
        "-R", "--reverse",
        action="store",
        type=str,
        dest="reverse_proxy",
        help="""
            Forward all requests to upstream HTTP server:
            http[s]://host[:port]. Clients can always connect both
            via HTTPS and HTTP, the connection to the server is
            determined by the specified scheme.
        """
    )
    group.add_argument(
        "--socks",
        action="store_true", dest="socks_proxy",
        help="Set SOCKS5 proxy mode."
    )
    group.add_argument(
        "-T", "--transparent",
        action="store_true", dest="transparent_proxy",
        help="Set transparent proxy mode."
    )
    group.add_argument(
        "-U", "--upstream",
        action="store",
        type=str,
        dest="upstream_proxy",
        help="Forward all requests to upstream proxy server: http://host[:port]"
    )


def proxy_options(parser, opts):
    group = parser.add_argument_group("Proxy Options")
    group.add_argument(
        "-b", "--bind-address",
        action="store", type=str, dest="addr",
        help="Address to bind proxy to (defaults to all interfaces)"
    )
    group.add_argument(
        "-I", "--ignore",
        action="append", type=str, dest="ignore_hosts",
        metavar="HOST",
        help="""
            Ignore host and forward all traffic without processing it. In
            transparent mode, it is recommended to use an IP address (range),
            not the hostname. In regular mode, only SSL traffic is ignored and
            the hostname should be used. The supplied value is interpreted as a
            regular expression and matched on the ip or the hostname. Can be
            passed multiple times.
        """
    )
    group.add_argument(
        "--tcp",
        action="append", type=str, dest="tcp_hosts",
        metavar="HOST",
        help="""
            Generic TCP SSL proxy mode for all hosts that match the pattern.
            Similar to --ignore, but SSL connections are intercepted. The
            communication contents are printed to the log in verbose mode.
        """
    )
    opts.make_parser(group, "no_server")
    group.add_argument(
        "-p", "--port",
        action="store", type=int, dest="port",
        help="Proxy service port."
    )

    http2 = group.add_mutually_exclusive_group()
    opts.make_parser(http2, "http2")
    opts.make_parser(http2, "http2_priority")

    websocket = group.add_mutually_exclusive_group()
    opts.make_parser(websocket, "websocket")

    parser.add_argument(
        "--upstream-auth",
        action="store", dest="upstream_auth",
        type=str,
        help="""
            Add HTTP Basic authentcation to upstream proxy and reverse proxy
            requests. Format: username:password
        """
    )

    opts.make_parser(group, "rawtcp")

    opts.make_parser(group, "spoof_source_address")
    group.add_argument(
        "--upstream-bind-address",
        action="store", type=str, dest="upstream_bind_address",
        help="Address to bind upstream requests to (defaults to none)"
    )
    opts.make_parser(group, "keep_host_header")


def proxy_ssl_options(parser, opts):
    # TODO: Agree to consistently either use "upstream" or "server".
    group = parser.add_argument_group("SSL")
    group.add_argument(
        "--cert",
        dest='certs',
        type=str,
        metavar="SPEC",
        action="append",
        help='Add an SSL certificate. SPEC is of the form "[domain=]path". '
             'The domain may include a wildcard, and is equal to "*" if not specified. '
             'The file at path is a certificate in PEM format. If a private key is included '
             'in the PEM, it is used, else the default key in the conf dir is used. '
             'The PEM file should contain the full certificate chain, with the leaf certificate '
             'as the first entry. Can be passed multiple times.')
    group.add_argument(
        "--ciphers-client", action="store",
        type=str, dest="ciphers_client",
        help="Set supported ciphers for client connections. (OpenSSL Syntax)"
    )
    group.add_argument(
        "--ciphers-server", action="store",
        type=str, dest="ciphers_server",
        help="Set supported ciphers for server connections. (OpenSSL Syntax)"
    )
    group.add_argument(
        "--client-certs", action="store",
        type=str, dest="clientcerts",
        help="Client certificate file or directory."
    )
    opts.make_parser(group, "upstream_cert")
    opts.make_parser(group, "add_upstream_certs_to_client_chain")
    opts.make_parser(group, "ssl_insecure")
    group.add_argument(
        "--upstream-trusted-cadir", action="store",
        dest="ssl_verify_upstream_trusted_cadir",
        help="Path to a directory of trusted CA certificates for upstream "
             "server verification prepared using the c_rehash tool."
    )
    group.add_argument(
        "--upstream-trusted-ca", action="store",
        dest="ssl_verify_upstream_trusted_ca",
        help="Path to a PEM formatted trusted CA certificate."
    )
    group.add_argument(
        "--ssl-version-client", dest="ssl_version_client",
        action="store",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions for client connections. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )
    group.add_argument(
        "--ssl-version-server", dest="ssl_version_server",
        action="store",
        choices=tcp.sslversion_choices.keys(),
        help="Set supported SSL/TLS versions for server connections. "
             "SSLv2, SSLv3 and 'all' are INSECURE. Defaults to secure, which is TLS1.0+."
    )


def onboarding_app(parser, opts):
    group = parser.add_argument_group("Onboarding App")
    opts.make_parser(parser, "onboarding")
    group.add_argument(
        "--onboarding-host",
        action="store", dest="onboarding_host",
        help="""
            Domain to serve the onboarding app from. For transparent mode, use
            an IP when a DNS entry for the app domain is not present. Default:
            %s
        """ % options.APP_HOST
    )
    group.add_argument(
        "--onboarding-port",
        action="store",
        dest="onboarding_port",
        type=int,
        metavar="80",
        help="Port to serve the onboarding app from."
    )


def client_replay(parser, opts):
    group = parser.add_argument_group("Client Replay")
    group.add_argument(
        "-c", "--client-replay",
        action="append", dest="client_replay", metavar="PATH",
        help="Replay client requests from a saved file."
    )


def server_replay(parser, opts):
    group = parser.add_argument_group("Server Replay")
    group.add_argument(
        "-S", "--server-replay",
        action="append", dest="server_replay", metavar="PATH",
        help="Replay server responses from a saved file."
    )
    opts.make_parser(parser, "replay_kill_extra")
    group.add_argument(
        "--server-replay-use-header",
        action="append", dest="server_replay_use_headers", type=str,
        help="Request headers to be considered during replay. "
             "Can be passed multiple times."
    )
    opts.make_parser(group, "refresh_server_playback")
    opts.make_parser(group, "server_replay_nopop")
    payload = group.add_mutually_exclusive_group()
    opts.make_parser(payload, "server_replay_ignore_content")
    payload.add_argument(
        "--replay-ignore-payload-param",
        action="append", dest="server_replay_ignore_payload_params", type=str,
        help="""
            Request's payload parameters (application/x-www-form-urlencoded or multipart/form-data) to
            be ignored while searching for a saved flow to replay.
            Can be passed multiple times.
        """
    )

    group.add_argument(
        "--replay-ignore-param",
        action="append", dest="server_replay_ignore_params", type=str,
        help="""
            Request's parameters to be ignored while searching for a saved flow
            to replay. Can be passed multiple times.
        """
    )
    opts.make_parser(parser, "server_replay_ignore_host")


def replacements(parser, opts):
    group = parser.add_argument_group(
        "Replacements",
        """
            Replacements are of the form "/pattern/regex/replacement", where
            the separator can be any character. Please see the documentation
            for more information.
        """.strip()
    )
    group.add_argument(
        "--replace",
        action="append", type=str, dest="replacements",
        metavar="PATTERN",
        help="Replacement pattern."
    )
    group.add_argument(
        "--replace-from-file",
        action="append", type=str, dest="replacement_files",
        metavar="PATH",
        help="""
            Replacement pattern, where the replacement clause is a path to a
            file.
        """
    )


def set_headers(parser, opts):
    group = parser.add_argument_group(
        "Set Headers",
        """
            Header specifications are of the form "/pattern/header/value",
            where the separator can be any character. Please see the
            documentation for more information.
        """.strip()
    )
    group.add_argument(
        "--setheader",
        action="append", type=str, dest="setheaders",
        metavar="PATTERN",
        help="Header set pattern."
    )


def proxy_authentication(parser, opts):
    group = parser.add_argument_group(
        "Proxy Authentication",
        """
            Specify which users are allowed to access the proxy and the method
            used for authenticating them.
        """
    ).add_mutually_exclusive_group()
    opts.make_parser(group, "auth_nonanonymous")
    group.add_argument(
        "--singleuser",
        action="store", dest="auth_singleuser", type=str,
        metavar="USER",
        help="""
            Allows access to a a single user, specified in the form
            username:password.
        """
    )
    group.add_argument(
        "--htpasswd",
        action="store", dest="auth_htpasswd", type=str,
        metavar="PATH",
        help="Allow access to users specified in an Apache htpasswd file."
    )


def common_options(parser, opts):
    parser.add_argument(
        "--conf",
        type=str, dest="conf", default=CONFIG_PATH,
        metavar="PATH",
        help="""
            Configuration file
        """
    )
    basic_options(parser, opts)
    proxy_modes(parser, opts)
    proxy_options(parser, opts)
    proxy_ssl_options(parser, opts)
    onboarding_app(parser, opts)
    client_replay(parser, opts)
    server_replay(parser, opts)
    replacements(parser, opts)
    set_headers(parser, opts)
    proxy_authentication(parser, opts)


def mitmproxy(opts):
    # Don't import mitmproxy.tools.console for mitmdump, urwid is not available
    # on all platforms.
    from .console import palettes

    parser = argparse.ArgumentParser(usage="%(prog)s [options]")
    common_options(parser, opts)
    parser.add_argument(
        "--palette", type=str,
        action="store", dest="console_palette",
        choices=sorted(palettes.palettes.keys()),
        help="Select color palette: " + ", ".join(palettes.palettes.keys())
    )
    opts.make_parser(parser, "console_palette_transparent")
    opts.make_parser(parser, "console_eventlog")
    opts.make_parser(parser, "console_focus_follow")
    parser.add_argument(
        "--order",
        type=str, dest="console_order",
        choices=[o[1] for o in view.orders],
        help="Flow sort order."
    )
    opts.make_parser(parser, "console_mouse")
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    group.add_argument(
        "-i", "--intercept", action="store",
        type=str, dest="intercept",
        help="Intercept filter expression."
    )
    group.add_argument(
        "-f", "--filter", action="store",
        type=str, dest="filter",
        help="Filter view expression."
    )
    return parser


def mitmdump(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options] [filter]")

    common_options(parser, opts)
    opts.make_parser(parser, "keepserving")
    parser.add_argument(
        "-d", "--detail",
        action="count", dest="flow_detail",
        help="Increase flow detail display level. Can be passed multiple times."
    )
    parser.add_argument(
        'filter',
        nargs="...",
        help="""
            Filter view expression, used to only show flows that match a certain filter.
            See help in mitmproxy for filter expression syntax.
        """
    )
    return parser


def mitmweb(opts):
    parser = argparse.ArgumentParser(usage="%(prog)s [options]")

    group = parser.add_argument_group("Mitmweb")
    opts.make_parser(group, "web_open_browser")
    group.add_argument(
        "--web-port",
        action="store", type=int, dest="web_port",
        metavar="PORT",
        help="Mitmweb port."
    )
    group.add_argument(
        "--web-iface",
        action="store", dest="web_iface",
        metavar="IFACE",
        help="Mitmweb interface."
    )
    opts.make_parser(group, "web_debug")

    common_options(parser, opts)
    group = parser.add_argument_group(
        "Filters",
        "See help in mitmproxy for filter expression syntax."
    )
    group.add_argument(
        "-i", "--intercept", action="store",
        type=str, dest="intercept",
        help="Intercept filter expression."
    )
    return parser
