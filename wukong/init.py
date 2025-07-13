import click
from pathlib import Path


@click.command()
def init_project():
    """Initialize a new project structure"""
    project_name = click.prompt("Project name", type=str)
    project_description = click.prompt("Project description", type=str)

    # Create root directory
    root_path = Path(project_name)
    root_path.mkdir(parents=True, exist_ok=True)

    # Create directory structure
    directories = [
        "ddls",
        # "backend/app/api/v1/endpoints",
        # "backend/app/auth",
        # "backend/app/models",
        # "backend/app/schemas",
        "backend/tests",
        # "frontend/public",
        # "frontend/src/assets",
        # "frontend/src/components",
        # "frontend/src/views",
        # "frontend/src/router",
        # "frontend/src/store",
        # "frontend/src/services",
        "docs"
    ]

    # Create all directories
    for directory in directories:
        (root_path / directory).mkdir(parents=True, exist_ok=True)

    # Create files
    create_readme(root_path, project_name, project_description)
    # create_backend_files(root_path, project_name)
    # create_frontend_files(root_path)
    create_dockerfile(root_path)

    click.echo(f"✅ Project '{project_name}' initialized successfully!")
    click.echo(f"Next steps:\n  cd {project_name}\n  wukong codegen")


def create_readme(root_path, project_name, description):
    """Create README.md files for the project"""
    # Main README content
    main_readme = f"""# {project_name}

{description}

## Project Structure

```
{project_name}/
├── ddls/               # Database definition files (SQL DDLs)
├── backend/            # Backend application (FastAPI)
│   ├── app/            # Application source code
│   │   ├── api/        # API endpoints
│   │   ├── auth/       # Authentication logic
│   │   ├── models/     # Pydantic models
│   │   ├── schemas/    # SQLAlchemy schemas
│   │   ├── database.py # Database configuration
│   │   └── main.py     # Application entry point
│   ├── tests/          # Unit tests
│   ├── requirements.txt# Python dependencies
│   └── pyproject.toml  # Project configuration
├── frontend/           # Frontend application (Vue 3)
│   ├── public/         # Static assets
│   └── src/            # Application source
│       ├── assets/     # Images/styles
│       ├── components/ # Vue components
│       ├── views/      # Page views
│       ├── router/     # Navigation routes
│       ├── store/      # State management
│       ├── services/   # API services
│       ├── App.vue     # Root component
│       └── main.js     # Application entry point
├── docs/               # Documentation
├── Dockerfile          # Container configuration
└── README.md           # This file
```

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- SQLite (or your preferred database)

### Installation
1. Initialize project:
   ```bash
   wukong init
   ```
2. Add DDL files to `ddls/` directory
3. Generate applications:
   ```bash
   wukong codegen
   ```
4. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   
   cd ../frontend
   npm install
   ```

### Running Applications
**Backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm run dev
```

## Project Commands
| Command | Description |
|--------|-------------|
| `wukong init` | Initialize project structure |
| `wukong codegen` | Generate CRUD applications from DDLs |
| `wukong add <package>` | Add Python dependency |
| `wukong increase-build` | Increment build version |
| `wukong increase-minor` | Increment minor version |
| `wukong increase-major` | Increment major version |

## Customization
- Edit DDL files in `ddls/` and re-run `wukong codegen`
- Modify generated code in `backend/app/` and `frontend/src/`
- Add environment variables in `.env` files

## Deployment
Build Docker container:
```bash
docker build -t {project_name} .
docker run -p 8000:8000 {project_name}
```

## Support
For issues or feature requests, please [open an issue](https://github.com/your-repo/issues)
"""

    # Write main README
    (root_path / "README.md").write_text(main_readme)


def create_dockerfile(root_path):
    dockerfile_content = """# Backend build stage
FROM python:3.10-slim as backend-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy backend source code
COPY backend/ .

# Frontend build stage
FROM node:18 as frontend-builder

WORKDIR /app

# Install frontend dependencies
COPY frontend/package*.json .
RUN npm install

# Copy frontend source code
COPY frontend/ .
RUN npm run build

# Final production image
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=backend-builder /root/.local /root/.local

# Copy backend source
COPY --from=backend-builder /app /app

# Copy built frontend
COPY --from=frontend-builder /app/dist /app/frontend/dist

# Set environment variables
ENV PATH="/root/.local/bin:${PATH}"
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV STATIC_FILES_PATH=/app/frontend/dist

# Expose port
EXPOSE $PORT

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:$PORT/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    (root_path / "Dockerfile").write_text(dockerfile_content)