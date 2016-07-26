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
import os, filecmp, shutil, struct, datetime, json

from PyQt4 import ( QtGui, QtCore )
from qgis import ( core as QgsCore, gui as QgsGui, utils as QgsUtils )

from osgeo import ( gdal, ogr, osr )
from gdalconst import ( GA_ReadOnly, GA_Update )

from messagebarprogress import MessageBarProgress
  
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

      rbBBox = QtGui.QRadioButton("Bound box", self)
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
      self.accept()
      self.hasValidPixels = self.rbValidPixel.isChecked()
      self.hasSubDir = self.cbSubDir.isChecked()
      self.textFilters = self.leFilters.text().replace(' ', '')
      self.hasInverse = self.cbInverse.isChecked()
    else:
      self.msgBar.pushMessage( self.pluginName, self.titleSelectDirectory, QgsGui.QgsMessageBar.WARNING, 4 )

class Footprint():
  gdal_sctruct_types = {
    gdal.GDT_Byte: 'B',
    gdal.GDT_UInt16: 'H',
    gdal.GDT_Int16: 'h',
    gdal.GDT_UInt32: 'I',
    gdal.GDT_Int32: 'i',
    gdal.GDT_Float32: 'f',
    gdal.GDT_Float64: 'd'
  }

  def __init__(self, hasValidPixels, wktSRS=None):
    self.hasValidPixels = hasValidPixels
    self.metadata = {}
    self.srsTransform = self.crsDescripTransform = self.msgError = None
    self.isKilled = False
    if not wktSRS is None:
      self.srsTransform = osr.SpatialReference()
      self.srsTransform.ImportFromWkt( wktSRS )
      crs = QgsCore.QgsCoordinateReferenceSystem()
      crs.createFromWkt( wktSRS )
      self.crsDescripTransform = crs.description()

  def calculate(self, filename):
    def setMetadata(ds):
      def getMetadataSR():
        sr = osr.SpatialReference()
        sr.ImportFromWkt( ds.GetProjectionRef() )
        is_geographic = False
        if sr.IsGeographic():
          is_geographic = True
          epsg = sr.GetAuthorityCode('GEOGCS')
        elif sr.IsProjected():
          epsg = sr.GetAuthorityCode('PROJCS')
        else:
          epsg = None

        return {
          'crs': { 'is_geographic': is_geographic, 'epsg': epsg, 'unit_sr': sr.GetLinearUnitsName() },
          'sr': sr,
          'wkt_sr': sr.ExportToWkt()
        }

      def getStrTypeBands():
        strTypes = []
        for id in xrange( ds.RasterCount ):
          band = ds.GetRasterBand( id+1 )
          strType = "B%d(%s)" % ( id+1, gdal.GetDataTypeName( band.DataType ) )
          strTypes.append( strType )
        return ",".join( strTypes )

      coefs = ds.GetGeoTransform()
      raster_size = {
        'x': ds.RasterXSize, 'y': ds.RasterYSize,
        'resX': coefs[1], 'resY': -1 * coefs[5] 
      }
      self.metadata = {
        'raster_size': raster_size,
        'drive': ds.GetDriver().GetDescription(),
        'bands': { 'number': ds.RasterCount, 'types': getStrTypeBands() },
        'transform': coefs,
      }
      self.metadata.update( getMetadataSR() )
    
    def getDatasetMem(datatype):
      ds = drv_mem.Create( '', self.metadata['raster_size']['x'], self.metadata['raster_size']['y'], 1, datatype )
      if ds is None:
        return None
      ds.SetProjection( self.metadata['wkt_sr'] )
      ds.SetGeoTransform( self.metadata['transform'] )
      return ds

    def populateMask(datatype_mask):
      xoff, xsize, ysize = 0, self.metadata['raster_size']['x'], 1
      format_struct_img = self.gdal_sctruct_types[ self.metadata['type_band1'] ] * xsize * ysize
      format_struct__mask = self.gdal_sctruct_types[ datatype_mask ] * xsize * ysize
      value_new = []
      for row in xrange( self.metadata['raster_size']['y'] ):
        line = band_img.ReadRaster( xoff, row, xsize, ysize, xsize, ysize, self.metadata['type_band1'] )
        value =  list( struct.unpack( format_struct_img, line) )
        del line
        for index, item in enumerate(value):
          value[ index ] = int( value[ index ] != 0 )
        line = struct.pack( format_struct__mask, *value )
        del value
        band_mask.WriteRaster( xoff, row, xsize, ysize, line )
        del line

    def getGeomsSieve():
      srs = osr.SpatialReference()
      srs.ImportFromWkt( self.metadata['wkt_sr'] )
      drv_poly = ogr.GetDriverByName('MEMORY')
      ds_poly = drv_poly.CreateDataSource('memData')
      layer_poly = ds_poly.CreateLayer( 'memLayer', srs, ogr.wkbPolygon )
      field = ogr.FieldDefn("dn", ogr.OFTInteger)
      layer_poly.CreateField( field )
      idField = 0
      gdal.Polygonize( band_sieve, None, layer_poly, idField, [], callback=None )
      if gdal.GetLastErrorType() != 0:
        return { 'isOk': False, 'msg': gdal.GetLastErrorMsg() }
      geoms = []
      layer_poly.SetAttributeFilter("dn = 1")
      for feat in layer_poly:
        geoms.append( feat.GetGeometryRef().Clone() )
      ds_poly = layer_poly = None

      return { 'isOk': True, 'geoms': geoms }

    def addArea(geom):
      area = None
      area_img = None
      typeFootprint = "Valid pixeis" if self.hasValidPixels else "Bound box"
      if not self.metadata['crs']['is_geographic']:
        area = geom.GetArea()
        area_img = { 'is_calculate': True, 'ha': area / 10000 }
      else:
        if not self.srsTransform is None:
          geom_c = geom.Clone()
          geom_c.AssignSpatialReference( self.metadata['sr'] )
          geom_c.TransformTo( self.srsTransform )
          area = geom_c.GetArea()
          geom_c.Destroy()
          area_img = { 'is_calculate': True, 'ha': area / 10000, 'crs_description': self.crsDescripTransform }
        else:
          area_img = { 'is_calculate': False }
      area_img['type'] = typeFootprint
      self.metadata.update( { 'area': area_img } ) 

    def addGeom(geom):
      self.metadata.update( { 'wkt_geom': geom.ExportToWkt() } )
      num_parts = geom.GetGeometryCount()
      num_holes = 0
      for i in xrange( num_parts ):
        num_rings =  geom.GetGeometryRef( i ).GetGeometryCount()
        if num_rings > 1:
          num_holes += num_rings - 1           
      value = { 'num_parts': num_parts, 'num_holes': num_holes }
      self.metadata.update( { 'geometry':  value } )

    def getBoundBox():
      def getXY( col, line):
        x = coefs[0] + col * coefs[1] + line * coefs[2]
        y = coefs[3] + col * coefs[4] + line * coefs[5]
        return { 'x': x, 'y': y }
      coefs = self.metadata['transform']
      p1 = getXY(0,0)
      p2 = getXY( self.metadata['raster_size']['x'], self.metadata['raster_size']['y'] )
      
      geom = ogr.Geometry( ogr.wkbMultiPolygon )
      
      ring = ogr.Geometry( ogr.wkbLinearRing )
      ring.AddPoint( p1['x'], p1['y'] )
      ring.AddPoint( p2['x'], p1['y'] )
      ring.AddPoint( p2['x'], p2['y'] )
      ring.AddPoint( p1['x'], p2['y'] )
      ring.AddPoint( p1['x'], p1['y'] )
      poly = ogr.Geometry( ogr.wkbPolygon )
      poly.AddGeometry( ring )

      geom.AddGeometry( poly )

      return geom

    ds_img = gdal.Open( filename, GA_ReadOnly )
    self.metadata.clear()
    setMetadata( ds_img )
    
    if not self.hasValidPixels:
      geom = getBoundBox()
      ds_img = None
      addArea(geom)
      addGeom(geom)
      geom.Destroy()
      del self.metadata['transform']
      del self.metadata['sr']

      return True
    
    
    if self.killed:
      return False

    band_img = ds_img.GetRasterBand( 1 )
    self.metadata.update( { 'type_band1': band_img.DataType } )

    if not self.metadata['type_band1'] in self.gdal_sctruct_types.keys():
      ds_img = None
      self.msgError = "Type of image not supported"
      return False

    drv_mem = gdal.GetDriverByName('MEM')
    datatype_out = gdal.GDT_Byte
    
    if self.killed:
      return False

    # Mask
    ds_mask = getDatasetMem( datatype_out )
    if ds_mask is None:
      self.msgError = "Error for create 'mask' image in memory"
      return False
    band_mask = ds_mask.GetRasterBand(1)

    if self.killed:
      ds_img = band_img = None
      return False

    populateMask( datatype_out )
    ds_img = band_img = None
    # Sieve
    pSieve = { 'threshold': 100, 'connectedness': 8 }
    ds_sieve = getDatasetMem( datatype_out )
    if ds_sieve is None:
      self.msgError = "Error for create memory 'sieve' image in memory"
      ds_mask = None
      return False

    if self.killed:
      ds_sieve = None
      return False

    band_sieve = ds_sieve.GetRasterBand(1)
    gdal.SieveFilter( band_mask, None, band_sieve, pSieve['threshold'], pSieve['connectedness'], [], callback=None )
    ds_mask = band_mask = None
    if gdal.GetLastErrorType() != 0:
      self.msgError = gdal.GetLastErrorMsg()
      return False
    
    if self.killed:
      ds_sieve = band_sieve = None
      return False

    # Geoms
    vreturn = getGeomsSieve()
    ds_sieve = band_sieve = None
    if not vreturn['isOk']:
      self.msgError = vreturn['msg']
      return False
    geomsSieve = vreturn['geoms']
    numGeoms = len( geomsSieve )
    if numGeoms == 0:
      self.msgError = "Not exist geometry from image"
      return False

    if self.killed:
      for id in xrange( numGeoms ):
        geomsSieve[ id ].Destroy()
      del geomsSieve[:]
      return False

    geomUnion = ogr.Geometry( ogr.wkbMultiPolygon )
    for id in xrange( numGeoms ):
      geomUnion.AddGeometry( geomsSieve[ id ] )
      geomsSieve[ id ].Destroy()
    del geomsSieve[:]
    
    if self.killed:
      geomUnion.Destroy()
      return False
    
    geom = geomUnion.UnionCascaded()
    geomUnion.Destroy()
    addArea( geom )
    addGeom( geom.ConvexHull() )
    geom.Destroy()
    del self.metadata['transform']
    del self.metadata['type_band1']
    del self.metadata['sr']
    
    return True

  def kill(self):
    self.isKilled = True

class WorkerPopulateCatalog(QtCore.QObject):
  finished = QtCore.pyqtSignal(int, bool)
  processed = QtCore.pyqtSignal()

  def __init__(self):
    super(WorkerPopulateCatalog, self).__init__()
    self.isKilled = False
    self.layerCatalog = self.foot = self.featTemplate = None
    self.lstSources = self.ct = None

  def setData(self, data):
    self.layerCatalog = data['layer']
    self.lstSources = data[ 'sources' ]
    self.featTemplate = data[ 'feature' ]
    self.ct = QgsCore.QgsCoordinateTransform()
    self.ct.setDestCRS( data['crsLayer'] )
    self.foot = Footprint( data['hasValidPixels'], data['wktCrsImages'] )

  @QtCore.pyqtSlot()
  def run(self):
    def setFeatureAttributes(feat, filename, metadata):
      def getHtmlTreeMetadata(value, html):
        if isinstance( value, dict ):
          html += "<ul>"
          for key, val in sorted( value.iteritems() ):
            if not isinstance( val, dict ):
              html += "<li>%s: %s</li> " % ( key, val )
            else:
              html += "<li>%s</li> " % key
            html = getHtmlTreeMetadata( val, html )
          html += "</ul>"
          return html
        return html

      feat.setAttribute('filename',  filename )
      feat.setAttribute('name', os.path.basename( filename ) )
      html = getHtmlTreeMetadata(metadata, '')
      feat.setAttribute('meta_html',html )
      vjson = json.dumps( metadata )
      feat.setAttribute('meta_json', vjson )
      feat.setAttribute('meta_jsize', len( vjson) )

    totalError = 0
    for i in xrange( len( self.lstSources ) ):
      feat = QgsCore.QgsFeature( self.featTemplate )
      if self.foot.calculate( self.lstSources[ i ] ):
        geomLayer = QgsCore.QgsGeometry.fromWkt( self.foot.metadata['wkt_geom'] )
        crs = QgsCore.QgsCoordinateReferenceSystem()
        crs.createFromWkt( self.foot.metadata['wkt_sr'] )
        self.ct.setSourceCrs( crs )
        if not geomLayer.transform( self.ct ) == 0:
          msgError = { '_error': True, 'message_error': "Can't transform geometry" }
          setFeatureAttributes( feat, self.lstSources[ i ], msgError )
          totalError += 1
          geomLayer.Destroy()
          del feat
          continue
        del self.foot.metadata['wkt_geom']
        del self.foot.metadata['wkt_sr']
        self.foot.metadata['crs']['description'] = crs.description()
        self.foot.metadata['_error'] = False
        setFeatureAttributes( feat, self.lstSources[ i ], self.foot.metadata )
        feat.setGeometry( geomLayer )
        del geomLayer
      else:
        msgError = { '_error': True, 'message_error': self.foot.msgError }
        setFeatureAttributes( feat, self.lstSources[ i ], msgError )
        totalError += 1
      self.layerCatalog.addFeature( feat )
      del feat
      self.processed.emit()

      if self.isKilled:
        break

    self.finished.emit( self.isKilled, totalError )

  def kill(self):
    self.isKilled = True
    self.foot.kill()

class CatalogFootprint(QtCore.QObject):
  styleFile = "catalog_footprint.qml"
  expressionFile = "imagefootprint_exp.py"
  expressionDir = "expressions"
  iface = QgsUtils.iface
  
  def __init__(self, pluginName):
    super(CatalogFootprint, self).__init__()
    self.pluginName = pluginName
    self.layerPolygon = self.totalImages = None
    self.workers = self.threads = self.mbp = None
    self.totalError = self.totalFinishedWorker = self.totalProcessed = 0
    self.msgBar = self.iface.messageBar()
    self.nameModulus = "ImageFootprint"
    self.initThreads()
    
  def __del__(self):
    self.finishThreads()

  def initThreads(self):
    totalCPU = QtCore.QThread.idealThreadCount()
    title = "Processing with %d CPU" % totalCPU
    self.workers = []
    self.threads = []
    for i in xrange( totalCPU ):
      worker = WorkerPopulateCatalog()
      thread = QtCore.QThread( self )
      thread.setObjectName( "%s - %d" % ( self.nameModulus, i+1 ) )
      worker.moveToThread( thread )
      self.threads.append( thread )
      self.workers.append( worker )
      self._connectWorkers( i )

  def finishThreads(self):
    for i in xrange( len( self.workers ) ):
      self._connectWorkers( i, False )
      self.workers[ i ].deleteLater()
      self.threads[ i ].wait()
      self.threads[ i ].deleteLater()
      self.threads[ i ] = self.workers[ i ] = None

  def _connectWorkers(self, i, isConnect = True):
    ss = [
      { 'signal': self.threads[ i ].started,   'slot': self.workers[ i ].run },
      { 'signal': self.workers[ i ].finished,  'slot': self.finishedWorker },
      { 'signal': self.workers[ i ].processed, 'slot': self.processedWorker }
    ]
    if isConnect:
      for item in ss:
        item['signal'].connect( item['slot'] )  
    else:
      for item in ss:
        item['signal'].disconnect( item['slot'] )

  @QtCore.pyqtSlot(int, bool)
  def finishedWorker(self, totalErros, isKilled):
    self.totalError += totalErros
    self.totalFinishedWorker += 1
    if self.totalFinishedWorker == len( self.workers ):
      self.finishedCatalog(isKilled)

  @QtCore.pyqtSlot()
  def processedWorker(self):
    self.totalProcessed += 1
    self.mbp.step( self.totalProcessed )

  def finishedCatalog(self, isKilled):
    self.totalError = self.totalFinishedWorker = self.totalProcessed = 0
    statusFinished = { 'isOk': True, 'msg': None }
    if isKilled:
      statusFinished['isOk'] = False
      if not self.layerPolygon is None:
        name = self.layerPolygon.name()
        self.layerPolygon.commitChanges()
        QgsCore.QgsMapLayerRegistry.instance().removeMapLayer( self.layerPolygon.id() )
        statusFinished['msg'] = "Canceled by remove layer '%s'" % name
      else:
        statusFinished['msg'] = "Canceled by user"
    else:
      if self.totalError > 0:
        data = ( self.totalImages, self.layerPolygon.name(), self.totalError )
        statusFinished['msg'] = "Add %d features in '%s'. Total of errors %d" % data
      else:
        data = ( self.totalImages, self.layerPolygon.name() )
        statusFinished['msg'] = "Add %d features in '%s'" % data
      self.layerPolygon.commitChanges()
      self.layerPolygon.updateExtents()

    self.msgBar.popWidget()
    typMessage = QgsGui.QgsMessageBar.INFO if statusFinished['isOk'] else QgsGui.QgsMessageBar.WARNING
    self.msgBar.pushMessage( self.pluginName, statusFinished['msg'], typMessage, 4 )

  def run(self, dataDlgFootprint):
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
      self.layerPolygon =  QgsCore.QgsVectorLayer( "MultiPolygon?%s" % s_fields, nameLayer, "memory")
      QgsCore.QgsMapLayerRegistry.instance().addMapLayer( self.layerPolygon )
      self.layerPolygon.loadNamedStyle( os.path.join( os.path.dirname( __file__ ), self.styleFile ) )
      self.iface.legendInterface().refreshLayerSymbology( self.layerPolygon )
      
      return self.layerPolygon
    
    def getValidImages():
      def getValids(root, files):
        def addImage(root, file):
          def validDataSet(filename):
            ds = gdal.Open( filename, GA_ReadOnly )
            not_valid = ds is None or len( ds.GetProjectionRef() ) == 0 or ds.RasterCount == 0
            return None if not_valid else ds

          filename = os.path.join( root, file )
          ds = validDataSet( filename )
          if ds is None:
            return
          ds = None
          images.append( filename )
          
        filters = None
        hasFilters = len( dataDlgFootprint['filters'] ) > 0
        if hasFilters:
          filters = dataDlgFootprint['filters'].upper().split(',')
        images = []
        if hasFilters:
          if dataDlgFootprint['hasInverse']:
            for i in xrange( len( files ) ):
              file = files[ i ]
              if not any( w in file.upper() for w in filters ):
                addImage( root, file )
          else:
            for i in xrange( len( files ) ):
              file = files[ i ]
              if any( w in file.upper() for w in filters ):
                addImage( root, file )
        else:
          for i in xrange( len( files ) ):
            addImage( root, files[ i ] )

        return images
      
      images = []
      if dataDlgFootprint['hasSubDir']:
        for root, dirs, files in os.walk( dataDlgFootprint['dirImages'] ):
          images.extend( getValids( root, files ) )
      else:
        for root, dirs, files in os.walk( dataDlgFootprint['dirImages'] ):
          images.extend( getValids( root, files ) )
          break

      return images

    def generatorSplitImagesWorkers():
      a = images
      n = len( self.workers )
      # Resolution by http://stackoverflow.com/users/220672/tixxit
      # Python: A: splitting a list of arbitrary size into only roughly N-equal parts
      k, m = len(a) / n, len(a) % n
      return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in xrange(n))

    self.msgBar.clearWidgets()
    msg = "Searching images..."
    self.msgBar.pushMessage( self.pluginName, msg, QgsGui.QgsMessageBar.WARNING, 4 )    
    images = getValidImages()
    self.totalImages = len( images )
    if self.totalImages == 0:
      msg = '' if dataDlgFootprint['hasSubDir'] else "not"
      msgSubdir = "%s searching in subdirectories" % msg
      data = ( dataDlgFootprint['dirImages'], msgSubdir )
      msg = "Not found images in '%s' %s!" % data
      self.msgBar.pushMessage( self.pluginName, msg, QgsGui.QgsMessageBar.WARNING, 4 )
      return

    self.layerPolygon = createLayerPolygon()
    self.layerPolygon.startEditing()
    crsLayer = QgsCore.QgsCoordinateReferenceSystem()
    crsLayer.createFromWkt( self.layerPolygon.crs().toWkt() )

    data = {
      'layer': self.layerPolygon,
      'feature': QgsCore.QgsFeature( self.layerPolygon.dataProvider().fields() ),
      'crsLayer': crsLayer,
      'hasValidPixels': dataDlgFootprint['hasValidPixels'] ,
      'wktCrsImages': dataDlgFootprint['wktCrsImages']
    }
    
    # MessageBarProgress destroy in 'finishedCatalog' by self.msgBar.popWidget
    self.msgBar.popWidget()
    title = "Processing with %d CPU" % len( self.workers ) 
    self.mbp = MessageBarProgress( self.pluginName, title, len( images ) )
    
    gen = generatorSplitImagesWorkers()
    for i in xrange( len( self.workers ) ):
      data['sources'] = gen.next()
      self.workers[ i ].setData( data )
      self.mbp.canceled.connect( self.workers[ i ].kill )
      self.threads[ i ].start()
      #self.workers[ i ].run() # DEBUG
    gen.close()
      
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
      canvas = CatalogFootprint.iface.mapCanvas()
      extent = _getExtent( canvas )
      _highlight( canvas, extent )
    
    def zoom():
      canvas = CatalogFootprint.iface.mapCanvas()
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
    
    legend = CatalogFootprint.iface.legendInterface()
    actionsFunc[ nameAction ]()
    return { 'isOk': True }
