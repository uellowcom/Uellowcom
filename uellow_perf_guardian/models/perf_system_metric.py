import logging
import os
import shutil
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _read_loadavg():
    try:
        with open('/proc/loadavg', 'r') as f:
            parts = f.read().split()
        return float(parts[0]), float(parts[1]), float(parts[2])
    except Exception:
        return 0.0, 0.0, 0.0


def _read_meminfo():
    """Return (mem_used_pct, swap_used_mb, total_mb)."""
    try:
        info = {}
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                k, _, v = line.partition(':')
                v = v.strip().split()
                if v:
                    info[k.strip()] = int(v[0])  # kB
        total = info.get('MemTotal', 0)
        avail = info.get('MemAvailable', 0)
        swap_total = info.get('SwapTotal', 0)
        swap_free  = info.get('SwapFree', 0)
        used_pct = 100 * (total - avail) / total if total else 0
        swap_used_mb = (swap_total - swap_free) / 1024
        return used_pct, swap_used_mb, total / 1024
    except Exception:
        return 0.0, 0.0, 0.0


def _read_disk():
    try:
        total, used, free = shutil.disk_usage('/')
        return 100 * used / total
    except Exception:
        return 0.0


class PerfSystemMetric(models.Model):
    """One row per minute — host CPU/RAM/disk + idle-in-transaction count."""
    _name = 'uellow.perf.system.metric'
    _description = 'Uellow Performance — system metric'
    _order = 'create_date desc'

    load_1m = fields.Float(string='Load avg (1m)')
    load_5m = fields.Float(string='Load avg (5m)')
    load_15m = fields.Float(string='Load avg (15m)')
    cpu_count = fields.Integer()
    mem_used_pct = fields.Float(string='Memory used (%)')
    mem_total_mb = fields.Float(string='Memory total (MB)')
    swap_used_mb = fields.Float(string='Swap used (MB)')
    disk_used_pct = fields.Float(string='Disk used (%)')

    pg_connections = fields.Integer(string='PG connections')
    idle_tx_count = fields.Integer(
        string='Idle in transaction (count)',
        help='Number of Postgres connections stuck in "idle in transaction" state.')
    pg_stat_statements_available = fields.Boolean(
        string='pg_stat_statements loaded')

    @api.model
    def cron_collect(self):
        load_1, load_5, load_15 = _read_loadavg()
        mem_pct, swap_mb, mem_total = _read_meminfo()
        disk_pct = _read_disk()
        cpu_n = os.cpu_count() or 0

        # PG stats (best-effort; never fail)
        pg_conn, idle_tx = 0, 0
        try:
            self.env.cr.execute("""
                SELECT
                  count(*) AS total,
                  count(*) FILTER (WHERE state = 'idle in transaction') AS idle_tx
                FROM pg_stat_activity
                WHERE datname = current_database()
            """)
            row = self.env.cr.dictfetchone() or {}
            pg_conn = row.get('total') or 0
            idle_tx = row.get('idle_tx') or 0
        except Exception:
            pass

        # pg_stat_statements probe
        pgss = False
        try:
            self.env.cr.execute(
                "SELECT 1 FROM pg_extension WHERE extname='pg_stat_statements'")
            pgss = bool(self.env.cr.fetchone())
        except Exception:
            pass

        rec = self.create({
            'load_1m': load_1, 'load_5m': load_5, 'load_15m': load_15,
            'cpu_count': cpu_n,
            'mem_used_pct': mem_pct, 'mem_total_mb': mem_total,
            'swap_used_mb': swap_mb, 'disk_used_pct': disk_pct,
            'pg_connections': pg_conn, 'idle_tx_count': idle_tx,
            'pg_stat_statements_available': pgss,
        })

        # Fire alerts on bad signals
        Alert = self.env['uellow.perf.alert'].sudo()
        if load_1 > (cpu_n or 2) * 1.5:
            Alert.fire('system', 'critical',
                       f'Load avg 1m = {load_1:.2f} (CPU={cpu_n}, ratio > 1.5)')
        elif load_1 > (cpu_n or 2):
            Alert.fire('system', 'warning',
                       f'Load avg 1m = {load_1:.2f} (CPU={cpu_n}, ratio > 1.0)')

        if mem_pct >= 90:
            Alert.fire('system', 'critical',
                       f'Memory used {mem_pct:.0f}% — risk of OOM')
        elif mem_pct >= 80:
            Alert.fire('system', 'warning',
                       f'Memory used {mem_pct:.0f}%')

        if idle_tx >= 5:
            Alert.fire('system', 'warning',
                       f'{idle_tx} Postgres connections idle in transaction')

        if disk_pct >= 90:
            Alert.fire('system', 'critical',
                       f'Disk used {disk_pct:.0f}%')

        if not pgss:
            Alert.fire('system', 'info',
                       'pg_stat_statements extension not loaded — slow-query '
                       'tracking inactive. Add to shared_preload_libraries.')

        return rec.id

    @api.model
    def cron_prune(self):
        cutoff = fields.Datetime.now() - timedelta(days=14)
        self.env.cr.execute(
            "DELETE FROM uellow_perf_system_metric WHERE create_date < %s",
            [cutoff])
