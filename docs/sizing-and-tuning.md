# Sizing & PostgreSQL Tuning

The `database-server` (PostgreSQL 18) is tuned via `.env` for the host's RAM and
the disk the data volume lives on. Defaults target an 8 GB host on SSD/NVMe; the
development compose defaults to the 4 GB column.

## Storage I/O — match the disk

`random_page_cost` and `effective_io_concurrency` model how cheap random reads
are. SSD/NVMe ≈ sequential; spinning disks pay a large seek penalty.

| ENV Variable                  | SSD/NVMe (default) | HDD 10k RPM | HDD 7.2k RPM |
|-------------------------------|--------------------|-------------|--------------|
| `PG_RANDOM_PAGE_COST`         | `1.1`              | `2.0`       | `4.0`        |
| `PG_EFFECTIVE_IO_CONCURRENCY` | `200`              | `4`         | `2`          |

## Memory — match host RAM

| ENV Variable              | 4 GB    | 8 GB    | 16 GB   | 32 GB   |
|---------------------------|---------|---------|---------|---------|
| `PG_SHARED_BUFFERS`       | `1GB`   | `2GB`   | `4GB`   | `8GB`   |
| `PG_EFFECTIVE_CACHE_SIZE` | `3GB`   | `6GB`   | `12GB`  | `24GB`  |
| `PG_WORK_MEM`             | `4MB`   | `8MB`   | `16MB`  | `32MB`  |
| `PG_MAINTENANCE_WORK_MEM` | `128MB` | `256MB` | `512MB` | `1GB`   |

## WAL (Write-Ahead Log) — scale with RAM

| ENV Variable      | 4 GB    | 8 GB    | 16 GB   | 32 GB   |
|-------------------|---------|---------|---------|---------|
| `PG_MAX_WAL_SIZE` | `1GB`   | `2GB`   | `4GB`   | `8GB`   |
| `PG_MIN_WAL_SIZE` | `256MB` | `512MB` | `1GB`   | `2GB`   |

## Fixed parameters

Set directly in the compose `command:` (rarely need changing):
`seq_page_cost=1.0`, `max_parallel_workers_per_gather=2`, `max_parallel_workers=4`,
`max_parallel_maintenance_workers=2`, `checkpoint_completion_target=0.9`,
`wal_buffers=16MB`, `default_statistics_target=100`.

`PG_MAX_CONNECTIONS` defaults to `100`; Zitadel pools internally, so this suits
most single-instance deployments. Raise it only when running multiple Zitadel
replicas (HA) against the same database.

## How to apply

Pick the column for your host and set the variables in `.env`, then recreate the
database service:

```bash
docker compose -f docker-compose.traefik.yml up -d database-server
```

Changes to `command:` flags take effect on container recreation; no data is lost
(the tuning is server config, not schema).
