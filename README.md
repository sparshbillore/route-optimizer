# Route Optimizer

A REST API for modelling a network of servers and their connection latencies, and finding the lowest-latency route between any two of them.

## Tech stack

- Python 3.10+ (developed on 3.12)
- Django 5.2
- Django REST Framework 3.18
- SQLite

## Setup

```bash
git clone https://github.com/sparshbillore/route-optimizer.git route-optimizer
cd route-optimizer
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

The API is now available at `http://127.0.0.1:8000`. Check it with:

```bash
curl http://127.0.0.1:8000/health
```

## Running tests

```bash
python manage.py test
```

To measure coverage, install the development requirements first. They include the runtime requirements, and `coverage` is kept out of `requirements.txt` because the app doesn't need it to run.

```bash
pip install -r requirements-dev.txt
coverage run --source=network,config manage.py test
coverage report -m --omit="*/migrations/*,*/tests/*,config/asgi.py,config/wsgi.py"
```

The tests are in `network/tests/`, one file per area:

| File | Covers |
|---|---|
| `test_services.py` | The Dijkstra function on its own, with no database |
| `test_nodes.py` | Creating and listing nodes |
| `test_edges.py` | Creating and listing edges |
| `test_routes.py` | `POST /routes/shortest` |
| `test_history.py` | `GET /routes/history` and its filters |
| `test_delete.py` | Retrieve and delete endpoints, cascades, history surviving deletes |
| `test_end_to_end.py` | One full flow: nodes, edges, route, history |

## API reference

All request and response bodies are JSON. URLs have no trailing slash.

| Method | URL | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/nodes` | Create a node |
| `GET` | `/nodes` | List nodes |
| `GET` | `/nodes/{id}` | Retrieve a node |
| `DELETE` | `/nodes/{id}` | Delete a node and its edges |
| `POST` | `/edges` | Create an edge |
| `GET` | `/edges` | List edges |
| `GET` | `/edges/{id}` | Retrieve an edge |
| `DELETE` | `/edges/{id}` | Delete an edge |
| `POST` | `/routes/shortest` | Find the lowest-latency route |
| `GET` | `/routes/history` | List past route queries |

### `GET /health`

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status": "ok"}
```

### `POST /nodes`

```bash
curl -X POST http://127.0.0.1:8000/nodes \
  -H "Content-Type: application/json" \
  -d '{"name": "ServerA"}'
```

`201 Created`

```json
{"id": 1, "name": "ServerA"}
```

A duplicate, missing, blank or over-255-character name returns `400`:

```json
{"name": ["node with this name already exists."]}
```

### `GET /nodes`

```bash
curl http://127.0.0.1:8000/nodes
```

```json
[
  {"id": 1, "name": "ServerA"},
  {"id": 2, "name": "ServerB"},
  {"id": 3, "name": "ServerC"}
]
```

### `GET /nodes/{id}`

```bash
curl http://127.0.0.1:8000/nodes/1
```

```json
{"id": 1, "name": "ServerA"}
```

### `DELETE /nodes/{id}`

```bash
curl -X DELETE http://127.0.0.1:8000/nodes/3
```

`204 No Content`. Every edge into or out of the node is deleted with it. An unknown id returns `404`:

```json
{"detail": "No Node matches the given query."}
```

### `POST /edges`

```bash
curl -X POST http://127.0.0.1:8000/edges \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerB", "latency": 12.5}'
```

`201 Created`

```json
{"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5}
```

Errors return `400`. For example:

```json
{"non_field_errors": ["Edge ServerA → ServerB already exists."]}
```

```json
{"latency": ["Latency must be greater than 0."]}
```

```json
{"source": ["Object with name=ServerX does not exist."]}
```

```json
{"destination": ["Source and destination must be different nodes."]}
```

### `GET /edges`

```bash
curl http://127.0.0.1:8000/edges
```

```json
[
  {"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5},
  {"id": 2, "source": "ServerB", "destination": "ServerC", "latency": 10.9},
  {"id": 3, "source": "ServerA", "destination": "ServerC", "latency": 30.0}
]
```

### `GET /edges/{id}`

```bash
curl http://127.0.0.1:8000/edges/1
```

```json
{"id": 1, "source": "ServerA", "destination": "ServerB", "latency": 12.5}
```

### `DELETE /edges/{id}`

```bash
curl -X DELETE http://127.0.0.1:8000/edges/3
```

`204 No Content`, or `404` for an unknown id.

### `POST /routes/shortest`

With the three edges above:

```bash
curl -X POST http://127.0.0.1:8000/routes/shortest \
  -H "Content-Type: application/json" \
  -d '{"source": "ServerA", "destination": "ServerC"}'
```

`200 OK`. The route through `ServerB` (12.5 + 10.9) beats the direct edge (30):

```json
{"total_latency": 23.4, "path": ["ServerA", "ServerB", "ServerC"]}
```

When both nodes exist but no route connects them, it returns `404`:

```json
{"error": "No path exists between ServerA and ServerD"}
```

An unknown or missing node returns `400`:

```json
{"destination": ["Object with name=ServerX does not exist."]}
```

### `GET /routes/history`

```bash
curl "http://127.0.0.1:8000/routes/history?source=ServerA&date_from=2026-01-01&limit=10"
```

```json
[
  {
    "id": 1,
    "source": "ServerA",
    "destination": "ServerC",
    "total_latency": 23.4,
    "path": ["ServerA", "ServerB", "ServerC"],
    "created_at": "2026-10-17T01:35:52Z"
  }
]
```

Results are newest first. All query parameters are optional:

| Parameter | Format | Meaning |
|---|---|---|
| `source` | Node name | Exact match on the queried source |
| `destination` | Node name | Exact match on the queried destination |
| `date_from` | `YYYY-MM-DD` or ISO 8601 datetime | `created_at` on or after this |
| `date_to` | `YYYY-MM-DD` or ISO 8601 datetime | `created_at` on or before this |
| `limit` | Integer, 1–1000 | Maximum number of records, applied after filtering |

Invalid values return `400` with the parameter name, for example:

```json
{"limit": ["Ensure this value is greater than or equal to 1."]}
```

## Design decisions

### Graph model

**Edges are one-way.** An edge from `ServerA` to `ServerB` doesn't let you travel from `ServerB` to `ServerA`; that needs its own edge, possibly with a different latency. Real network links aren't always symmetric, and this keeps one row equal to one direction. A unique constraint on `(source, destination)` prevents duplicates. The reverse edge is a separate pair, so it's allowed.

**Self-loops are rejected.** An edge from a node to itself could never be part of a shortest route, and the route from a node to itself already costs 0. An edge like that is almost certainly a client mistake, so the API returns a `400` rather than storing it silently.

**Node names are case-sensitive and trimmed.** `ServerA` and `servera` are different nodes. That keeps lookups as exact matches everywhere and avoids guessing at the client's intent. Leading and trailing whitespace is trimmed before validation, so `"  ServerA  "` is stored as `ServerA`, `"   "` is rejected as blank, and a padded duplicate is still caught as a duplicate.

**Latency must be greater than 0, enforced in two places.** The serializer checks it, so a client gets a clean `400` with a clear message. A `CheckConstraint` in the database enforces it too, so data written by any other path, such as the admin, a shell or a future bulk import, can't break the rule. Without the serializer check, the database would raise an `IntegrityError`, which surfaces as a `500`. Booleans are also rejected: Python treats `true` as `1`, which DRF would otherwise accept as a latency of 1.0. `NaN` and `Infinity` are rejected as invalid numbers.

**Deleting a node deletes its edges.** Both foreign keys on `Edge` use `on_delete=CASCADE`. An edge with a missing end has no meaning, and blocking the delete until every edge is removed by hand would make the endpoint tedious to use.

### Shortest path

**Dijkstra runs as a pure function.** `network/services.py` has a `shortest_path(edges, start, end)` function. It takes plain `(source, destination, latency)` tuples and returns `(total_latency, path)`, or `None` when there's no path. It knows nothing about Django, so it can be unit-tested with plain lists and swapped out or reused easily. The view handles HTTP, the database and history; the function only handles the graph.

It builds an adjacency list, then uses a binary heap (`heapq`) as the priority queue. When it finds a shorter distance to a node, it pushes a new heap entry instead of updating the old one. Old entries are skipped when they're popped, if their distance is worse than the best known one. The search stops as soon as it pops the destination, because Dijkstra guarantees that distance is final. It doesn't explore the rest of the graph. Overall it takes O((V + E) log V) time.

Dijkstra is correct here because every latency is positive, which the validation guarantees.

**Totals are rounded to 6 decimal places in the response.** Floating-point addition produces noise: `12.5 + 10.9` is `23.400000000000002`. Rounding to 6 places removes it without losing real precision. Rounding to 2 places would turn small latencies like `0.001 + 0.001` into `0.0`, which misrepresents the data. The service returns the exact sum, and rounding happens only in the view, where the response is built, so the algorithm stays exact and display formatting lives in one place.

**`source == destination` returns `200` with a total of 0.** `{"total_latency": 0, "path": ["ServerA"]}` is the correct answer: you're already there. Returning an error would push a special case onto every client.

**There are two kinds of "no route".** Asking for a node that doesn't exist is a bad request (`400`). Asking for two real nodes with nothing connecting them is a valid question with no answer (`404`).

### History

**Only successful queries are saved.** A history record has a total latency and a path, and a failed query has neither. Storing failures would mean making both fields nullable, and every consumer would have to handle the empty case. `source == destination` counts as a success and is saved.

**History stores names, not foreign keys.** `RouteQuery.source` and `destination` are plain text, and `path` is a JSON list of names. History is a record of what happened at the time. A foreign key would force a bad choice when a node is deleted: cascade and silently lose history, or block deleting any node that was ever queried. Storing names means history survives node and edge deletions unchanged. The cost is that renaming a node, if that's ever added, wouldn't update past records, which is arguably correct for an audit log anyway.

**Newest first.** That's the model's default ordering (`-created_at`), with `-id` breaking ties between records created in the same instant.

**`created_at` is formatted as `YYYY-MM-DDTHH:MM:SSZ`.** DRF's default includes microseconds. The format is set in `REST_FRAMEWORK["DATETIME_FORMAT"]`, and the literal `Z` is correct because the server's `TIME_ZONE` is UTC.

**Date filters:**

- **Plain dates and datetimes:** `date_from` and `date_to` accept either a plain date (`2026-02-20`) or a full ISO 8601 datetime.
- **A plain `date_to` covers the whole day.** `date_to=2026-02-20` includes everything up to `23:59:59.999999` UTC on the 20th. If it meant midnight at the start of the day, as a naive conversion would, records from that day would quietly disappear. A plain `date_from` starts at `00:00:00` UTC.
- **Datetime bounds are inclusive** at both ends.
- **Datetimes without a timezone are treated as UTC.** Datetimes with an offset, like `+05:30`, are respected.
- **Send `+` as `%2B`.** In a query string, `+` means a space, so `date_to=2026-02-20T12:00:00+05:30` arrives with a space instead of `+` and returns `400`. Send `%2B05:30`, use `Z`, or let your HTTP client encode the parameters.
- **Invalid input returns `400`, not `500`.** That covers malformed dates and impossible ones (`2026-02-30`), and also a `date_from` later than `date_to`.

**`limit` must be from 1 to 1000.** Zero, negative, non-integer and over-cap values return `400`. Without `limit`, every matching record is returned. The cap stops one request from pulling an unbounded result set.

**Empty parameters are ignored.** `?limit=` or `?source=` behaves as if the parameter wasn't sent. That's DRF's default for optional fields in query strings, and "empty means unset" is the friendlier reading.

### API conventions

**There are two error shapes.** Validation errors use DRF's standard shape: an object keyed by field name, each with a list of messages, or `non_field_errors` for errors that span fields. This tells a client exactly which input to fix. A missing route uses `{"error": "..."}`, as the spec requires. It isn't about any particular field, so it has no field to key on.

**URLs have no trailing slashes,** matching the spec (`/nodes`, not `/nodes/`). If the routes were defined with slashes, Django's `APPEND_SLASH` would handle a request for `/nodes` by redirecting to `/nodes/`. For a POST, that goes wrong either way. With `DEBUG = True`, Django raises an error instead of redirecting, because the body would be lost. In production it redirects, and most clients follow the redirect as a GET without the body. Defining the routes without slashes avoids the problem entirely. The trade-off is that `/nodes/` returns `404`.

**`id` is read-only.** Any `id` in a request body is ignored.

## Limitations and future improvements

- **The whole graph is loaded on every route query.** That's one query and fine at this scale, but it won't scale to millions of edges. The next step would be to cache the adjacency list in memory, invalidate it whenever a node or edge is created or deleted, and only reload it after a write. Beyond that, the search could run inside the database, for example as a recursive query in PostgreSQL, or in a dedicated graph store.
- **SQLite isn't suitable for production.** It handles concurrent writes poorly. PostgreSQL would be the natural choice and only needs a settings change.
- **There's a small race in duplicate-edge validation.** Two identical edge requests arriving at the same moment could both pass the serializer's check. The second then hits the database constraint and returns a `500` instead of a `400`. Catching `IntegrityError` when creating the edge would close the gap.
- **There's no authentication or authorisation.** Anyone who can reach the API can create and delete nodes. A real deployment would need at least token authentication, and probably read-only access for most users.
- **There's no pagination beyond `limit`.** The list endpoints return everything. DRF's `LimitOffsetPagination` or cursor pagination would be the next step for large histories.
- **Settings are development defaults.** `DEBUG = True` and the `SECRET_KEY` are hard-coded in `config/settings.py`. In production, they and `ALLOWED_HOSTS` would come from environment variables.
- **Nodes and edges can't be updated.** Changing a latency means deleting and recreating the edge. A `PATCH /edges/{id}` would be a small addition.
- **Only one shortest route is returned.** If several routes tie on latency, the API returns one of them. It's deterministic but not configurable.
