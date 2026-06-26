from app.stac import gen_stac_catalog, log_exception


def test():
    try:
        gen_stac_catalog()
    except Exception as e:
        log_exception("General stac test exception. See stacktrace for details.")


test()
