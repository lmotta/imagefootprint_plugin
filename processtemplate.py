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
  processed = QtCore.pyqtSignal(dict) # For ProcessMultiTemplate
  isKilled = False

  def __init__(self):
    super(WorkerTemplate, self).__init__()
    self.idWorker = None # For ProcessMultiTemplate

  #def setData(self, data):
  #def run(self): # @QtCore.pyqtSlot()

class MessageBarTemplate(QtCore.QObject):
  def __init__(self, pluginName, msg, killeds ):
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
    self.killeds = killeds
    self.msgBarItem = self.tbCancel = None
    initGui()
    self.tbCancel.clicked.connect( self.clickedCancel )
    
  @QtCore.pyqtSlot(bool)
  def clickedCancel(self, checked):
    self.tbCancel.setEnabled( False )
    for i in xrange( len( self.killeds ) ):
      self.killeds[ i ].isKilled = True
    msg = "Wait! Cancelling processes"
    self.msgBarItem.setText( msg )

class ProcessTemplate(QtCore.QObject):
  finished = QtCore.pyqtSignal(dict)
  
  def __init__(self, pluginName, nameModulus, templateWorker):
    super(ProcessTemplate, self).__init__()
    self.pluginName, self.nameModulus, self.templateWorker = pluginName, nameModulus, templateWorker
    self.worker = self.thread = self.mb = self.ss = None
    self.msgBar = QgsUtils.iface.messageBar()
    self.initThread()
    self._connectWorker()
    
  def __del__(self):
    self.finishThread()

  def initThread(self):
    self.worker = self.templateWorker()
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
    self.thread, self.worker = None, None

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
  
  #def run(self, dataDlgFootprint, images):

class ProcessMultiTemplate(QtCore.QObject):
  finished = QtCore.pyqtSignal(dict)
  
  def __init__(self, pluginName, nameModulus, templateWorker):
    super(ProcessMultiTemplate, self).__init__()
    self.pluginName, self.nameModulus, self.templateWorker = pluginName, nameModulus, templateWorker
    self.totalProcess, self.countTotalProcess = QtCore.QThread.idealThreadCount(), None
    self.workers, self.threads, self.ss = {}, {}, {}
    self.totalKeys = {}
    for key in templateWorker.totalKeys():
      self.totalKeys[ key ] = None
    self.mb = None
    self.msgBar = QgsUtils.iface.messageBar()
    self.initThreads()
    self._connectWorkers()
    
  def __del__(self):
    self.finishThreads()

  def initThreads(self):
    for i in xrange( self.totalProcess ):
      self.workers[ i ] = self.templateWorker()
      self.threads[ i ] = QtCore.QThread( self )
      self.threads[ i ].setObjectName( "%s - %d" % ( self.nameModulus, i+1 ) )
      self.workers[ i ].moveToThread( self.threads[ i ] )
      self.ss[ i ] = [
        { 'signal': self.threads[ i ].started,   'slot': self.workers[ i ].run },
        { 'signal': self.workers[ i ].finished,  'slot': self.finishedWorkers },
        { 'signal': self.workers[ i ].processed, 'slot': self.processedWorkers }
      ]
 
  def finishThreads(self):
    self._connectWorkers( False )
    for i in xrange( self.totalProcess ):
      self.workers[ i ].deleteLater()
      self.threads[ i ].wait()
      self.threads[ i ].deleteLater()
      self.threads[ i ], self.workers[ i ] = None, None

  def _connectWorkers(self, isConnect = True):
    if isConnect:
      for i in xrange( self.totalProcess ):
        for item in self.ss[ i ]:
          item['signal'].connect( item['slot'] )  
    else:
      for i in xrange( self.totalProcess ):
        for item in self.ss[ i ]:
          item['signal'].disconnect( item['slot'] )

  @QtCore.pyqtSlot(dict)
  def finishedWorkers(self, data):
    self.threads[ data['idWorker'] ].quit()
    self.countTotalProcess += 1
    for key in self.totalKeys.keys():
      self.totalKeys[ key ] += data[ key ]
    if self.countTotalProcess == self.totalProcess:
      self.finished.emit( self.totalKeys )

  @QtCore.pyqtSlot(dict)
  def processedWorkers(self, data):
    self.mb.step( 1 )

  def run(self, data, images):
    def generatorSplitImages():
      a = images
      n = self.totalProcess
      # Resolution by http://stackoverflow.com/users/220672/tixxit
      # Python: A: splitting a list of arbitrary size into only roughly N-equal parts
      k, m = len(a) / n, len(a) % n
      return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in xrange(n))

    for key in self.totalKeys.keys():
      self.totalKeys[ key ] = 0
    self.countTotalProcess = 0
    gen = generatorSplitImages()
    for i in xrange( self.totalProcess ):
      data['sources'] = gen.next()
      data['idWorker'] = i
      self.workers[ i ].setData( data )
    gen.close()
    for i in xrange( self.totalProcess ):
      self.threads[ i ].start()
      #self.workers[ i ].run() # DEBUG
