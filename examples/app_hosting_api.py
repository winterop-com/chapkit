"""Example service hosting static web applications.

This example demonstrates the chapkit app system for hosting static web apps
(HTML/JS/CSS) alongside your FastAPI service.

Run:
    fastapi dev examples/app_hosting_api.py

Then visit:
    http://localhost:8000/dashboard  - Sample dashboard app
    http://localhost:8000/docs       - API documentation
    http://localhost:8000/health     - Health check
"""

from chapkit.core.api import BaseServiceBuilder, ServiceInfo

# Create service with app hosting
app = (
    BaseServiceBuilder(
        info=ServiceInfo(
            display_name="App Hosting Demo",
            version="1.0.0",
            summary="Demonstrates hosting static web apps with chapkit",
            description="This service hosts a sample dashboard app at /dashboard",
        )
    )
    .with_health()
    .with_system()
    # Mount single app from filesystem
    .with_app("examples/apps/sample-dashboard")
    # Or auto-discover all apps in directory:
    # .with_apps("examples/apps")
    # Or auto-discover apps from package resources:
    # .with_apps(("mycompany.webapps", "apps"))
    .build()
)

if __name__ == "__main__":
    from chapkit.core.api import run_app

    run_app("app_hosting_api:app")
