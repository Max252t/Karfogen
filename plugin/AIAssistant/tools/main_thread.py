import threading


class MainThreadTimeout(Exception):
    pass


def _app():
    from steslicer.SteSlicerApplication import SteSlicerApplication
    return SteSlicerApplication.getInstance()


def run_on_main(func, *args, **kwargs):
    timeout = kwargs.pop("_timeout", 30)
    if threading.current_thread() is threading.main_thread():
        return func(*args, **kwargs)
    app = _app()
    done = threading.Event()
    box = {}

    def wrapper():
        if box.get("cancelled"):
            done.set()
            return
        try:
            box["result"] = func(*args, **kwargs)
        except Exception as e:
            box["error"] = e
        finally:
            done.set()

    app.callLater(wrapper)
    if not done.wait(timeout):
        box["cancelled"] = True
        raise MainThreadTimeout("Main thread did not respond in %s s" % timeout)
    if "error" in box:
        raise box["error"]
    return box.get("result")


def wait_until(predicate, timeout, interval=0.3):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = run_on_main(predicate)
        if value:
            return value
        time.sleep(interval)
    return None
