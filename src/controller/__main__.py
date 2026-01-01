def _run():
    try:
        from . import cli  # type: ignore
        if hasattr(cli, "main"):
            return cli.main()
    except Exception:
        pass

    # fallback: execute cli module as script
    import runpy
    runpy.run_module("src.controller.cli", run_name="__main__")

if __name__ == "__main__":
    _run()
