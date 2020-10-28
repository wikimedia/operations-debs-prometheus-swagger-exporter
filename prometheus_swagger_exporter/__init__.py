#!/usr/bin/env python

from gevent import monkey; monkey.patch_all()  # noqa
import gevent
from bottle import run, route, request
from servicechecker import CheckerBase
from servicechecker.swagger import CheckService
from servicechecker.metrics import Metrics
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import generate_latest
import urllib3

# seconds to subtract from the request timeout to allow for rendering time
RESPONSE_HEADROOM = 3


class MetricsCollection(list):
    def collect(self):
        for x in self:
            yield x


class Prometheus(Metrics):
    def __init__(self, **config):
        self.metrics = MetricsCollection()
        self.hostname = config.get('hostname')

    def send(self, delta, tags):
        gmf = GaugeMetricFamily(
            'service_checker_request_duration_seconds',
            [x[1] for x in tags if x[0] == 'path'][0],  # path from tags as documentation
            labels=[x[0] for x in tags]
        )
        gmf.add_metric(value=delta.total_seconds(), labels=[x[1] for x in tags])
        self.metrics.append(gmf)

    def _get_tags_for(self, url):
        url = urllib3.util.parse_url(url)
        return [('path', url.path), ('host', url.host)]


def summarize(checks):
    return get_summary(all([check['job'].successful() for check in checks]))


def get_summary(result):
    gmf = GaugeMetricFamily(
        'service_checker_probe_success',
        'condensed view of all checks as a one (pass) or zero (fail)',
        labels=[]
    )
    gmf.add_metric(value=int(result), labels=[])
    return gmf


def get_metrics(url: urllib3.util.Url, spec_segment, timeout=5):
    metrics_manager = Prometheus(hostname=url.host)
    timeout -= RESPONSE_HEADROOM
    if timeout <= 0:  # It is useless to proceed with a timeout of 0 or less
        metrics_manager.metrics.append(get_summary(False))  # Assume failure
        return metrics_manager.metrics
    checker = CheckService(
        url.host,
        url.url,
        timeout,
        spec_segment,
        metrics_manager
    )
    # Spawn the downloaders
    checks = [
        {
            'ep': ep,
            'data': data,
            'job': gevent.spawn(checker._check_endpoint, ep, data)
        } for ep, data in checker.get_endpoints()
    ]
    gevent.joinall([v['job'] for v in checks], timeout)
    # summarize check result in to a 1 or 0 gauge
    metrics_manager.metrics.append(summarize(checks))
    return metrics_manager.metrics


def sanitize_path(path, spec_segment):
    if len(path) > 0:
        # strip trailing slash
        if path.endswith('/'):
            path = path[:-1]
        # strip spec segment
        if path[-len(spec_segment):] == spec_segment:
            path = path[:-len(spec_segment)]
    return path


def get_url(target, request_path, spec_segment):
    # parse_url doesn't do the right thing when given just a host:port as a url
    # give it a scheme if it doesn't have one -- http only
    if target[:4] != 'http':
        target = 'http://{}'.format(target)
    scheme, auth, host, port, path, query, fragment = urllib3.util.parse_url(target)
    if path is not None:
        path = sanitize_path(path, spec_segment)
    else:
        path = sanitize_path(request_path, spec_segment)
    return urllib3.util.Url(scheme=scheme, host=host, port=port, path=path)


@route('/probe')
def metrics():
    timeout = float(request.headers.get(
        'X-Prometheus-Scrape-Timeout-Seconds',
        default=CheckerBase.nrpe_timeout
    ))
    spec_segment = request.params.get('spec_segment', '/?spec')
    url = get_url(request.params.target, request.params.get('path', ''), spec_segment)
    metrics = get_metrics(url, spec_segment, timeout)
    return generate_latest(metrics)


def main():
    # Possible port allocation collision
    # https://github.com/prometheus/prometheus/wiki/Default-port-allocations
    run(host='localhost', port='9220', server='gevent')


if __name__ == '__main__':
    main()
