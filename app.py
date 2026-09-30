"""
Local development entry point:   python app.py
For production, use wsgi.py with gunicorn instead (see README).
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
