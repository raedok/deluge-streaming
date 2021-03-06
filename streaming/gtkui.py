#
# gtkui.py
#
# Copyright (C) 2009 John Doee <johndoee@tidalstream.org>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
#     The Free Software Foundation, Inc.,
#     51 Franklin Street, Fifth Floor
#     Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import gtk
import os
import subprocess
import sys

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.ui.gtkui import dialogs
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from twisted.internet import defer, threads

from common import get_resource


def execute_url(url):
    if sys.platform == 'win32':
        os.startfile(url)
    elif sys.platform == 'darwin':
        subprocess.Popen(['open', url])
    else:
        try:
            subprocess.Popen(['xdg-open', url])
        except OSError:
            print 'Unable to open URL %s' % (url, )

def execute_mpv(url):
    if sys.platform == 'win32':
        os.startfile(url)
    elif sys.platform == 'darwin':
        subprocess.Popen(['/usr/local/bin/mpv', url])
    else:
        try:
            subprocess.Popen(['xdg-open', url])
        except OSError:
            print 'Unable to open URL %s' % (url, )


class GtkUI(GtkPluginBase):
    def get_widget(self, widget_name):
        main_window = component.get("MainWindow")
        if hasattr(main_window, 'main_glade'):
            return main_window.main_glade.get_widget(widget_name)
        else:
            return main_window.main_builder.get_object(widget_name)

def enable(self):
    self.glade = gtk.glade.XML(get_resource("config.glade"))
    
    component.get("Preferences").add_page("Streaming", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)
        
        file_menu = self.get_widget('menu_file_tab')
        
        self.sep = gtk.SeparatorMenuItem()
        self.item = gtk.MenuItem(_("_Stream this file"))
        self.item.connect("activate", self.on_menuitem_stream)
        
        file_menu.append(self.sep)
        file_menu.append(self.item)
        
        self.sep.show()
        self.item.show()
        
        torrentmenu = component.get("MenuBar").torrentmenu
        
        self.sep_torrentmenu = gtk.SeparatorMenuItem()
        self.item_torrentmenu = gtk.MenuItem(_("_Stream this torrent"))
        self.item_torrentmenu.connect("activate", self.on_torrentmenu_menuitem_stream)
        
        torrentmenu.append(self.sep_torrentmenu)
        torrentmenu.append(self.item_torrentmenu)
        
        self.sep_torrentmenu.show()
        self.item_torrentmenu.show()
    
    def disable(self):
        component.get("Preferences").remove_page("Streaming")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)
        
        file_menu = self.get_widget('menu_file_tab')
        
        file_menu.remove(self.item)
        file_menu.remove(self.sep)
        
        torrentmenu = component.get("MenuBar").torrentmenu
        
        torrentmenu.remove(self.item_torrentmenu)
        torrentmenu.remove(self.sep_torrentmenu)

@defer.inlineCallbacks
    def on_apply_prefs(self):
        log.debug("applying prefs for Streaming")
        
        if self.glade.get_widget("input_serve_standalone").get_active():
            serve_method = 'standalone'
        elif self.glade.get_widget("input_serve_webui").get_active():
            serve_method = 'webui'
        
        if self.glade.get_widget("input_ssl_cert_daemon").get_active():
            ssl_source = 'daemon'
        elif self.glade.get_widget("input_ssl_cert_custom").get_active():
            ssl_source = 'custom'
        
        config = {
            "ip": self.glade.get_widget("input_ip").get_text(),
            "port": int(self.glade.get_widget("input_port").get_text()),
            "use_stream_urls": self.glade.get_widget("input_use_stream_urls").get_active(),
            "auto_open_stream_urls": self.glade.get_widget("input_auto_open_stream_urls").get_active(),
            "allow_remote": self.glade.get_widget("input_allow_remote").get_active(),
            "download_only_streamed": self.glade.get_widget("input_download_only_streamed").get_active(),
            "use_ssl": self.glade.get_widget("input_use_ssl").get_active(),
            "remote_username": self.glade.get_widget("input_remote_username").get_text(),
            "remote_password": self.glade.get_widget("input_remote_password").get_text(),
            "ssl_priv_key_path": self.glade.get_widget("input_ssl_priv_key_path").get_text(),
            "ssl_cert_path": self.glade.get_widget("input_ssl_cert_path").get_text(),
            "serve_method": serve_method,
            "ssl_source": ssl_source,
        }
        
        result = yield client.streaming.set_config(config)
        
        if result:
            message_type, message_class, message = result
            if message_type == 'error':
                topic = 'Unknown error type'
                if message_class == 'ssl':
                    topic = 'SSL Failed'
                
                dialogs.ErrorDialog(topic, message).run()

def on_show_prefs(self):
    client.streaming.get_config().addCallback(self.cb_get_config)
    
    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.glade.get_widget("input_ip").set_text(config["ip"])
        self.glade.get_widget("input_port").set_text(str(config["port"]))
        self.glade.get_widget("input_use_stream_urls").set_active(config["use_stream_urls"])
        self.glade.get_widget("input_auto_open_stream_urls").set_active(config["auto_open_stream_urls"])
        self.glade.get_widget("input_allow_remote").set_active(config["allow_remote"])
        self.glade.get_widget("input_use_ssl").set_active(config["use_ssl"])
        self.glade.get_widget("input_download_only_streamed").set_active(config["download_only_streamed"])
        self.glade.get_widget("input_remote_username").set_text(config["remote_username"])
        self.glade.get_widget("input_remote_password").set_text(config["remote_password"])
        self.glade.get_widget("input_ssl_priv_key_path").set_text(config["ssl_priv_key_path"])
        self.glade.get_widget("input_ssl_cert_path").set_text(config["ssl_cert_path"])
        
        self.glade.get_widget("input_serve_standalone").set_active(config["serve_method"] == "standalone")
        self.glade.get_widget("input_serve_webui").set_active(config["serve_method"] == "webui")
        
        self.glade.get_widget("input_ssl_cert_daemon").set_active(config["ssl_source"] == "daemon")
        self.glade.get_widget("input_ssl_cert_custom").set_active(config["ssl_source"] == "custom")
        
        api_url = 'http%s://%s:%s/streaming/stream' % (('s' if config["use_ssl"] else ''), config["ip"], config["port"])
        self.glade.get_widget("output_remote_url").set_text(api_url)
    
    def stream_ready(self, result):
        if result['status'] == 'success':
            threads.deferToThread(execute_mpv, result['url'])

def on_menuitem_stream(self, data=None):
    torrent_id = component.get("TorrentView").get_selected_torrents()[0]
    
    ft = component.get("TorrentDetails").tabs['Files']
        paths = ft.listview.get_selection().get_selected_rows()[1]
        
        selected = []
        for path in paths:
            selected.append(ft.treestore.get_iter(path))
        
        for select in selected:
            path = ft.get_file_path(select)
            client.streaming.stream_torrent(infohash=torrent_id, filepath_or_index=path, includes_name=True).addCallback(self.stream_ready)
            break

def on_torrentmenu_menuitem_stream(self, data=None):
    torrent_id = component.get("TorrentView").get_selected_torrents()[0]
    client.streaming.stream_torrent(infohash=torrent_id).addCallback(self.stream_ready)
