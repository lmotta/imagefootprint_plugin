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
import os, struct, json

from PyQt4 import ( QtCore, QtGui )
from qgis import ( gui as QgsGui, core as QgsCore )

from processtemplate import WorkerTemplate, MessageBarTemplate, ProcessMultiTemplate

from osgeo import ( gdal, osr, ogr )
from gdalconst import GA_ReadOnly
gdal.UseExceptions()
gdal.PushErrorHandler('CPLQuietErrorHandler')

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
  isKilled = False
  factorTolerance = 4 # multiply (resX + resY) / 2

  def __init__(self, hasValidPixels, wktSRS=None):
    self.hasValidPixels = hasValidPixels
    self.metadata = {}
    self.srsTransform = self.crsDescripTransform = self.msgError = None
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
        unit_sr = None
        if sr.IsGeographic():
          is_geographic = True
          epsg = sr.GetAuthorityCode('GEOGCS')
          unit_sr = sr.GetAngularUnitsName()
        elif sr.IsProjected():
          epsg = sr.GetAuthorityCode('PROJCS')
          unit_sr = sr.GetLinearUnitsName()
        else:
          epsg = None

        return {
          'crs': { 'is_geographic': is_geographic, 'epsg': epsg, 'unit_sr': unit_sr },
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
      ds = None
      try:
        ds = drv_mem.Create( '', self.metadata['raster_size']['x'], self.metadata['raster_size']['y'], 1, datatype )
      except RuntimeError:
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
        if self.isKilled:
          break

    def getGeomsSieve():
      srs = osr.SpatialReference()
      srs.ImportFromWkt( self.metadata['wkt_sr'] )
      drv_poly = ogr.GetDriverByName('MEMORY')
      ds_poly = drv_poly.CreateDataSource('memData')
      layer_poly = ds_poly.CreateLayer( 'memLayer', srs, ogr.wkbPolygon )
      field = ogr.FieldDefn("dn", ogr.OFTInteger)
      layer_poly.CreateField( field )
      idField = 0
      try:
        gdal.Polygonize( band_sieve, None, layer_poly, idField, [], callback=None )
      except RuntimeError:
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
      typeFootprint = "Valid pixeis" if self.hasValidPixels else "Bounding box"
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
      num_parts = geom.GetGeometryCount()
      num_holes = 0
      for i in xrange( num_parts ):
        poly = geom.GetGeometryRef( i )
        num_rings =  poly.GetGeometryCount()
        if num_rings > 1:
          num_holes += num_rings - 1
      
      value = { 'num_parts': num_parts, 'num_holes': num_holes }
      self.metadata.update( { 'geometry':  value } )
      tol = ( self.metadata['raster_size']['resX'] + self.metadata['raster_size']['resY'] ) / 2.0
      tol *= self.factorTolerance
      wkt_geom = geom.SimplifyPreserveTopology( tol ).ExportToWkt()
      self.metadata.update( { 'wkt_geom': wkt_geom } )

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
    
    if self.isKilled:
      return False

    band_img = ds_img.GetRasterBand( self.metadata['bands']['number'] )
    self.metadata.update( { 'type_band1': band_img.DataType } )

    if not self.metadata['type_band1'] in self.gdal_sctruct_types.keys():
      ds_img = None
      self.msgError = "Type of image not supported"
      return False

    drv_mem = gdal.GetDriverByName('MEM')
    datatype_out = gdal.GDT_Byte
    
    if self.isKilled:
      return False

    # Mask
    ds_mask = getDatasetMem( datatype_out )
    if ds_mask is None:
      self.msgError = "Error for create 'mask' image in memory"
      return False
    band_mask = ds_mask.GetRasterBand(1)

    populateMask( datatype_out )
    ds_img = band_img = None

    if self.isKilled:
      return False
    # Sieve
    pSieve = { 'threshold': 100, 'connectedness': 8 }
    ds_sieve = getDatasetMem( datatype_out )
    if ds_sieve is None:
      self.msgError = "Error for create memory 'sieve' image in memory"
      ds_mask = None
      return False

    if self.isKilled:
      ds_sieve = None
      return False

    band_sieve = ds_sieve.GetRasterBand(1)
    try:
      gdal.SieveFilter( band_mask, None, band_sieve, pSieve['threshold'], pSieve['connectedness'], [], callback=None )
    except RuntimeError:
      self.msgError = gdal.GetLastErrorMsg()
      ds_mask = band_mask = None
      return False

    ds_mask = band_mask = None
    
    if self.isKilled:
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

    if self.isKilled:
      for id in xrange( numGeoms ):
        geomsSieve[ id ].Destroy()
      del geomsSieve[:]
      return False

    geomUnion = ogr.Geometry( ogr.wkbMultiPolygon )
    for id in xrange( numGeoms ):
      geomUnion.AddGeometry( geomsSieve[ id ] )
      geomsSieve[ id ].Destroy()
    del geomsSieve[:]
    
    if self.isKilled:
      geomUnion.Destroy()
      return False
    
    geom = geomUnion.UnionCascaded()
    geomUnion.Destroy()
    addArea( geom )
    addGeom( geom )
    geom.Destroy()
    del self.metadata['transform']
    del self.metadata['type_band1']
    del self.metadata['sr']
    
    return True

class WorkerPopulateCatalog(WorkerTemplate):
  def __init__(self):
    super(WorkerPopulateCatalog, self).__init__()
    self.foot = self.featTemplate = None
    self.lstSources = self.ct = None

  def setData(self, data):
    self.idWorker = data['idWorker']
    self.lstSources = data[ 'sources' ]
    self.featTemplate = QgsCore.QgsFeature( data['provLayer'].fields() )
    self.ct = QgsCore.QgsCoordinateTransform()
    self.ct.setDestCRS( data['provLayer'].crs() )
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

    totalError = totalAdded = 0
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
        totalAdded += 1
        del geomLayer
      else:
        msgError = { '_error': True, 'message_error': self.foot.msgError }
        setFeatureAttributes( feat, self.lstSources[ i ], msgError )
        totalError += 1

      if self.isKilled:
        del feat
        break
      self.processed.emit( { 'feats': [ feat ] } )

    data = { 'idWorker': self.idWorker, 'totalAdded': totalAdded, 'totalError': totalError }
    self.finished.emit( data )

  @staticmethod
  def totalKeys():
    return ( 'totalAdded', 'totalError' )

class MessageBarProgress(MessageBarTemplate):
  def __init__(self, pluginName, msg):
    super(MessageBarProgress, self).__init__( pluginName, msg, [ WorkerPopulateCatalog, Footprint ] )
    self.pb = QtGui.QProgressBar( self.msgBarItem )
    self.pb.setAlignment( QtCore.Qt.AlignLeft )
    self.lCount = QtGui.QLabel( self.msgBarItem )
    lyt = self.msgBarItem.layout()
    lyt.addWidget( self.lCount )
    lyt.addWidget( self.pb )

  def init(self, maximum):
    self.pb.setValue( 0 )
    self.pb.setMaximum( maximum )
    self.lCount.setText( "1/%d" % maximum )

  def step(self, step):
    value = self.pb.value() + step 
    self.pb.setValue( value )
    lCount = "%d/%d" % ( value, self.pb.maximum() )
    self.lCount.setText( lCount )

class PopulateCatalog(ProcessMultiTemplate):
  def __init__(self, pluginName,  nameModulus):
    super(PopulateCatalog, self).__init__( pluginName,  nameModulus, WorkerPopulateCatalog )
    self.provLayer = None

  @QtCore.pyqtSlot(dict)
  def processedWorkers(self, data):
    super(PopulateCatalog, self).processedWorkers( data )
    if not WorkerPopulateCatalog.isKilled:
      self.provLayer.addFeatures( data['feats'] )

  def run(self, provLayer, dataDlgFootprint, images):
    self.msgBar.clearWidgets()
    msg = "Using until %d processors" % self.totalProcess
    self.mb = MessageBarProgress( self.pluginName, msg )
    self.msgBar.pushWidget( self.mb.msgBarItem, QgsGui.QgsMessageBar.INFO )
    
    data = {
      'provLayer': provLayer,
      'hasValidPixels': dataDlgFootprint['hasValidPixels'] ,
      'wktCrsImages': dataDlgFootprint['wktCrsImages']
    }
    
    self.mb.init( len( images ) )
    WorkerPopulateCatalog.isKilled, Footprint.isKilled = False, False
    self.provLayer = provLayer
    super( PopulateCatalog, self ).run( data, images )
