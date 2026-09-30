"""
Production entry point.  Run locally with:   python app.py
Run in production with:                      gunicorn wsgi:app
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
