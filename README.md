Prometheus Swagger Exporter
===

A Prometheus exporter that renders metrics from requests executed by service-checker.


Probe Endpoint
===

`target`: Can be:
  1. The full target URL
  2. The target scheme (optional, default 'http://'), host, and port (optional, default to scheme default).  Usually combined with `path`.

`path`: The path to append if `target` is not a full URL 

`spec_segment`: The path segment appended to the URL that yields the API spec.  Default: '/?spec'. 

Examples
===
```bash
# Target with URL
curl -s "http://swagger-exporter:9220/probe?target=http://aqs1004:7232/analytics.wikimedia.org/v1"

# Target as host:port with path
curl -s "http://swagger-exporter:9220/probe?target=aqs1004:7232&path=analytics.wikimedia.org/v1"

# Target as host:port with custom spec_segment
curl -s "http://swagger-exporter:9220/probe?target=aqs1004:7232&spec_segment=/?spec&path=analytics.wikimedia.org/v1"

```
