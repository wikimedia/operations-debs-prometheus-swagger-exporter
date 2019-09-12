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


def get_summary(checks):
    gmf = GaugeMetricFamily(
        'service_checker_probe_success',
        'condensed view of all checks as a one (pass) or zero (fail)',
        labels=[]
    )
    if all([check['job'].successful for check in checks]):
        gmf.add_metric(value=1, labels=[])
    else:
        gmf.add_metric(value=0, labels=[])
    return gmf


def get_metrics(target, timeout=5):
    target = urllib3.util.parse_url(target)
    metrics_manager = Prometheus(hostname=target.host)
    checker = CheckService(
        target.host,
        target.url,
        timeout,
        metrics_manager=metrics_manager
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
    metrics_manager.metrics.append(get_summary(checks))
    return metrics_manager.metrics


@route('/probe')
def metrics():
    timeout = int(request.headers.get(
        'X-Prometheus-Scrape-Timeout-Seconds',
        default=CheckerBase.nrpe_timeout
    ))
    metrics = get_metrics(request.query.target, timeout)
    return generate_latest(metrics)


def main():
    # Possible port allocation collision
    # https://github.com/prometheus/prometheus/wiki/Default-port-allocations
    run(host='localhost', port='9220', server='gevent')


if __name__ == '__main__':
    main()
