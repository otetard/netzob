# -*- coding: utf-8 -*-

#+---------------------------------------------------------------------------+
#|          01001110 01100101 01110100 01111010 01101111 01100010            |
#|                                                                           |
#|               Netzob : Inferring communication protocols                  |
#+---------------------------------------------------------------------------+
#| Copyright (C) 2011 Georges Bossert and Frédéric Guihéry                   |
#| This program is free software: you can redistribute it and/or modify      |
#| it under the terms of the GNU General Public License as published by      |
#| the Free Software Foundation, either version 3 of the License, or         |
#| (at your option) any later version.                                       |
#|                                                                           |
#| This program is distributed in the hope that it will be useful,           |
#| but WITHOUT ANY WARRANTY; without even the implied warranty of            |
#| MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              |
#| GNU General Public License for more details.                              |
#|                                                                           |
#| You should have received a copy of the GNU General Public License         |
#| along with this program. If not, see <http://www.gnu.org/licenses/>.      |
#+---------------------------------------------------------------------------+
#| @url      : http://www.netzob.org                                         |
#| @contact  : contact@netzob.org                                            |
#| @sponsors : Amossys, http://www.amossys.fr                                |
#|             Supélec, http://www.rennes.supelec.fr/ren/rd/cidre/           |
#+---------------------------------------------------------------------------+

#+----------------------------------------------
#| Global Imports
#+----------------------------------------------
import gtk
import pygtk
import uuid
import datetime
from bitarray import bitarray
from netzob.Import.ThirdParties.OSpy import OSpy
pygtk.require('2.0')
import logging
import os
import random

#+----------------------------------------------
#| Local Imports
#+----------------------------------------------
from netzob.Common.Type.TypeConvertor import TypeConvertor
from netzob.Common.Models.FileMessage import FileMessage
from netzob.Common.Models.Factories.FileMessageFactory import FileMessageFactory
from netzob.Common.ProjectConfiguration import ProjectConfiguration
from netzob.Common.EnvironmentalDependencies import EnvironmentalDependencies
from netzob.Import.AbstractImporter import AbstractImporter
from netzob.Import.ThirdParties.AbstractThirdPartyImporter import AbstractThirdPartyImporter


#+----------------------------------------------
#| ThirdPartyImport:
#|     GUI for importing messages from any other tools
#+----------------------------------------------
class ThirdPartyImport(AbstractImporter):

    def new(self):
        pass

    def update(self):
        pass

    def clear(self):
        pass

    def kill(self):
        pass

    #+----------------------------------------------
    #| Constructor:
    #+----------------------------------------------
    def __init__(self, netzob):
        AbstractImporter.__init__(self, "THIRD PARTY IMPORT")
        self.netzob = netzob

        # create the environmental dependancy object
        self.envDeps = EnvironmentalDependencies()

        # create logger with the given configuration
        self.log = logging.getLogger('netzob.Import.ThirdPartyImporter.py')
        self.messages = []

        ospyImporter = OSpy()

        # Creates the list of third parties
        self.thirdParties = [ospyImporter]
        self.plugins = []
        # Load plugins
        for plugin in self.thirdParties:
            self.plugins.append(plugin)

        self.init()

        self.dialog = gtk.Dialog(title="Import data from third parties", flags=0, buttons=None)
        self.dialog.show()
        self.dialog.vbox.pack_start(self.getPanel(), True, True, 0)
        self.dialog.set_size_request(1000, 600)

    def init(self):
        self.fileName = ""
        self.thirdParty = ""

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Main panel
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        self.panel = gtk.Table(rows=10, columns=8, homogeneous=True)
        self.panel.show()

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Select a file
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        label_selectSource = gtk.Label("Select data source")
        label_selectSource.show()

        entry_filepath = gtk.Entry()
        entry_filepath.set_text("")
        entry_filepath.show()

        but_source = gtk.Button("...")
        but_source.show()
        but_source.connect("clicked", self.selectFiles, entry_filepath)

        self.panel.attach(label_selectSource, 0, 1, 0, 1, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)
        self.panel.attach(entry_filepath, 1, 5, 0, 1, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)
        self.panel.attach(but_source, 5, 6, 0, 1, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Select a third party
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        label_thirdParty = gtk.Label("Select a third party")
        label_thirdParty.show()
        self.thirdPartyStore = gtk.combo_box_entry_new_text()
        self.thirdPartyStore.show()
        self.thirdPartyStore.set_size_request(500, -1)
        self.thirdPartyStore.set_model(gtk.ListStore(str))

        # register all the available plugins
        for plugin in self.plugins:
            self.thirdPartyStore.append_text(plugin.getName())

        but_import = gtk.Button("Load")
        but_import.show()
        but_import.connect("clicked", self.load_file, entry_filepath)

        self.panel.attach(label_thirdParty, 0, 1, 1, 2, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)
        self.panel.attach(self.thirdPartyStore, 1, 5, 1, 2, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)
        self.panel.attach(but_import, 5, 6, 1, 2, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # File details
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        scroll = gtk.ScrolledWindow()
        self.textview = gtk.TextView()
        self.textview.show()
        self.textview.get_buffer().create_tag("normalTag", family="Courier")

        scroll.add(self.textview)
        scroll.show()
        scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.panel.attach(scroll, 0, 6, 2, 10, xoptions=gtk.FILL | gtk.EXPAND, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)

        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Extracted data
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        scroll2 = gtk.ScrolledWindow()
        self.lineView = gtk.TreeView(gtk.TreeStore(str, str))  # line number, content
        self.lineView.get_selection().set_mode(gtk.SELECTION_SINGLE)
        self.lineView.connect('button-press-event', self.button_press_on_message)
        cell = gtk.CellRendererText()
        # Col file descriptor
        column = gtk.TreeViewColumn('Message ID')
        column.pack_start(cell, True)
        column.set_attributes(cell, text=0)
        self.lineView.append_column(column)
        self.lineView.show()

        scroll2.add(self.lineView)
        scroll2.show()
        scroll2.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.panel.attach(scroll2, 6, 8, 0, 10, xoptions=gtk.FILL, yoptions=gtk.FILL | gtk.EXPAND, xpadding=5, ypadding=5)

        # Button select packets for further analysis
        but = gtk.Button(label="Import")
        but.show()
        but.connect("clicked", self.import_file)
        self.panel.attach(but, 2, 3, 10, 11, xoptions=0, yoptions=0, xpadding=5, ypadding=5)

    def button_press_on_message(self, treeview, event):
        x = int(event.x)
        y = int(event.y)

        info = treeview.get_path_at_pos(x, y)
        idMessage = None
        if info is not None:
            path = info[0]
            iter = treeview.get_model().get_iter(path)
            idMessage = str(treeview.get_model().get_value(iter, 0))

        if idMessage == None:
            return

        # Search for the selected message
        selectedMessage = None
        for message in self.messages:
            if str(message.getID()) == idMessage:
                selectedMessage = message

        if selectedMessage == None:
            self.log.warn("Impossible to retrieve the message the user clicked on. Hum ?")
            return

        self.displayMessage(selectedMessage)

    def load_file(self, button, entryPath):
        # First we retrieve the provided files
        filesToBeImported = []

        # Computes the selected file(s)
        strPaths = entryPath.get_text().split(";")
        for strPath in strPaths:
            filename = unicode(strPath, "utf-8")
            if filename != None and filename != "" and os.path.isfile(filename):
                filesToBeImported.append(filename)
            else:
                logging.warning("Cannot load file {0}, its not a file.".filename)

        # Start to load
        parsedMessages = self.loadMessagesFromPlugin(self.thirdPartyStore.get_active_text(), filesToBeImported)

        if parsedMessages == None:
            logging.warning("Impossible to find a plugin to import data from.")
        else:
            logging.debug("A number of {0} messages were extracted.".format(len(parsedMessages)))
            for message in parsedMessages:
                self.messages.append(message)
                self.lineView.get_model().append(None, [message.getID(), message.getData()])

                # We clean the display
                self.textview.get_buffer().insert_with_tags_by_name(self.textview.get_buffer().get_start_iter(), "", "normalTag")

    def loadMessagesFromPlugin(self, pluginName, files):
        for plugin in self.plugins:
            if plugin.getName() == pluginName:
                return plugin.parse(files)
        return None

    #+----------------------------------------------
    #| Called when user select a list of packet
    #+----------------------------------------------
    def import_file(self, button):
        currentProject = self.netzob.getCurrentProject()

        # We ask the confirmation
        dialog = gtk.MessageDialog(None,
                               gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_QUESTION,
                               gtk.BUTTONS_OK_CANCEL,
                               "Are you sure to import the " + str(len(self.messages)) + " computed messages in project " + currentProject.getName() + ".")

        # Checkbox for session
        vbox = gtk.VBox()
        vbox.show()
        hbox = gtk.HBox()
        hbox.show()
        vbox.pack_start(hbox)
        isSession = gtk.CheckButton("Check if this trace is a session")
        isSession.set_active(False)
        isSession.show()
#        hbox.pack_start(isSession)

        dialog.vbox.pack_end(vbox, True, True, 0)
        resp = dialog.run()
        dialog.destroy()

        if resp == gtk.RESPONSE_OK:
            self.saveMessagesInProject(self.netzob.getCurrentWorkspace(), currentProject, self.messages)
            self.dialog.destroy()
            # We update the gui
            self.netzob.update()

    #+----------------------------------------------
    #| Called when user import files
    #+----------------------------------------------
    def selectFiles(self, button, label):
        aFile = ""
        chooser = gtk.FileChooserDialog(title="Select one or multiple file", action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                        buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(True)

        filesToBeImported = []

        # Computes the selected file(s)
        res = chooser.run()
        if res == gtk.RESPONSE_OK:
            for filename in chooser.get_filenames():
                filename = unicode(filename, "utf-8")
                if filename != None and filename != "" and os.path.isfile(filename):
                    filesToBeImported.append(filename)
        chooser.destroy()

        # We update the label with the list of the selected files
        label.set_text(";".join(filesToBeImported))

    #+----------------------------------------------
    #| Retrieve messages from files
    #+----------------------------------------------
    def retrieveMessagesFromFiles(self):
        # We capture the current environment
        self.envDeps.captureEnvData()

        # We read each file and create one message for each file
        fileNumber = 0
        self.messages = []
        self.lineView.get_model().clear()

        for file in self.filesToBeImported:
            # Extraction of the metadata
            fileName = file.strip()
            size = os.path.getsize(file)
            creationDate = datetime.datetime.fromtimestamp(os.path.getctime(file))
            modificationDate = datetime.datetime.fromtimestamp(os.path.getmtime(file))
            owner = "none"

            # Retrieve the binary content of the file
            content = self.getNetzobRawContentOfFile(file)
            if not len(content) > 0:
                continue

            # Create a message
            message = FileMessage(uuid.uuid4(), 0, content, fileName, creationDate, modificationDate, owner, size, 0)
            self.messages.append(message)
            self.lineView.get_model().append(None, [message.getID(), content])
            fileNumber += 1

        # We clean the display
        self.textview.get_buffer().insert_with_tags_by_name(self.textview.get_buffer().get_start_iter(), "", "normalTag")

    def getNetzobRawContentOfFile(self, filename):
        file = open(filename, "rb")
        content = file.read()
        file.close()
        return TypeConvertor.stringToNetzobRaw(content)

    def entry_separator_callback(self, widget, entry):
        entry_text = widget.get_text()
        self.lineSeparator = entry_text
        self.updateMessageList()

    def updateMessageList(self):
        # We read each file and create one message for each file
        fileNumber = 0

        # We split the content of each message and retrieve new messages
        self.retrieveMessagesFromFiles()
        new_messages = []
        for message in self.messages:
            lineNumber = 0
            if len(self.lineSeparator) > 0:
                splittedStrHexData = message.getData().split(self.lineSeparator)
            else:
                splittedStrHexData = [message.getData()]
            for s in splittedStrHexData:
                if len(s) > 0:
                    message = FileMessage(uuid.uuid4(), 0, s, message.getFilename(), message.getCreationDate(), message.getModificationDate(), message.getOwner(), message.getSize(), lineNumber)
                    new_messages.append(message)
                    lineNumber += 1

        # We save the new messages
        self.messages = []
        self.messages.extend(new_messages)
        self.lineView.get_model().clear()
        for message in self.messages:
            self.lineView.get_model().append(None, [message.getID(), message.getData()])
        # We clean the display
        self.textview.get_buffer().delete(self.textview.get_buffer().get_start_iter(), self.textview.get_buffer().get_end_iter())

    def displayMessage(self, message):
        # Clean the hexdump view
        self.textview.get_buffer().delete(self.textview.get_buffer().get_start_iter(), self.textview.get_buffer().get_end_iter())
        # Fecth the content of the message to display
        hexContent = TypeConvertor.hexdump(TypeConvertor.netzobRawToPythonRaw(message.getData()))
        # Update the hexdump
        self.textview.get_buffer().insert_with_tags_by_name(self.textview.get_buffer().get_start_iter(), hexContent, "normalTag")

    #+----------------------------------------------
    #| GETTERS
    #+----------------------------------------------
    def getPanel(self):
        return self.panel