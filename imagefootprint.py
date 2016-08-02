# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Image Footprint
Description          : Plugin for create a catalog layer from directories of images
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
import os, datetime, filecmp, shutil, json

from PyQt4 import ( QtGui, QtCore )
from qgis import ( core as QgsCore, gui as QgsGui, utils as QgsUtils )

from populatecatalog import PopulateCatalog, WorkerPopulateCatalog, Footprint
from validimages import ValidImages, WorkerValidImages
  
class DialogFootprint(QtGui.QDialog):
  dirImages = None
  wktCrsImages = None
  hasValidPixels = False
  hasSubDir = False
  hasInverse = False
  textFilters =  ""
  def __init__(self, pluginName):
    def initGui():
      def getLayout(parent, widgets):
        lyt = QtGui.QGridLayout( parent )
        for item in widgets:
          if item.has_key('spam'):
            sRow, sCol = item['spam']['row'], item['spam']['col']
            lyt.addWidget( item['widget'], item['row'], item['col'], sRow, sCol, QtCore.Qt.AlignLeft )
          else:
            lyt.addWidget( item['widget'], item['row'], item['col'], QtCore.Qt.AlignLeft )
        return lyt

      def getGroupBox(name, parent, widgets):
        lyt = getLayout( parent, widgets )
        gbx = QtGui.QGroupBox(name, parent )
        gbx.setLayout( lyt )
        return gbx

      self.setWindowTitle( self.pluginName )
      
      self.pbSelectDir = QtGui.QPushButton(self)
      self.pbSelectDir.setToolTip( self.titleSelectDirectory )
      self.pbSelectDir.setIcon( QtGui.QIcon(":/images/themes/default/mActionFileOpen.svg") )
      self.cbSubDir = QtGui.QCheckBox("Search in Subdirectories", self )
      self.cbSubDir.setChecked( self.hasSubDir )
      self.leFilters = QtGui.QLineEdit( self.textFilters, self )
      tip = "Search images with/without filters(',' for separate filters)"
      tip += "\nExample: LC8,LT5 (only files with LC8 or LT5)\n* Case insensitive"
      self.leFilters.setToolTip( tip )
      self.cbInverse = QtGui.QCheckBox("Inverse filters", self )
      self.cbInverse.setChecked( self.hasInverse )
      l_wts = [
        { 'widget': self.pbSelectDir, 'row': 0, 'col': 0 },
        { 'widget': self.cbSubDir,    'row': 0, 'col': 1 },
        { 'widget': self.leFilters,   'row': 1, 'col': 0 },
        { 'widget': self.cbInverse,   'row': 1, 'col': 1 }
      ]
      gbxImage = getGroupBox("Image", self, l_wts)

      rbBBox = QtGui.QRadioButton("Bounding box", self)
      rbBBox.setToolTip( "Soft processing")
      rbBBox.setChecked( not self.hasValidPixels )
      self.rbValidPixel = QtGui.QRadioButton("Valid pixels", self)
      self.rbValidPixel.setToolTip( "Heavy processing")
      self.rbValidPixel.setChecked( self.hasValidPixels )
      self.pbSelectCRS = QtGui.QPushButton(self)
      self.pbSelectCRS.setToolTip("Select projected reference systems for image with geographic systems(used for area calculation)")
      self.pbSelectCRS.setIcon( QtGui.QIcon(":/images/themes/default/propertyicons/CRS.svg") )
      l_wts = [
        { 'widget': rbBBox,          'row': 0, 'col': 0 },
        { 'widget': self.rbValidPixel, 'row': 0, 'col': 1 },
        { 'widget': self.pbSelectCRS,  'row': 0, 'col': 2 }
      ]
      gbxProcessing = getGroupBox("Processing", self, l_wts)

      self.pbRun = QtGui.QPushButton("Run", self )
      l_wts = [
        { 'widget': gbxImage,      'row': 0, 'col': 0 },
        { 'widget': gbxProcessing, 'row': 1, 'col': 0 },
        { 'widget': self.pbRun,    'row': 2, 'col': 0 }
      ]
      lyt = getLayout( self, l_wts )
      self.setLayout( lyt )

    def connect():
      self.pbSelectDir.clicked.connect( self.selectDir )
      self.pbSelectCRS.clicked.connect( self.selectCRS )
      self.dlgCRS.crsChanged.connect( self.setCRS )
      self.pbRun.clicked.connect( self.run )

    wparent = QgsUtils.iface.mainWindow()
    super( DialogFootprint, self ).__init__( wparent )
    self.pluginName = pluginName
    self.titleSelectDirectory = "Select diretory of images"
    initGui()
    self.dlgCRS = QgsGui.QgsProjectionSelectionWidget( wparent )
    self.dlgCRS.setOptionVisible( QgsGui.QgsProjectionSelectionWidget.ProjectCrs, True )
    connect()
    self.msgBar = QgsUtils.iface.messageBar()

  @QtCore.pyqtSlot( bool )
  def selectDir(self, checked):
    sdir = QtGui.QFileDialog.getExistingDirectory(self, self.titleSelectDirectory, self.dirImages )
    if len(sdir) > 0:
      self.dirImages = sdir
      self.pbSelectDir.setToolTip( sdir )

  @QtCore.pyqtSlot( bool )
  def selectCRS(self, checked):
    self.dlgCRS.selectCrs() # Open Dialog

  @QtCore.pyqtSlot( QgsCore.QgsCoordinateReferenceSystem )
  def setCRS(self, crs):
    csr = self.dlgCRS.crs()
    description = crs.description()
    if crs.geographicFlag():
      msg = "CRS selected '%s' need be Projected." % description
      self.msgBar.pushMessage( self.pluginName, msg, QgsGui.QgsMessageBar.WARNING, 4 )
    else:
      description = "CRS '%s' for image with geographic systems(used for area calculation)" % description 
      self.pbSelectCRS.setToolTip( description )
      self.wktCrsImages = crs.toWkt()

  @QtCore.pyqtSlot( bool )
  def run(self, checked):
    if not self.dirImages is None:
      self.hasValidPixels = self.rbValidPixel.isChecked()
      self.hasSubDir = self.cbSubDir.isChecked()
      self.textFilters = self.leFilters.text().replace(' ', '')
      self.hasInverse = self.cbInverse.isChecked()
      self.accept()
    else:
      self.msgBar.pushMessage( self.pluginName, self.titleSelectDirectory, QgsGui.QgsMessageBar.WARNING, 4 )

class CatalogFootprint(QtCore.QObject):
  expressionFile = "imagefootprint_exp.py"
  expressionDir = "expressions"
  styleFile = "catalog_footprint.qml"

  finished = QtCore.pyqtSignal()
  
  def __init__(self, pluginName):
    super(CatalogFootprint, self).__init__()
    self.pluginName = pluginName
    nameModulus = "ImageFootprint"
    self.registry = QgsCore.QgsMapLayerRegistry.instance()
    self.layerCatalog = self.idLayerCatalog = None
    self.images = []
    self.statusPopulate = { 'isRunning': False, 'cancelByRemoveLayer': False }
    self.pc = PopulateCatalog( pluginName,  nameModulus )
    self.vi = ValidImages( pluginName,  nameModulus )
    self.msgBar = QgsUtils.iface.messageBar()
    
    self.registry.layerWillBeRemoved.connect( self.layerWillBeRemoved )
    
  def __del__(self):
    self.registry.layerWillBeRemoved.disconnect( self.layerWillBeRemoved )

  @QtCore.pyqtSlot(str)
  def layerWillBeRemoved(self, theLayerId):
    if not self.statusPopulate['isRunning']:
      return
    if self.idLayerCatalog == theLayerId:
      WorkerPopulateCatalog.isKilled = True
      Footprint.isKilled = True
      self.statusPopulate['cancelByRemoveLayer'] = True

  def run(self, dataDlgFootprint):
    def populateCatalog():
      def createLayerPolygon():
        atts = [
          "name:string(100)", "filename:string(500)",
          "meta_html:string(1000)", "meta_json:string(500)",
          "meta_jsize:integer"
        ]
        l_fields = map( lambda item: "field=%s" % item, atts  )
        l_fields.insert( 0, "crs=epsg:4326" )
        l_fields.append( "index=yes" )
        s_fields = '&'.join( l_fields )
        nameLayer = "catalog_footprint_%s" % str( datetime.datetime.now() )
        self.layerCatalog =  QgsCore.QgsVectorLayer( "MultiPolygon?%s" % s_fields, nameLayer, "memory")
        self.idLayerCatalog = self.layerCatalog.id()
        QgsCore.QgsMapLayerRegistry.instance().addMapLayer( self.layerCatalog )
        self.layerCatalog.loadNamedStyle( os.path.join( os.path.dirname( __file__ ), self.styleFile ) )
        QgsUtils.iface.legendInterface().refreshLayerSymbology( self.layerCatalog )
   
      @QtCore.pyqtSlot(dict)
      def finishedPopulateCatalog(data):
        def refreshLayer():
          self.layerCatalog.updateExtents()
          if QgsUtils.iface.mapCanvas().isCachingEnabled():
            self.layerCatalog.setCacheImage( None )
          else:
            QgsUtils.iface.mapCanvas().refresh()
        
        self.pc.finished.disconnect( finishedPopulateCatalog )
        self.msgBar.popWidget()
        isOk, msg = True, None
        if WorkerPopulateCatalog.isKilled:
          isOk = False
          if self.statusPopulate['cancelByRemoveLayer']:
            msg = "Canceled by remove catalog layer"
          else:
            msg = "Canceled by user"
            self.registry.removeMapLayer( self.idLayerCatalog )
        else:
          if data['totalError'] > 0:
            d = ( data['totalAdded'], self.layerCatalog.name(), data['totalError'] )
            msg = "Add %d features in '%s'. Total of errors %d" % d
          else:
            d = ( data['totalAdded'], self.layerCatalog.name() )
            msg = "Add %d features in '%s'" % d
          refreshLayer()

        typMessage = QgsGui.QgsMessageBar.INFO if isOk else QgsGui.QgsMessageBar.WARNING
        self.msgBar.pushMessage( self.pluginName, msg, typMessage, 4 )
        self.idLayerCatalog, self.layerCatalog = None, None
        self.statusPopulate['isRunning'] = False
        self.statusPopulate['cancelByRemoveLayer'] = False
        self.finished.emit()
      
      createLayerPolygon()
      self.statusPopulate['isRunning'] = True
      self.pc.finished.connect( finishedPopulateCatalog )
      self.pc.run( self.layerCatalog.dataProvider(), dataDlgFootprint, self.images )

    @QtCore.pyqtSlot(dict)
    def finishedValidImages():
      self.vi.finished.disconnect( finishedValidImages )
      self.msgBar.popWidget()
      isOk, msg = True, None 
      if WorkerValidImages.isKilled:
        isOk, msg = False, "Canceled by user" 
      elif len( self.images ) == 0:
        msg = '' if dataDlgFootprint['hasSubDir'] else "NOT"
        msgSubdir = "%s searching in subdirectories" % msg
        data = ( dataDlgFootprint['dirImages'], msgSubdir )
        isOk, msg = False, "Not found images in '%s' %s!" % data
      
      if not isOk:
        self.msgBar.pushMessage( self.pluginName, msg, QgsGui.QgsMessageBar.WARNING, 4 )
        self.finished.emit()
      else:
        populateCatalog()
    
    del self.images[:]
    self.vi.finished.connect( finishedValidImages )
    self.vi.run( dataDlgFootprint, self.images )
    
  @staticmethod
  def copyExpression():
    f = os.path.dirname
    fromFile = os.path.join( f( __file__ ), CatalogFootprint.expressionFile )
    dirExp = os.path.join( f( f( f( __file__ ) ) ), CatalogFootprint.expressionDir )
    toFile = os.path.join( dirExp , CatalogFootprint.expressionFile )
    if os.path.exists( toFile ) and filecmp.cmp( fromFile, toFile ):
      return
    shutil.copy2( fromFile, toFile )
    toFile = toFile.replace(".py", ".pyc")
    if os.path.exists( toFile ):
      os.remove( toFile )

  @staticmethod
  def getValueMetadata(jsonMetadataFeature, keys):
    dicMetadata = json.loads( jsonMetadataFeature )
    
    msgError = value = None
    e_keys = map( lambda item: "'%s'" % item, keys )
    try:
      value = reduce( lambda d, k: d[ k ], [ dicMetadata ] + keys )
    except KeyError as e:
      msgError = "Have invalid key: %s" % ' -> '.join( e_keys)
    except TypeError as e:
      msgError = "The last key is invalid: %s" % ' -> '.join( e_keys)
  
    if msgError is None and isinstance( value, dict):
      msgError = "Missing key: %s" % ' -> '.join( e_keys)
  
    return ( True, value ) if msgError is None else ( False, msgError ) 
  
  @staticmethod
  def actionCatalog(nameAction, sourceRaster):
    def _getRasterLayer():
      layerRasters = filter( lambda l: l.type() == QgsCore.QgsMapLayer.RasterLayer, legend.layers() )
      sources = map( lambda l: l.source(), layerRasters )
      needAdd = False
      if sourceRaster in sources:
        layer = layerRasters[ sources.index( sourceRaster ) ]
      else:
        name = os.path.splitext( os.path.basename( sourceRaster ) )[0]
        layer = QgsCore.QgsRasterLayer( sourceRaster, name )
        needAdd = True

      return { 'layer': layer, 'needAdd': needAdd }

    def _getExtent(canvas):
      crsCanvas = canvas.mapSettings().destinationCrs()
      layer = _getRasterLayer()['layer']
      crsLayer = layer.crs()
      ctCanvas = QgsCore.QgsCoordinateTransform( crsLayer, crsCanvas )
      return ctCanvas.transform( layer.extent() )
    
    def _highlight(canvas, extent):
      def removeRB():
        rb.reset( True )
        canvas.scene().removeItem( rb )
      
      rb = QgsGui.QgsRubberBand( canvas, QgsCore.QGis.Polygon )
      rb.setBorderColor( QtGui.QColor( 255,  0, 0 ) )
      rb.setWidth( 2 )
      rb.setToGeometry( QgsCore.QgsGeometry.fromRect( extent ), None )
      QtCore.QTimer.singleShot( 2000, removeRB )

    # Actions functions
    def show_hideImage():
      vreturn = _getRasterLayer()
      isLayerVisible = True
      if vreturn['needAdd']:
        QgsCore.QgsMapLayerRegistry.instance().addMapLayer( vreturn['layer'] )
      else:
        isLayerVisible = not legend.isLayerVisible( vreturn['layer'] )
      legend.setLayerVisible( vreturn['layer'], isLayerVisible )
    
    def setCurrent():
      vreturn = _getRasterLayer()
      if vreturn['needAdd']:
        QgsCore.QgsMapLayerRegistry.instance().addMapLayer( vreturn['layer'] )
      legend.setCurrentLayer( vreturn['layer'] )
    
    def highlight():
      canvas = QgsUtils.iface.mapCanvas()
      extent = _getExtent( canvas )
      _highlight( canvas, extent )
    
    def zoom():
      canvas = QgsUtils.iface.mapCanvas()
      extent = _getExtent( canvas )
      canvas.setExtent( extent )
      canvas.zoomByFactor( 1.05 )
      canvas.refresh()
      _highlight( canvas, extent )
    
    actionsFunc = {
      'show_hideImage': show_hideImage,
      'highlight': highlight,
      'zoom': zoom,
      'setCurrent': setCurrent
    }
    if not nameAction in actionsFunc.keys():
      return { 'isOk': False, 'msg': "Missing action '%s'" % nameAction }
    if not os.path.exists( sourceRaster ):
      return { 'isOk': False, 'msg': "Raster layer '%s' not found" % sourceRaster }
    
    legend = QgsUtils.iface.legendInterface()
    actionsFunc[ nameAction ]()
    return { 'isOk': True }
