# Subnet Helper

A lightweight Flask web application for calculating IPv4 and IPv6 subnet details and browsing a networking cheat sheet. The project is designed to run locally or inside a container (e.g., Podman Desktop).

## Features

- IPv4 subnet calculator with network address, netmask, broadcast, host ranges, and host counts.
- IPv6 subnet calculator with compressed/expanded representations, host totals, and scope indicators.
- IPv4 VLSM planner to divide a larger network across departments based on host needs.
- Curated cheat sheet covering private/public ranges and other quick reference facts for IPv4 and IPv6.
- Responsive interface built with Bootstrap.

## Getting Started

### Prerequisites

- Python 3.11+
- [Podman](https://podman.io/) (optional, required for containerized execution)

### Local Development

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

2. Run the Flask development server:

   ```bash
   flask --app app.app run --host 0.0.0.0 --port 8000
   ```

3. Open your browser to [http://localhost:8000](http://localhost:8000) to use the app.

### Containerized Deployment with Podman Desktop

1. Build the container image:

   ```bash
   podman build -t subnet-helper .
   ```

2. Run the container, forwarding port 8000:

   ```bash
   podman run --rm -p 8000:8000 subnet-helper
   ```

3. Access the application at [http://localhost:8000](http://localhost:8000).

### Configuration

The default configuration exposes the Flask server on port 8000 and listens on all interfaces. Adjust port mappings as needed when running in Podman.

### Using the VLSM Planner

1. Open the **IPv4 VLSM Planner** card in the UI.
2. Enter the IPv4 network you want to subdivide (for example, `10.0.0.0/22`).
3. Provide each department's host requirement on a separate line. You can use `Department: hosts`, `Department, hosts`, or just a number. Example:

   ```
   Sales: 50
   Engineering: 120
   HR, 25
   30
   ```

4. Submit the form to see the calculated subnets, the usable host range for each allocation, and any leftover address space inside the base network.

> **Tip:** Requirements are automatically sorted from largest to smallest so that the planner finds space-efficient allocations first.

### Project Structure

```
├── Dockerfile
├── README.md
├── app
│   ├── app.py
│   ├── static
│   │   └── styles.css
│   └── templates
│       └── index.html
└── requirements.txt
```

## Development Notes

- The application uses Python's standard `ipaddress` module for all calculations.
- Error handling provides validation feedback for malformed network inputs.
- The included Dockerfile uses the official `python:3.11-slim` base image for a compact footprint.

## License

This project is provided as-is for demonstration purposes.
