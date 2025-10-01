# IPAM web application

This repository contains a lightweight IP Address Management (IPAM) web application built with [FastAPI](https://fastapi.tiangolo.com/), SQLite, and Jinja templates. It helps teams catalogue subnets, calculate address ranges, and allocate individual IPs with auditing information.

## Features

- **Authentication** – Built-in session-based login with hashed passwords. A default `admin / changeme` account is provisioned on first run, and additional users can be created with a helper CLI.
- **Subnet registry** – Store networks in CIDR notation, add descriptions, and review usage from the dashboard.
- **Subnet calculator** – Calculate network, broadcast, host range, and usable host counts for any CIDR block.
- **IP allocations** – Track host assignments with hostname, owner, notes, and release management. Auto-assign the next available address or reserve a specific host.
- **Modern UI** – Responsive, single-page templates styled with modern CSS for a clear overview.

## Getting started

### 1. Install dependencies

The app uses Python 3.11+. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Launch the server

Run the API with Uvicorn:

```bash
uvicorn app.main:app --reload
```

The site will be available at http://127.0.0.1:8000. You will be redirected to the login screen.

### 3. Sign in

Use the bootstrap credentials created on startup:

```
Username: admin
Password: changeme
```

Change the password or create additional accounts as soon as possible.

### 4. Manage users (optional)

A small CLI is provided for administrative tasks. To create a new user run:

```bash
python -m app.cli create-user <username>
```

If the `--password` flag is omitted, the tool securely prompts for one.

## Application tour

1. **Dashboard** – Lists all stored subnets with capacity, allocation counts, and quick access to their detail pages.
2. **Subnet detail** – Shows derived information (netmask, broadcast, usable hosts), allows manual or automatic allocation, and lists active assignments. Each allocation can be released.
3. **Subnet calculator** – A dedicated tool for one-off calculations without storing the network.

## Codebase overview

```
app/
├── __init__.py          # Makes the folder a Python package
├── auth.py              # Password hashing utilities and user dependency
├── cli.py               # Helper CLI for creating user accounts
├── database.py          # SQLAlchemy engine/session configuration
├── main.py              # FastAPI application, routes, and UI wiring
├── models.py            # ORM models for users, subnets, and IP assignments
├── static/
│   └── style.css        # Shared styling for templates
└── templates/           # Jinja templates for UI pages
    ├── base.html        # Layout shell (nav/footer)
    ├── calculator.html  # Subnet calculator page
    ├── dashboard.html   # Subnet list view
    ├── login.html       # Authentication screen
    ├── new_subnet.html  # Form to register a subnet
    └── subnet_detail.html # Details and allocation management
```

### Important modules

- **`app/main.py`** – Declares the FastAPI application, session middleware, routes, and startup hook that creates the SQLite schema and default admin user. Routes ensure only authenticated sessions reach protected pages (`get_current_user` dependency).
- **`app/models.py`** – Defines SQLAlchemy ORM models and helper properties for subnet capacity, host iteration, and validation. These utilities power allocation logic and UI metrics.
- **`app/database.py`** – Central place to create the engine and expose the `get_db` dependency. FastAPI dependencies manage the lifecycle of database sessions for each request.
- **`app/auth.py`** – Wraps Passlib's bcrypt hashing and exposes the `get_current_user` dependency, redirecting unauthenticated requests to the login page.
- **`app/cli.py`** – Command-line entry point for administrative tasks like user creation.

### Data flow

1. **Authentication** – The login form posts credentials to `/login`. Passwords are validated with `verify_password` and sessions are persisted via Starlette's `SessionMiddleware`.
2. **Subnet creation** – `/subnets` receives form data, validates the CIDR with Python's `ipaddress` module, and stores it via SQLAlchemy. Duplicate networks are gracefully handled.
3. **IP allocation** – `/subnets/{id}/allocate` either validates a requested host or picks the next available address using `next_available_ip`. Allocations are persisted in the `ip_addresses` table and shown immediately in the UI.
4. **Subnet calculator** – `/calculator` uses `ipaddress.ip_network` to compute metrics without touching the database.

### Development tips

- The SQLite database file (`ipam.db`) is created in the project root. Delete it during development to reset the state.
- FastAPI's interactive API docs remain available at `/docs` even though the app primarily serves HTML.
- Extend the data model by adding columns to `app/models.py`, then run the app to auto-create new tables/fields (SQLite lacks migrations; consider Alembic for production).
- To customize styling, edit `app/static/style.css`. All templates extend `base.html` to share layout.

## Testing the installation

After installing dependencies, you can run a quick sanity check to ensure modules import correctly:

```bash
python -m compileall app
```

This compiles the Python modules and catches syntax errors early.

## Running with Podman

You can containerize the application using [Podman](https://podman.io/) with the provided helper script.

1. Ensure Podman is installed and that your user can run rootless containers.
2. From the project root, execute:

   ```bash
   ./scripts/run_podman.sh
   ```

   The script builds the image from the `Containerfile`, provisions a persistent volume for the SQLite database, and starts the service on port `8000`.

3. Visit http://127.0.0.1:8000 to access the UI. Use `Ctrl+C` in the terminal to stop the container.

### Customizing the Podman run

The script honors a few optional environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `IMAGE_NAME` | `ipam-app` | Image tag produced during `podman build`. |
| `CONTAINER_NAME` | `ipam-app` | Name assigned to the running container. |
| `HOST_PORT` | `8000` | Host port exposed for the FastAPI server. |
| `DB_VOLUME` | `ipam-db` | Podman volume used to persist the SQLite database. |

For example, to run on port 9000 with a custom image name:

```bash
HOST_PORT=9000 IMAGE_NAME=company/ipam ./scripts/run_podman.sh
```

The application reads the `IPAM_DB_PATH` environment variable, so you can map the database to a different location or volume if needed.

## License

This project is provided as-is for demonstration and educational purposes.
