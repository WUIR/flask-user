"""Entry point for Flask CLI and development server."""
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

from app import create_app

# Import models so Flask-Migrate can discover them
from app.models import User  # noqa: F401

app = create_app()

if __name__ == "__main__":
    app.run()
