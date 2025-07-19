# WukongStack

WukongStack is a dynamic CLI tool that generates a full-stack web application skeleton, featuring a Python FastAPI backend with OAuth2 authentication, pytest unit tests, and a Vue 3 frontend powered by the PrimeVue component library. Inspired by the lightning-fast Monkey King, Sun Wukong, from Chinese mythology, WukongStack streamlines development by delivering a secure, testable, and modern project structure for rapid prototyping and production-ready applications.

## Features

- **FastAPI Backend**: High-performance, asynchronous Python backend with pre-configured OAuth2 authentication for secure API access.
- **Vue 3 with PrimeVue**: A modern, reactive frontend using Vue 3 and the PrimeVue component library for sleek, accessible UI components.
- **CRUD APIs**: Pre-built RESTful APIs for creating, reading, updating, and deleting resources, with OAuth2-protected endpoints.
- **Pytest Unit Tests**: Comprehensive unit tests for backend APIs using pytest, ensuring reliability and maintainability.
- **Modular Structure**: Organized directory layout for scalability, with clear separation of backend and frontend concerns.
- **Wukong CLI**: Generate a project with a single command using `wukong-cli`, designed for simplicity and customization.
- **Extensible**: Ready for database integration (e.g., SQLite, PostgreSQL) and state management (e.g., Vuex or Pinia).

## Getting Started

### Prerequisites
- Python 3.8+ (for FastAPI backend and pytest)
- Node.js 16+ (for Vue 3 frontend)
- pip and npm installed

### Installation
1. Install the WukongStack CLI:
   ```bash
   pip install click
   ```
2. Generate a new project:
   ```bash
   python wukong-cli.py init my_project
   ```
3. Set up the backend:
   ```bash
   cd my_project/backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. Set up the frontend:
   ```bash
   # instal fnm nodes.js manager
   #linux or mac
   curl -fsSL https://fnm.vercel.app/install | bash
   # windows
   winget install Schniz.fnm

   fnm install v23.11.1

   cd my_project/frontend
   npm install
   npm run dev
   ```

### Project Structure
- `backend/`:
  - `app/main.py`: FastAPI app with OAuth2 authentication setup.
  - `app/api/v1/endpoints/`: CRUD endpoints with OAuth2 security.
  - `app/auth/`: OAuth2 implementation (e.g., JWT-based authentication).
  - `tests/`: Pytest unit tests for APIs and authentication logic.
- `frontend/`:
  - `src/components/`: Reusable PrimeVue components (e.g., DataTable, InputText).
  - `src/views/`: Vue 3 views for managing resources with PrimeVue styling.
  - `src/main.js`: Vue app entry with PrimeVue integration.
- `wukong-cli.py`: CLI script to generate the project skeleton.

### Example Usage
- **Backend**: Access OAuth2-protected APIs at `http://localhost:8000/items/` for CRUD operations. Use the `/token` endpoint to authenticate users.
- **Frontend**: A Vue component (`ItemList.vue`) leverages PrimeVue’s DataTable and forms to interact with secure APIs.
- **Testing**: Run `pytest` in the `backend/` directory to execute unit tests for APIs and authentication.

## Why WukongStack?
Named after Sun Wukong, the Monkey King renowned for his meteoric speed and ingenuity, WukongStack empowers developers to swiftly create secure, testable, and visually appealing full-stack applications. With OAuth2 integration, pytest unit tests, and PrimeVue’s elegant components, WukongStack is ideal for building modern web applications with minimal setup.

## Contributing
Contributions are welcome! Submit issues or pull requests to the [WukongStack repository](https://github.com/your-repo/wukongstack).

## License
MIT License
