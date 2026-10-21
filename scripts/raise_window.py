#!/usr/bin/env python
"""Đưa cửa sổ X lên trước (raise + activate) theo tên — dùng cho app "Smart Parking".

Với GNOME/Mutter, chỉ restack (XRaiseWindow) có thể không đủ: compositor vẫn giữ
texture cũ nên cửa sổ bị "mất" khi có cửa sổ khác phủ lên. Cách chắc chắn hơn:
unmap → map lại → activate.

Usage:
    python scripts/raise_window.py "Smart Parking"
    python scripts/raise_window.py "Smart Parking" --remap

Cần: pip install python-xlib   (đã có sẵn trong .venv của repo)
"""
import sys
import time

try:
    from Xlib import display, X
    from Xlib.protocol import event as Xevent
except ImportError:
    print("Thiếu python-xlib — cài: pip install python-xlib")
    sys.exit(1)


def find_windows(root, title):
    found = []

    def walk(w):
        try:
            name = w.get_wm_name()
        except Exception:
            name = None
        if name and title in name:
            found.append(w)
        try:
            for child in w.query_tree().children:
                walk(child)
        except Exception:
            pass

    walk(root)
    return found


def main(argv):
    if not argv:
        print(__doc__)
        return 1
    title = argv[0]
    remap = "--remap" in argv[1:]

    disp = display.Display()
    root = disp.screen().root
    windows = find_windows(root, title)
    if not windows:
        print("Không tìm thấy cửa sổ: %r" % title)
        return 1

    win = windows[-1]
    print("window %s: %r" % (hex(win.id), win.get_wm_name()))

    if remap:
        wm_state = disp.intern_atom("WM_STATE")
        win.change_property(wm_state, wm_state, 32, [0, 0])
        win.unmap()
        disp.sync()
        time.sleep(0.8)
        win.map()
        disp.sync()
        time.sleep(0.8)

    # EWMH activation
    atom = disp.get_atom("_NET_ACTIVE_WINDOW")
    root.send_event(
        Xevent.ClientMessage(window=win, client_type=atom,
                             data=(32, [2, X.CurrentTime, 0, 0, 0])),
        event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
    disp.flush()
    time.sleep(0.4)

    # hard restack above the rest
    try:
        win.configure(stack_mode=X.Above)
    except Exception:
        pass
    disp.sync()

    geom = win.get_geometry()
    print("OK: %dx%d+%d+%d" % (geom.width, geom.height, geom.x, geom.y))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
