# trellis-wp-monitoring

Nginx log traffic analysis and attack detection for [Roots Trellis](https://roots.io/trellis/) servers, as an Ansible role.

Installs two log analysers on the server, wraps them in per-site report
scripts, and schedules them with cron. Reports land in
`/home/web/monitoring/logs/` and can be mailed when something is flagged.

## Why this exists

The [user-contributed Trellis extensions](https://roots.io/trellis/docs/user-contributed-extensions/)
cover database and uploads sync several times over — and nothing else.
There is no published Trellis role for Nginx log analysis, traffic
reporting, or attack detection. This is that role.

## What it does

| Report | Default schedule | Output |
|--------|------------------|--------|
| Traffic | daily, 08:00 | Requests, top pages, referrers, bots, bandwidth over the last 24h |
| Security scan | every 6 hours | wp-login/xmlrpc abuse, high-volume IPs, scanner probes |
| Weekly summary | Mondays, 09:00 | Same traffic analysis over a 168h window |

Each runs per site in `wordpress_sites`, against that site's own
`logs/access.log`.

## Requirements

- Ansible 2.12+
- A Trellis project. The role reads `wordpress_sites`, `web_user`, and
  `www_root` from your Trellis group_vars — the same coupling every
  extension on the roots.io page has.
- Ubuntu 20.04 / 22.04 / 24.04

## Installation

Add to `galaxy.yml` in your Trellis directory:

```yaml
roles:
  - name: imagewize.trellis_wp_monitoring
    src: https://github.com/imagewize/trellis-wp-monitoring
    version: v1.0.0
```

Install it:

```bash
ansible-galaxy install -r galaxy.yml
```

Add it to `server.yml`, after the `wordpress-setup` role so the site log
directories exist:

```yaml
  roles:
    # ... existing Trellis roles ...
    - { role: imagewize.trellis_wp_monitoring, tags: [wp-monitoring] }
```

Then provision:

```bash
trellis provision --tags wp-monitoring production
```

## Configuration

Everything is overridable from `group_vars/<env>/main.yml`. Defaults are in
[`defaults/main.yml`](defaults/main.yml).

```yaml
# Mail reports and alerts here. Empty (the default) writes reports to disk
# and sends nothing.
wp_monitoring_alert_email: alerts@example.com

# Flag any single IP exceeding this many requests in the scan window.
wp_monitoring_security_threshold: 100

# Scan more often, report less often.
wp_monitoring_security_cron_hour: "*/2"
wp_monitoring_traffic_cron_hour: "6"

# Keep daily traffic reports for a quarter instead of a month.
wp_monitoring_traffic_retention_days: 90
```

### Monitoring a subset of sites

`wp_monitoring_sites` defaults to all of `wordpress_sites`. Narrow it:

```yaml
wp_monitoring_sites:
  example.com: "{{ wordpress_sites['example.com'] }}"
```

### Turning a report off

Each of the three is independently switchable, and setting one to `false`
**removes** its cron entry rather than orphaning it:

```yaml
wp_monitoring_weekly_enabled: false
```

### A non-standard log path

```yaml
wp_monitoring_log_file: /var/log/nginx/access.log
```

## Reading the reports

```bash
trellis ssh production
ls /home/web/monitoring/logs/

# Run one by hand rather than waiting for cron
/home/web/monitoring/traffic-monitor.sh /srv/www/example.com/logs/access.log 24
/home/web/monitoring/security-monitor.sh /srv/www/example.com/logs/access.log 6 100
```

## Notes

**gawk.** The analysers use `mktime()` to cut a log to an N-hour window.
Ubuntu ships mawk, which has no `mktime`, so the role installs gawk. Set
`wp_monitoring_install_gawk: false` to skip it — the scripts still run, but
fall back to a cruder line-count estimate of the window.

**Why the cron jobs call wrapper scripts.** cron treats an unescaped `%` as
end-of-command and pipes the rest to the job's stdin. A crontab line
containing `$(date +%Y-%m-%d)` is silently truncated mid-word, which is a
common way for a scheduled report to produce nothing for months without
anyone noticing. The wrappers keep `%` out of the crontab entirely.

## Source

The analysers in [`files/`](files/) come from
[imagewize/wp-ops](https://github.com/imagewize/wp-ops), which stays their
source of truth. This role packages them for the standard Trellis
provisioning path; wp-ops also exposes them as ad-hoc commands
(`wp-ops monitoring`, or `trellis ops monitoring`) for when you want a
report right now rather than on a schedule.

## License

MIT
