try:
    from app import create_app
    app = create_app()
except Exception as e:
    import sys, traceback
    print(f"[WSGI] FATAL: Failed to create app: {e}", file=sys.stderr)
    print(traceback.format_exc(), file=sys.stderr)
    raise
