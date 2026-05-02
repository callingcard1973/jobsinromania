"""Shared state for dashboard modules."""
JS_FILES = {}

def register_js(name, content):
    JS_FILES[name] = content
