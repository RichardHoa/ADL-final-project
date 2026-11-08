from flask import current_app


def services():
    return current_app.extensions["rag"]
