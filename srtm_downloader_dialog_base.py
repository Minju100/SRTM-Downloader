#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SrtmDownloader
                                 A QGIS plugin
 Downloads SRTM Tiles from NASA Server
                              -------------------
        begin                : 2017-12-30
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Dr. Horst Duester / Sourcepole AG
        email                : horst.duester@sourcepole.ch
 ***************************************************************************/

/*************************************************************************
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.core import *
from qgis.PyQt import uic
from qgis.PyQt import QtNetwork
from qgis.PyQt.QtCore import pyqtSlot,  Qt,  QUrl
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import QDialog,  QFileDialog, QApplication, QMessageBox
from about.do_about import About
from download.download import Download
import math,  os,  tempfile,  sys

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'srtm_downloader_dialog_base.ui'))

        
class SrtmDownloaderDialogBase(QDialog, FORM_CLASS):
    """
    Class documentation goes here.
    """
    
    try:            # QGIS3
        VERSION_INT = Qgis.QGIS_VERSION_INT
        VERSION = Qgis.QGIS_VERSION
    except:     # QGIS2
        VERSION_INT = QGis.QGIS_VERSION_INT
        VERSION = QGis.QGIS_VERSION
    
    
    def __init__(self, iface,  parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super(SrtmDownloaderDialogBase, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.username = None
        self.password = None
        self.success = False
        self.dir = tempfile.gettempdir()
        self.btn_download.setEnabled(False)
        
        self.int_validator = QIntValidator()
        self.lne_east.setValidator(self.int_validator)
        self.lne_west.setValidator(self.int_validator)
        self.lne_north.setValidator(self.int_validator)
        self.lne_south.setValidator(self.int_validator)
        
        self.lne_east.textChanged.connect(self.coordinates_valid)
        self.lne_west.textChanged.connect(self.coordinates_valid)
        self.lne_north.textChanged.connect(self.coordinates_valid)
        self.lne_south.textChanged.connect(self.coordinates_valid)
        
        self.overall_progressBar.setValue(0)

        
    @pyqtSlot()
    def on_button_box_rejected(self):
        """
        Slot documentation goes here.
        """
        self.close()

    @pyqtSlot()
    def on_btn_extent_clicked(self):
        """
        Slot documentation goes here.
        """
        crsDest = QgsCoordinateReferenceSystem(4326)  # WGS84
        
        if self.VERSION_INT < 29900:    # QGIS2
            crsSrc =self.iface.mapCanvas().mapRenderer().destinationCrs()    
            xform = QgsCoordinateTransform(crsSrc, crsDest)
        else:                                           # QGIS3
            crsSrc =self.iface.mapCanvas().mapSettings().destinationCrs()
            xform = QgsCoordinateTransform()
            xform.setSourceCrs(crsSrc)
            xform.setDestinationCrs(crsDest)
            
        extent = xform.transform(self.iface.mapCanvas().extent())        

        self.lne_west.setText(str(int(math.floor(extent.xMinimum()))))
        self.lne_east.setText(str(math.ceil(extent.xMaximum())))
        self.lne_south.setText(str(int(math.floor(extent.yMinimum()))))
        self.lne_north.setText(str(math.ceil(extent.yMaximum())))


    def coordinates_valid(self,  text):
        
        if self.lne_west.text() != '' and self.lne_east.text() != '' and self.lne_south.text() != '' and self.lne_north.text() != '':
            self.btn_download.setEnabled(True)
        else:
            self.btn_download.setEnabled(False)

    def get_tiles(self):
            
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            lat_diff = abs(int(self.lne_north.text()) - int(self.lne_south.text()))
            lon_diff = abs(int(self.lne_east.text()) - int(self.lne_west.text()))
            self.n_tiles = lat_diff * lon_diff
            self.image_counter = 0
            self.overall_progressBar.setMaximum(self.n_tiles)
            self.overall_progressBar.setValue(0)
            
            for lat in range(int(self.lne_south.text()), int(self.lne_north.text())):
                for lon in range(int(self.lne_west.text()), int(self.lne_east.text())):
                        if lon < 10 and lon >= 0:
                            lon_tx = "E00%s" % lon
                        elif lon >= 10 and lon < 100:
                            lon_tx = "E0%s" % lon
                        elif lon >= 100:
                            lon_tx = "E%s" % lon
                        elif lon > -10 and lon < 0:
                            lon_tx = "W00%s" % abs(lon)
                        elif lon <= -10 and lon > -100:
                            lon_tx = "W0%s" % abs(lon)
                        elif lon <= -100:
                            lon_tx = "W%s" % abs(lon)
    
                        if lat < 10 and lat >= 0:
                            lat_tx = "N0%s" % lat
                        elif lat >= 10 and lat < 100:
                            lat_tx = "N%s" % lat
                        elif lat > -10 and lat < 0:
                            lat_tx = "S0%s" % abs(lat)
                        elif lat < -10 and lat > -100:
                            lat_tx = "S%s" % abs(lat)
                        
                        try:
                            url = "https://e4ftl01.cr.usgs.gov//MODV6_Dal_D/SRTM/SRTMGL1.003/2000.02.11/%s%s.SRTMGL1.hgt.zip" % (lat_tx, lon_tx)
                            file = "%s/%s" % (self.dir,  url.split('/')[len(url.split('/'))-1])
                            
                            if len(QgsMapLayerRegistry.instance().mapLayersByName("%s%s.hgt" % (lat_tx,  lon_tx))) == 0:
                                self.downloader = Download(self,  self.iface)
                                if self.chk_load_image.checkState() == Qt.Checked:
                                    self.downloader.get_image(url,  file, True)
                                else:
                                    self.downloader.get_image(url,  file, False)
                            else:
                                progress_value = float(self.opener.overall_progressBar.value()) + 1
                                self.opener.overall_progressBar.setValue(progress_value)
                                print ("Progress-Value: %s" % progress_value)
                        except:
                            pass
    
            return True
            
    def download_finished(self):
        QApplication.restoreOverrideCursor()
        self.n_tiles = 0
        self.image_counter = 0
#        QMessageBox.information(None,  self.tr("Result"),  self.tr("Download completed"))

    @pyqtSlot()
    def on_btn_download_clicked(self):
        """
        Slot documentation goes here.
        """
        self.get_tiles()

    @pyqtSlot()
    def on_btn_file_dialog_clicked(self):
        """
        Slot documentation goes here.
        """
        from os.path import expanduser
        home = expanduser("~")
        self.dir = QFileDialog.getExistingDirectory(None, self.tr("Open Directory"),
                                                 home,
                                                 QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks)

        self.lne_SRTM_path.setText(self.dir)   
    
    @pyqtSlot()
    def on_btn_about_clicked(self):
        """
        Slot documentation goes here.
        """
        self.about = About()
        self.about.exec_()
      
