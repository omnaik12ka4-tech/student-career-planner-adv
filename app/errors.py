from flask import render_template


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, title="Page not found",
                               message="The page you are looking for doesn't exist or was moved."), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, title="Admins only",
                               message="You don't have permission to open this page."), 403

    @app.errorhandler(400)
    def bad_request(_e):
        return render_template("error.html", code=400, title="That form has expired",
                               message="For your safety the form session timed out. Go back, refresh the page and try again."), 400
