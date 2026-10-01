#!/usr/bin/python3
"""Türkçe GTK4 sıralı disk hız testi."""
import ctypes
import errno
import json
import mmap
import os
import random
import shutil
import signal
import stat
import subprocess
import threading
import time
import urllib.parse

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, GLib, Gdk

APP_ID = "org.diskspeedtest.Gtk4"
TEMP_NAME = ".disk_hiz_testi.tmp"
MIB = 1024 ** 2
GIB = 1024 ** 3


def tr_number(value, decimals=0):
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def human_bytes(n):
    if n is None or n < 0:
        return "—"
    units = ("B", "KB", "MB", "GB", "TB")
    v = float(n)
    for unit in units:
        if v < 1024 or unit == units[-1]:
            return f"{tr_number(v, 0)} {unit}"
        v /= 1024
    return "—"


def speed_text(bps):
    if not bps or bps < 0:
        return "—"
    if bps >= GIB:
        return f"{tr_number(bps / GIB, 2)} GB/s"
    if bps >= MIB:
        return f"{tr_number(bps / MIB)} MB/s"
    return f"{tr_number(bps / 1024)} KB/s"


def mount_for(path):
    best = None
    try:
        path = os.path.realpath(path)
        with open("/proc/self/mountinfo", encoding="utf-8") as f:
            for line in f:
                left, right = line.rstrip().split(" - ", 1)
                a, b = left.split(), right.split()
                mp = urllib.parse.unquote(a[4].replace("\\040", " ").replace("\\011", "\t").replace("\\134", "\\"))
                if path == mp or path.startswith(mp.rstrip("/") + "/"):
                    if best is None or len(mp) > len(best[0]):
                        best = (mp, a[2], b[0], b[1])
    except (OSError, ValueError, IndexError):
        pass
    if not best:
        return {"mount": "—", "device": None, "fs": "?", "source": "—"}
    major_minor = best[1]
    source = best[3]
    dev = os.path.realpath(f"/sys/dev/block/{major_minor}")
    if not os.path.exists(dev):
        dev = None
    return {"mount": best[0], "device": dev, "fs": best[2], "source": source}


def sysread(path, fallback="—"):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip() or fallback
    except OSError:
        return fallback


def block_info(directory):
    m = mount_for(directory)
    dev = m["device"]
    if not dev:
        return m | {"model": "—", "kind": "Bilinmiyor", "usb": False, "usb_version": "—", "rpm": "—", "rotational": "—"}
    base = os.path.basename(dev)
    # Partition nodes report their parent disk for hardware attributes.
    if os.path.exists(os.path.join(dev, "partition")):
        dev = os.path.dirname(dev)
        base = os.path.basename(dev)
    model = sysread(os.path.join(dev, "device", "model"), "—")
    vendor = sysread(os.path.join(dev, "device", "vendor"), "—")
    rotational = sysread(os.path.join(dev, "queue", "rotational"), "—")
    usb_path = os.path.realpath(os.path.join(dev, "device"))
    usb = "/usb" in usb_path or "usb" in usb_path.lower()
    kind = "USB" if usb else ("HDD" if rotational == "1" else "SSD" if rotational == "0" else "Bilinmiyor")
    if base.startswith("nvme"):
        kind = "NVMe SSD"
    return m | {"device": dev, "name": "/dev/" + base, "model": model, "vendor": vendor, "kind": kind,
                "usb": usb, "usb_version": sysread(os.path.join(dev, "device", "version"), "—"),
                "rpm": sysread(os.path.join(dev, "device", "queue", "rotational"), "—"), "rotational": rotational}


def space_for(path):
    try:
        s = os.statvfs(path)
        return s.f_bavail * s.f_frsize, s.f_blocks * s.f_frsize, (s.f_blocks - s.f_bfree) * s.f_frsize
    except OSError:
        return None, None, None


def list_details(path, smart=None, locked=False):
    info = block_info(path)
    free, total, used = space_for(path)
    pct = round(used * 100 / total) if total else None
    device = info.get("name", "Bilinmiyor")
    model = info.get("model", "—")
    summary = [
        ("Bağlantı", [("Hedef konum", path), ("Aygıt", device), ("Dosya sistemi", info.get("fs", "?")),
                       ("Toplam alan", human_bytes(total)), ("Kullanılan", f"{human_bytes(used)} ({pct}%)" if pct is not None else "—"), ("Boş alan", human_bytes(free))]),
        ("Donanım", [("Tür", info.get("kind", "Bilinmiyor")), ("Model", model), ("Model ailesi", model),
                     ("Üretici", info.get("vendor", "—")), ("Seri numarası", sysread(os.path.join(info.get("device") or "/", "device", "serial"))),
                     ("Yazılım sürümü", sysread(os.path.join(info.get("device") or "/", "device", "rev"))),
                     ("Form faktörü", "—"), ("Kapasite", human_bytes(total))]),
        ("Bağlantı tipi", [("Arayüz", "NVMe" if device.startswith("/dev/nvme") else "USB" if info.get("usb") else "SATA / dahili"),
                            ("Aygıt adı", device), ("Bağlantı notu", "USB bağlantısında ölçülen hız bu tavanın altındadır" if info.get("usb") else "USB: Bağlı değil (dahili bağlantı)"),
                            ("USB sürümü", info.get("usb_version", "—"))]),
        ("Performans", [("Dönen medya", "Evet" if info.get("rotational") == "1" else "Hayır" if info.get("rotational") == "0" else "—"),
                         ("Mantıksal blok bayt", sysread(os.path.join(info.get("device") or "/", "queue", "logical_block_size"))),
                         ("Fiziksel blok bayt", sysread(os.path.join(info.get("device") or "/", "queue", "physical_block_size"))),
                         ("TRIM/DISCARD", "Destekliyor" if sysread(os.path.join(info.get("device") or "/", "queue", "discard_max_bytes"), "0") not in ("0", "—") else "Desteklemiyor"),
                         ("I/O zamanlayıcı", sysread(os.path.join(info.get("device") or "/", "queue", "scheduler"))),
                         ("Sıcaklık", (smart or {}).get("temperature", "Veri yok"))]),
        ("Sağlık", [("SMART", (smart or {}).get("health", "Root izni gerekli" if locked else "Veri yok")),
                     ("Çalışma süresi", (smart or {}).get("hours", "Root izni gerekli" if locked else "Veri yok")),
                     ("SMART notu", (smart or {}).get("note", "—")),
                     ("Yazma önbelleği", "Açık" if sysread(os.path.join(info.get("device") or "/", "queue", "write_cache"), "unknown") == "write back" else "—"),
                     ("Aygıt durumu", sysread(os.path.join(info.get("device") or "/", "device", "state")))]),
    ]
    if not info.get("device"):
        summary[1] = ("Aygıt", [("Durum", "Blok aygıt eşleştirilemedi (ağ diski, sanal dosya sistemi vb.)")])
    return info, total, used, pct, summary


class DiskSpeedApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.path = os.path.expanduser("~")
        self.running = False
        self.cancel_event = threading.Event()
        self.keep_file = False
        self.direct = False
        self.results = {"write": None, "read": None}
        self.phase_start = None
        self.detail_window = None
        self.css_provider = None

    def do_activate(self):
        if getattr(self, "window", None):
            self.window.present()
            return
        self.build_window()
        self.refresh_space()
        self.window.present()

    def build_window(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Disk Hız Testi")
        self.window.set_default_size(700, 250)
        self.window.set_size_request(520, 230)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.set_margin_top(10); root.set_margin_bottom(10); root.set_margin_start(10); root.set_margin_end(10)
        self.window.set_child(root)
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("main-card")
        card.set_margin_top(1); card.set_margin_bottom(1)
        root.append(card)
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_hexpand(True)
        card.append(row)
        self.path_label = Gtk.Label(xalign=0)
        self.path_label.set_ellipsize(3)
        self.path_label.set_selectable(True)
        self.path_label.set_hexpand(True)
        self.path_label.add_css_class("path-label")
        row.append(self.path_label)
        self.choose_btn = Gtk.Button(label="Seç…")
        self.choose_btn.connect("clicked", self.choose_folder)
        row.append(self.choose_btn)
        size_values = ["128 MB", "256 MB", "512 MB", "1 GB", "2 GB", "4 GB", "8 GB", "16 GB", "Özel"]
        self.size_drop = Gtk.DropDown.new_from_strings(size_values)
        self.size_drop.set_selected(3)
        self.size_drop.connect("notify::selected", self.size_changed)
        row.append(self.size_drop)
        self.custom_size = Gtk.SpinButton.new_with_range(0.1, 2048.0, 0.1)
        self.custom_size.set_digits(2); self.custom_size.set_value(1.0); self.custom_size.set_width_chars(7)
        self.custom_size.set_tooltip_text("Test boyutu (GB)")
        self.custom_size.connect("value-changed", lambda *_: self.refresh_space())
        self.custom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.custom_box.append(self.custom_size)
        self.custom_box.append(Gtk.Label(label="GB"))
        self.custom_box.set_visible(False)
        row.append(self.custom_box)
        self.keep_check = Gtk.CheckButton(label="Bırak")
        self.keep_check.set_tooltip_text("Test dosyasını silme")
        row.append(self.keep_check)
        self.details_btn = Gtk.Button(label="Detaylar…")
        self.details_btn.set_tooltip_text("Seçili diskin ayrıntılarını göster")
        self.details_btn.connect("clicked", self.open_details)
        row.append(self.details_btn)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        body.set_margin_top(4)
        card.append(body)
        self.metrics = {}
        for key, title in (("write", "Yazma"), ("read", "Okuma")):
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_hexpand(True)
            body.append(col)
            label = Gtk.Label(label=title, xalign=0); label.add_css_class("secondary")
            col.append(label)
            value = Gtk.Label(label="—", xalign=0); value.add_css_class("speed-value")
            col.append(value)
            avg = Gtk.Label(label="", xalign=0); avg.add_css_class("secondary")
            col.append(avg)
            bar = Gtk.ProgressBar(); bar.set_fraction(0); bar.set_hexpand(True)
            col.append(bar)
            self.metrics[key] = (value, avg, bar)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_valign(Gtk.Align.CENTER)
        body.append(actions)
        self.cancel_btn = Gtk.Button(label="İptal")
        self.cancel_btn.add_css_class("destructive-action")
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.connect("clicked", self.cancel_test)
        actions.append(self.cancel_btn)
        self.start_btn = Gtk.Button(label="Başlat")
        self.start_btn.add_css_class("suggested-action")
        self.start_btn.connect("clicked", self.start_test)
        actions.append(self.start_btn)

        self.summary_label = Gtk.Label(xalign=0)
        self.summary_label.set_ellipsize(3); self.summary_label.add_css_class("secondary")
        card.append(self.summary_label)
        self.status_label = Gtk.Label(label="", xalign=0)
        self.status_label.set_ellipsize(3); self.status_label.set_hexpand(True)
        card.append(self.status_label)
        self.install_css()
        self.path_label.set_text(self.path)
        self.window.connect("close-request", self.on_close)

    def install_css(self):
        display = Gdk.Display.get_default()
        if not display:
            return
        dark = False
        try:
            settings = Gtk.Settings.get_default()
            theme_name = (settings.get_property("gtk-theme-name") or "").lower()
            dark = settings.get_property("gtk-application-prefer-dark-theme") or "dark" in theme_name
        except Exception:
            pass
        if dark:
            bg, card, fg, secondary, border, button, hover = "#31363b", "#232629", "#eff0f1", "#a0a6ad", "#4a4f54", "#3a3f45", "#454b52"
            accent_text = "#1b1e20"
        else:
            bg, card, fg, secondary, border, button, hover = "#f7f7f7", "#ffffff", "#232629", "#707d8a", "#d8dadd", "#eff0f1", "#dfe1e3"
            accent_text = "#ffffff"
        css = f'''window {{ background: {bg}; color: {fg}; }}
        .main-card, .info-card {{ background: {card}; border: 1px solid {border}; border-radius: 8px; padding: 12px; }}
        label {{ color: {fg}; }} .secondary {{ color: {secondary}; font-size: 11px; }}
        .path-label {{ color: #2980b9; }} .speed-value {{ font-size: 22px; font-weight: 700; }}
        button, dropdown, spinbutton {{ min-height: 28px; border-radius: 4px; }}
        button {{ background: {button}; border: 1px solid {border}; }} button:hover {{ background: {hover}; }}
        button.suggested-action {{ background: #3daee9; color: {accent_text}; }}
        button.suggested-action:hover {{ background: {'#58b9e9' if dark else '#299dd4'}; }}
        button.destructive-action {{ color: #da4453; }}
        progressbar trough {{ min-height: 5px; background: {'#41474d' if dark else '#dcdfe3'}; }}
        progressbar progress {{ background: #3daee9; }}
        .section-title {{ color: #3daee9; font-weight: 700; }} .health-good {{ color: #27ae60; font-weight: 700; }}
        .health-bad {{ color: #da4453; font-weight: 700; }} .detail-value {{ font-weight: 700; }}'''
        self.css_provider = Gtk.CssProvider()
        self.css_provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(display, self.css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def choose_folder(self, *_):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Test klasörü seç")
        dialog.select_folder(self.window, None, self.folder_selected, None)

    def folder_selected(self, dialog, result, _data):
        try:
            file = dialog.select_folder_finish(result)
            if file:
                self.path = file.get_path()
                self.path_label.set_text(self.path)
                self.path_label.set_tooltip_text(self.path)
                self.refresh_space()
        except GLib.Error:
            pass

    def size_gib(self):
        idx = self.size_drop.get_selected()
        fixed = [128 / 1024, 256 / 1024, 512 / 1024, 1, 2, 4, 8, 16]
        if idx == 8:
            return self.custom_size.get_value()
        return fixed[idx] if idx < len(fixed) else 1

    def size_changed(self, *_):
        custom = self.size_drop.get_selected() == 8
        self.custom_box.set_visible(custom)
        self.refresh_space()

    def refresh_space(self):
        if not hasattr(self, "summary_label"):
            return
        info = block_info(self.path)
        free, _, _ = space_for(self.path)
        need = int(self.size_gib() * GIB * 1.05)
        mode = "doğrudan I/O" if info.get("device") and not info.get("usb") else "önbellekli I/O"
        text = f"{info.get('name', 'bilinmiyor')} · {info.get('fs', '?')} · boş: {human_bytes(free)} · gerekli: ~{human_bytes(need)} · {mode}"
        self.summary_label.set_text(text)
        self.summary_label.set_tooltip_text(text)
        self.summary_label.remove_css_class("health-bad")
        if free is not None and free < need:
            self.summary_label.add_css_class("health-bad")

    def alert(self, title, message, kind=Gtk.MessageType.WARNING):
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True, message_type=kind,
                                   buttons=Gtk.ButtonsType.CLOSE, text=title)
        dialog.format_secondary_text(message)
        dialog.connect("response", lambda d, _r: d.destroy())
        dialog.present()

    def start_test(self, *_):
        if self.running:
            return
        if not os.path.isdir(self.path):
            self.alert("Geçersiz klasör", "Seçilen konum bir klasör değil.")
            return
        if not os.access(self.path, os.W_OK | os.X_OK):
            self.alert("Yazma izni yok", f"{self.path} konumuna yazılamıyor. Yazılabilir bir konum seçin.")
            return
        total = int(self.size_gib() * GIB)
        total = max(4096, ((total + 4095) // 4096) * 4096)
        free, _, _ = space_for(self.path)
        need = int(total * 1.05)
        if free is not None and free < need:
            self.alert("Yetersiz boş alan", f"Gereken: ~{human_bytes(need)}\nBoş: {human_bytes(free)}")
            return
        self.running = True
        self.cancel_event.clear()
        self.keep_file = self.keep_check.get_active()
        self.results = {"write": None, "read": None}
        for value, avg, bar in self.metrics.values():
            value.set_text("—"); avg.set_text(""); bar.set_fraction(0)
        self.status_label.set_text("Test başladı…")
        self.start_btn.set_sensitive(False); self.cancel_btn.set_sensitive(True)
        threading.Thread(target=self.run_test, args=(total,), daemon=True).start()

    def cancel_test(self, *_):
        if self.running:
            self.cancel_event.set()
            self.cancel_btn.set_sensitive(False)
            self.status_label.set_text("İptal ediliyor…")

    def ui(self, fn, *args):
        GLib.idle_add(lambda: (fn(*args), GLib.SOURCE_REMOVE)[1])

    def set_status(self, text):
        self.status_label.set_text(text.replace("\n", " · "))

    def progress(self, stage, done, total, avg, instant):
        value, average, bar = self.metrics[stage]
        bar.set_fraction(min(1.0, done / total))
        value.set_text(speed_text(instant))
        average.set_text("ort. " + speed_text(avg))
        self.status_label.set_text(f"{'Yazma' if stage == 'write' else 'Okuma'}: {tr_number(done / MIB)} / {tr_number(total / MIB)} MB")

    def run_test(self, total):
        path = os.path.join(self.path, TEMP_NAME)
        keep = self.keep_file
        try:
            if os.path.lexists(path):
                if os.path.islink(path) or not os.path.isfile(path):
                    raise OSError(errno.EINVAL, "Önceki test dosyası güvenli bir normal dosya değil", path)
                os.unlink(path)
            info = block_info(self.path)
            direct = bool(info.get("device") and not info.get("usb"))
            block = 256 * 1024 if info.get("usb") else 8 * MIB
            block = max(4096, block // 4096 * 4096)
            try:
                write_result, mode = self.measure(path, total, block, "write", direct)
            except OSError as e:
                if direct and e.errno in (errno.EINVAL, errno.EOPNOTSUPP, errno.EPERM, errno.EINVAL):
                    direct = False
                    write_result, mode = self.measure(path, total, block, "write", False)
                else:
                    raise
            self.results["write"] = write_result
            self.direct = mode
            if self.cancel_event.is_set():
                raise InterruptedError()
            # Hint the kernel to discard file cache without affecting global caches.
            try:
                fd = os.open(path, os.O_RDONLY)
                if hasattr(os, "posix_fadvise"):
                    os.posix_fadvise(fd, 0, total, os.POSIX_FADV_DONTNEED)
                os.close(fd)
            except OSError:
                pass
            try:
                read_result, read_mode = self.measure(path, total, block, "read", direct)
            except OSError as e:
                if direct and e.errno in (errno.EINVAL, errno.EOPNOTSUPP, errno.EPERM):
                    direct = False
                    read_result, read_mode = self.measure(path, total, block, "read", False)
                else:
                    raise
            self.results["read"] = read_result
            self.direct = self.direct and read_mode
            write_result["elapsed"]
            msg = f"Yazma: {write_result['elapsed']:.2f} sn · Okuma: {read_result['elapsed']:.2f} sn · "
            msg += "doğrudan I/O ile ölçüldü (önbellek hariç)" if self.direct else "önbellekli I/O; yazma hızı diske yazma beklemesini içerir"
            self.ui(self.finish_test, "success", msg)
        except InterruptedError:
            self.ui(self.finish_test, "cancel", "İptal edildi.")
        except OSError as e:
            self.ui(self.finish_test, "error", f"Disk hatası: {e.strerror or str(e)}")
        except Exception as e:
            self.ui(self.finish_test, "error", f"Beklenmeyen hata: {e}")
        finally:
            if not keep:
                try:
                    if os.path.isfile(path) and not os.path.islink(path):
                        os.unlink(path)
                except OSError:
                    pass

    def measure(self, path, total, block, stage, direct):
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC if stage == "write" else os.O_RDONLY
        if direct:
            flags |= getattr(os, "O_DIRECT", 0)
        fd = os.open(path, flags, 0o600)
        aligned = mmap.mmap(-1, block)
        view = memoryview(aligned)
        start = time.monotonic(); last_ui = 0; done = 0; samples = []
        try:
            while done < total:
                if self.cancel_event.is_set():
                    raise InterruptedError()
                n = min(block, total - done)
                if stage == "write":
                    aligned[:n] = os.urandom(n)
                    wrote = 0
                    while wrote < n:
                        wrote += os.write(fd, view[wrote:n])
                else:
                    got = 0
                    while got < n:
                        count = os.readv(fd, [view[got:n]])
                        if count == 0:
                            raise OSError(errno.EIO, "Beklenmeyen dosya sonu")
                        got += count
                done += n
                now = time.monotonic(); elapsed = max(now - start, 0.000001)
                samples.append((now, done))
                while samples and now - samples[0][0] > 0.75:
                    samples.pop(0)
                window_rate = (done - samples[0][1]) / max(now - samples[0][0], .001) if len(samples) > 1 else done / elapsed
                avg = done / elapsed
                if now - last_ui >= .25 or done >= total:
                    self.ui(self.progress, stage, done, total, avg, window_rate)
                    last_ui = now
            elapsed = max(time.monotonic() - start, .000001)
            if stage == "write":
                os.fsync(fd)
                elapsed = max(time.monotonic() - start, .000001)
            stable = window_rate if done > 0 else 0
            return {"average": done / elapsed, "stable": stable, "elapsed": elapsed}, direct
        finally:
            view.release()
            aligned.close()
            os.close(fd)

    def finish_test(self, state, message):
        self.running = False
        self.start_btn.set_sensitive(True); self.cancel_btn.set_sensitive(False)
        if state == "success":
            for key, result in self.results.items():
                if result:
                    value, avg, bar = self.metrics[key]
                    value.set_text(speed_text(result["stable"]))
                    avg.set_text("ort. " + speed_text(result["average"]))
                    bar.set_fraction(1)
            self.set_status(message)
        elif state == "cancel":
            for value, avg, bar in self.metrics.values():
                bar.set_fraction(0)
            # Keep only completed stages.
            for key, result in self.results.items():
                if result:
                    value, avg, _bar = self.metrics[key]
                    value.set_text(speed_text(result["stable"]))
                    avg.set_text("ort. " + speed_text(result["average"]))
                else:
                    value, avg, _bar = self.metrics[key]
                    value.set_text("—"); avg.set_text("")
            self.set_status(message)
        else:
            for value, avg, bar in self.metrics.values():
                value.set_text("—"); avg.set_text(""); bar.set_fraction(0)
            self.set_status(message)
            self.alert("Test başarısız", message, Gtk.MessageType.ERROR)

    def on_close(self, *_):
        if self.running:
            self.cancel_event.set()
        return False

    def open_details(self, *_):
        self.details_btn.set_sensitive(False); self.details_btn.set_label("Yükleniyor…")
        threading.Thread(target=self.load_details, args=(self.path, None, True), daemon=True).start()

    def load_details(self, path, smart=None, locked=False, root_error=None):
        try:
            result = list_details(path, smart, locked)
            self.ui(self.show_details, path, result, smart, locked, root_error)
        except Exception as e:
            self.ui(self.show_details, path, list_details(path, None, True), None, True, str(e))

    def show_details(self, path, data, smart, locked, root_error):
        self.details_btn.set_sensitive(True); self.details_btn.set_label("Detaylar…")
        info, total, used, pct, groups = data
        if not self.detail_window:
            self.detail_window = Gtk.Window(title="Disk Özeti", transient_for=self.window, modal=True)
            self.detail_window.set_default_size(650, 650)
            outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            outer.set_margin_top(14); outer.set_margin_bottom(12); outer.set_margin_start(14); outer.set_margin_end(14)
            self.detail_window.set_child(outer)
            self.detail_scroller = Gtk.ScrolledWindow(); self.detail_scroller.set_vexpand(True)
            outer.append(self.detail_scroller)
            self.detail_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            self.detail_scroller.set_child(self.detail_content)
            self.detail_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            self.detail_actions.set_halign(Gtk.Align.END); outer.append(self.detail_actions)
            self.detail_close = Gtk.Button(label="Kapat"); self.detail_close.connect("clicked", lambda *_: self.detail_window.hide())
            self.detail_actions.append(self.detail_close)
        child = self.detail_content.get_first_child()
        while child:
            nxt = child.get_next_sibling(); self.detail_content.remove(child); child = nxt
        action_child = self.detail_actions.get_first_child()
        while action_child:
            next_action = action_child.get_next_sibling()
            if action_child is not self.detail_close:
                self.detail_actions.remove(action_child)
            action_child = next_action
        head = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label=info.get("model") if info.get("model") not in (None, "—") else info.get("name", "Disk"), xalign=0)
        title.add_css_class("speed-value"); head.append(title)
        sub = Gtk.Label(label=f"{info.get('kind', 'Bilinmiyor')} · {info.get('fs', '?')}", xalign=0); sub.add_css_class("secondary"); head.append(sub)
        self.detail_content.append(head)
        capacity = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7); capacity.add_css_class("info-card")
        caprow = Gtk.Box(); caprow.append(Gtk.Label(label="Kapasite", xalign=0)); caprow.append(Gtk.Label(label=human_bytes(total), xalign=1))
        caprow.get_last_child().set_hexpand(True); capacity.append(caprow)
        bar = Gtk.ProgressBar(); bar.set_fraction(min(1, used / total) if total else 0); capacity.append(bar)
        capfoot = Gtk.Box(); usedlabel = Gtk.Label(label=f"●  Kullanılan  {human_bytes(used)} · {pct if pct is not None else '—'}%", xalign=0); usedlabel.add_css_class("secondary"); capfoot.append(usedlabel)
        empty = Gtk.Label(label=f"Boş  {human_bytes(total-used if total and used is not None else None)}", xalign=1); empty.add_css_class("secondary"); empty.set_hexpand(True); capfoot.append(empty); capacity.append(capfoot)
        self.detail_content.append(capacity)
        cards = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for label, value in (("Sağlık", (smart or {}).get("health", "Veri yok")), ("Sıcaklık", (smart or {}).get("temperature", "Veri yok")), ("Çalışma süresi", (smart or {}).get("hours", "Veri yok"))):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4); box.set_hexpand(True); box.add_css_class("info-card")
            h = Gtk.Label(label=label, xalign=0); h.add_css_class("secondary"); box.append(h)
            v = Gtk.Label(label=value, xalign=0); v.add_css_class("detail-value"); v.set_ellipsize(3); v.set_tooltip_text(value); box.append(v); cards.append(box)
        self.detail_content.append(cards)
        target = Gtk.Label(label=path, xalign=0); target.add_css_class("secondary"); target.set_selectable(True); target.set_ellipsize(2); target.set_tooltip_text(path); self.detail_content.append(target)
        count = sum(len(fields) for _, fields in groups)
        heading = Gtk.Label(label=f"TÜM AYRINTILAR · {count}", xalign=0); heading.add_css_class("section-title"); self.detail_content.append(heading)
        for group, fields in groups:
            frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); frame.add_css_class("info-card")
            gh = Gtk.Label(label=group, xalign=0); gh.add_css_class("section-title"); frame.append(gh)
            grid = Gtk.Grid(column_spacing=12, row_spacing=10); grid.set_column_homogeneous(True)
            for i, (name, val) in enumerate(fields):
                cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                nm = Gtk.Label(label=name, xalign=0); nm.add_css_class("secondary"); cell.append(nm)
                vl = Gtk.Label(label=str(val), xalign=0); vl.add_css_class("detail-value"); vl.set_wrap(True); vl.set_selectable(True); cell.append(vl)
                grid.attach(cell, i % 2, i // 2, 1, 1)
            frame.append(grid); self.detail_content.append(frame)
        if locked:
            root_btn = Gtk.Button(label="Root olarak göster")
            root_btn.connect("clicked", self.request_root_details)
            root_btn.set_sensitive(bool(info.get("name", "").startswith("/dev/")))
            self.detail_actions.prepend(root_btn)
        if root_error:
            err = Gtk.Label(label=f"SMART bilgisi alınamadı: {root_error}", xalign=0); err.add_css_class("secondary"); self.detail_content.prepend(err)
        self.detail_window.present()

    def request_root_details(self, button):
        button.set_sensitive(False); button.set_label("Yetki bekleniyor…")
        # The authorization dialog is opened only after explicit user action.
        path = self.path
        device = block_info(path).get("name")
        threading.Thread(target=self.root_smart_worker, args=(path, device), daemon=True).start()

    def root_smart_worker(self, path, device):
        smart = None; error = None
        try:
            if not shutil.which("pkexec") or not shutil.which("smartctl"):
                raise RuntimeError("smartctl veya pkexec bulunamadı")
            proc = subprocess.run(["pkexec", "smartctl", "-a", "-j", device], capture_output=True, text=True, timeout=9)
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "Yetkilendirme reddedildi veya SMART sorgusu başarısız oldu")
            raw = json.loads(proc.stdout)
            health = raw.get("smart_status", {}).get("passed")
            attrs = raw.get("ata_smart_attributes", {}).get("table", [])
            hours = next((x.get("raw", {}).get("value") for x in attrs if x.get("name") in ("Power_On_Hours", "Power_On_Hours_And_Msec")), None)
            temp = raw.get("temperature", {}).get("current")
            smart = {"health": "Geçti" if health is True else "Uyarı" if health is False else "Veri yok",
                     "hours": f"{hours} saat" if hours is not None else "Veri yok",
                     "temperature": f"{temp} °C" if temp is not None else "Veri yok",
                     "note": raw.get("smart_status", {}).get("passed", "—")}
        except Exception as e:
            error = str(e)
        data = list_details(path, smart, smart is None)
        self.ui(self.show_details, path, data, smart, smart is None, error)


def main():
    app = DiskSpeedApp()
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
