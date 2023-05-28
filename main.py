#!/usr/bin/env python3
import os
import pathlib
import subprocess
import sys
from typing import List
from xml.etree import ElementTree

import pynvim
from dasbus.connection import SessionMessageBus

bus = SessionMessageBus()


def get_subnodes_from_xml(xml: str) -> List[str]:
    nodes: List[str] = []
    root = ElementTree.fromstring(xml)
    for child in root:
        if child.tag != "node":
            continue
        nodes.append(child.attrib.get("name"))

    return nodes


def get_dbus_names():
    proxy = bus.get_proxy("org.freedesktop.DBus", "/org/freedesktop/DBus")
    return proxy.ListNames()


def get_konsole_sessions(service_name: str) -> List[str]:
    proxy = bus.get_proxy(service_name, "/Sessions", "org.freedesktop.DBus.Introspectable")
    xml = proxy.Introspect()
    return get_subnodes_from_xml(xml)


def get_konsole_windows(service_name: str) -> List[str]:
    proxy = bus.get_proxy(service_name, "/Windows", "org.freedesktop.DBus.Introspectable")
    xml = proxy.Introspect()
    return get_subnodes_from_xml(xml)


def window_set_default_profile(service_name: str, window: str, default_profile: str):
    proxy = bus.get_proxy(service_name, f"/Windows/{window}", "org.kde.konsole.Window")
    print(f"Current default profile: {proxy.defaultProfile()}")
    proxy.setDefaultProfile(default_profile)


def session_set_profile(service_name: str, session: str, profile: str):
    proxy = bus.get_proxy(service_name, f"/Sessions/{session}", "org.kde.konsole.Session")
    print(f"Current profile: {proxy.profile()}")
    proxy.setProfile(profile)


def konsole_set_profile(service_name: str, profile: str):
    windows = get_konsole_windows(service_name)
    for window in windows:
        window_set_default_profile(service_name, window, profile)

    sessions = get_konsole_sessions(service_name)
    for session in sessions:
        session_set_profile(service_name, session, profile)


def global_theme_set(profile: str):
    if profile == "Light":
        plasma_theme = "org.kde.breeze.desktop"
    elif profile == "Dark":
        plasma_theme = "org.kde.breezedark.desktop"
    else:
        raise RuntimeError(f"Unhandled theme: {profile}")
    subprocess.check_call(["lookandfeeltool", "--apply", plasma_theme])


def nvim_config_reload():
    for nvim_instance in pathlib.Path(os.getenv("XDG_RUNTIME_DIR")).glob("nvim*"):
        nvim = pynvim.attach('socket', path=nvim_instance)
        nvim.command('source $MYVIMRC')


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} PROFILE")
        sys.exit(1)
    profile = sys.argv[1]

    # Service name is "org.kde.konsole-$pid"
    konsole_services = filter(lambda x: "org.kde.konsole-" in x, get_dbus_names())
    for service_name in konsole_services:
        konsole_set_profile(service_name, profile)

    konsole_set_profile("org.kde.yakuake", profile)

    nvim_config_reload()

    global_theme_set(profile)


if __name__ == '__main__':
    main()
