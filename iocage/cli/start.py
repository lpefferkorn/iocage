"""start module for the cli."""
import logging
from collections import OrderedDict
from operator import itemgetter

import click

from iocage.lib.ioc_json import IOCJson
from iocage.lib.ioc_list import IOCList
from iocage.lib.ioc_start import IOCStart

__cmdname__ = "start_cmd"
__rootcmd__ = True


@click.command(name="start", help="Starts the specified jails or ALL.")
@click.option("--rc", default=False, is_flag=True,
              help="Will start all jails with boot=on, in the specified"
                   " order with smaller value for priority starting first.")
@click.argument("jails", nargs=-1)
def start_cmd(rc, jails):
    """
    Looks for the jail supplied and passes the uuid, path and configuration
    location to start_jail.
    """
    lgr = logging.getLogger('ioc_cli_start')

    _jails, paths = IOCList("uuid").list_datasets()
    jail_order = {}
    boot_order = {}

    for j in _jails:
        path = paths[j]
        conf = IOCJson(path).json_load()
        boot = conf["boot"]
        priority = conf["priority"]

        jail_order[j] = int(priority)

        # This removes having to grab all the JSON again later.
        if boot == "on":
            boot_order[j] = int(priority)

    jail_order = OrderedDict(sorted(jail_order.items(),
                                    key=itemgetter(1)))
    boot_order = OrderedDict(sorted(boot_order.items(),
                                    key=itemgetter(1)))
    if rc:
        for j in boot_order.keys():
            uuid = _jails[j]
            path = paths[j]
            conf = IOCJson(path).json_load()
            status, _ = IOCList().list_get_jid(uuid)

            if not status:
                lgr.info("  Starting {} ({})".format(uuid, j))
                IOCStart(uuid, j, path, conf, silent=True)
            else:
                lgr.info("{} ({}) is already running!".format(uuid, j))
        exit()

    if len(jails) >= 1 and jails[0] == "ALL":
        if len(_jails) < 1:
            raise RuntimeError("No jails exist to start!")

        for j in jail_order:
            uuid = _jails[j]
            path = paths[j]

            conf = IOCJson(path).json_load()
            IOCStart(uuid, j, path, conf)
    else:
        if len(jails) < 1:
            raise RuntimeError("Please specify either one or more jails or "
                               "ALL!")

        for jail in jails:
            _jail = {tag: uuid for (tag, uuid) in _jails.items() if
                     uuid.startswith(jail) or tag == jail}

            if len(_jail) == 1:
                tag, uuid = next(iter(_jail.items()))
                path = paths[tag]
            elif len(_jail) > 1:
                lgr.error("Multiple jails found for"
                          " {}:".format(jail))
                for t, u in sorted(_jail.items()):
                    lgr.error("  {} ({})".format(u, t))
                raise RuntimeError()
            else:
                raise RuntimeError("{} not found!".format(jail))

            conf = IOCJson(path).json_load()

            if conf["type"] in ("jail", "plugin"):
                IOCStart(uuid, tag, path, conf)
            elif conf["type"] == "basejail":
                raise RuntimeError(
                    "Please run \"iocage migrate\" before trying"
                    " to start {} ({})".format(uuid, tag))
            elif conf["type"] == "template":
                raise RuntimeError(
                    "Please convert back to a jail before trying"
                    " to start {} ({})".format(uuid, tag))
            else:
                raise RuntimeError("{} is not a supported jail type.".format(
                    conf["type"]
                ))
