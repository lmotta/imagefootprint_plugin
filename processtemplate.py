# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Template for process
Description          : Template for using worker and messagebar
Date                 : July, 2016
copyright            : (C) 2016 by Luiz Motta
email                : motta.luiz@gmail.com

 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt4 import ( QtCore, QtGui )
from qgis import utils as QgsUtils

class WorkerTemplate(QtCore.QObject):
  finished = QtCore.pyqtSignal(dict)
  isKilled = False

  def __init__(self):
    super(WorkerTemplate, self).__init__()

#  def setData(self, data):
#    pass

#  @QtCore.pyqtSlot()
#  def run(self):
#    self.finished.emit()

class MessageBarTemplate(QtCore.QObject):
  def __init__(self, pluginName, msg ):
    def initGui():
      def setCancel():
        self.tbCancel.setIcon( QtGui.QIcon(":/images/themes/default/mActionFileExit.png") )
        self.tbCancel.setText( "Cancel")
        self.tbCancel.setToolButtonStyle( QtCore.Qt.ToolButtonTextBesideIcon )

      self.msgBarItem = QgsUtils.iface.messageBar().createMessage( pluginName, msg )
      self.tbCancel = QtGui.QToolButton( self.msgBarItem )
      setCancel()
      lyt = self.msgBarItem.layout()
      lyt.addWidget( self.tbCancel )

    super(MessageBarTemplate, self).__init__()
    self.msgBarItem = self.tbCancel = None
    initGui()
    self.tbCancel.clicked.connect( self.clickedCancel )
    
  @QtCore.pyqtSlot(bool)
  def clickedCancel(self, checked):
    self.tbCancel.setEnabled( False )
    #Worker??.isKilled = True

class ProcessTemplate(QtCore.QObject):
  finished = QtCore.pyqtSignal(dict)
  
  def __init__(self, pluginName, nameModulus):
    super(ProcessTemplate, self).__init__()
    self.pluginName, self.nameModulus = pluginName, nameModulus
    self.worker = self.thread = self.mb = self.ss = None
    self.msgBar = QgsUtils.iface.messageBar()
    self.initThread()
    self._connectWorker()
    
  def __del__(self):
    self.finishThread()

  def initThread(self):
    #self.worker = Worker??()
    self.thread = QtCore.QThread( self )
    self.thread.setObjectName( self.nameModulus )
    self.worker.moveToThread( self.thread )
    self.ss = [
      { 'signal': self.thread.started,   'slot': self.worker.run },
      { 'signal': self.worker.finished,  'slot': self.finishedWorker }
    ]
 
  def finishThread(self):
    self._connectWorker( False )
    self.worker.deleteLater()
    self.thread.wait()
    self.thread.deleteLater()
    self.thread = self.worker = None

  def _connectWorker(self, isConnect = True):
    if isConnect:
      for item in self.ss:
        item['signal'].connect( item['slot'] )  
    else:
      for item in self.ss:
        item['signal'].disconnect( item['slot'] )

  @QtCore.pyqtSlot(dict)
  def finishedWorker(self, data):
    self.thread.quit()
    self.finished.emit( data )
"""
  def run(self, dataDlgFootprint, images):
    self.msgBar.clearWidgets()
    self.mb = MessageBar??( self.pluginName, msg )
    self.msgBar.pushWidget( self.mb.msgBarItem, QgsGui.QgsMessageBar.INFO )
    data ??
    self.mb.init() ??
    self.worker.setData( data )
    Worker??.isKilled = False
    self.thread.start()
    #self.worker.run() # DEBUG
"""
