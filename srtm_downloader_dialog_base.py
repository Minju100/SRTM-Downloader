#!/usr/bin/python
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
        copyright            : (C) 2017 by Dr. Horst Duester
        email                : horst.duester@kappasys.ch
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
from qgis.core import QgsCoordinateReferenceSystem,  QgsCoordinateTransform
from qgis.PyQt import uic
from qgis.PyQt import QtNetwork
from qgis.PyQt.QtCore import pyqtSlot,  Qt,  QUrl,  QFileInfo
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import QDialog,  QMessageBox,  QTableWidgetItem,  QProgressBar,  QApplication,  QFileDialog
from .about.do_about import About
from .about.metadata import Metadata
from .download import Download

import math
import os
import tempfile

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'srtm_downloader_dialog_base.ui'))

IMAGE_URL = "https://e4ftl01.cr.usgs.gov/MEASURES/SRTMGL1.003/2000.02.11/"
        
class SrtmDownloaderDialogBase(QDialog, FORM_CLASS):
    """
    Class documentation goes here.
    """
    
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
        self.cancelled = False
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
        self.downloader = Download(self,  self.iface)
        self.progress_widget_item_list = {}
        self.row_count = 0
        self.progressTableWidget.setColumnCount(2)
        self.setWindowTitle("SRTM-Downloader %s" % (Metadata().version()))
                
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
        global IMAGE_URL
        lat_diff = abs(int(self.lne_north.text()) - int(self.lne_south.text()))
        lon_diff = abs(int(self.lne_east.text()) - int(self.lne_west.text()))
        self.n_tiles = lat_diff * lon_diff
        self.image_counter = 0
        self.init_progress()
        self.is_error = None

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
                    elif lat <= -10 and lat > -100:
                        lat_tx = "S%s" % abs(lat)
                    
                    url = "%s%s%s.SRTMGL1.hgt.zip" % (IMAGE_URL,  lat_tx, lon_tx)
                    file = "%s/%s" % (self.dir,  url.split('/')[len(url.split('/'))-1])
                    try:    
                        if not self.downloader.layer_exists('%s%s.hgt' % (lat_tx,  lon_tx)): 
                            if self.chk_load_image.checkState() == Qt.Checked:
                                self.downloader.get_image(url,  file, lat_tx, lon_tx, True)
                            else:
                                self.downloader.get_image(url,  file, lat_tx, lon_tx, False)
                        else:
                            self.set_progress()
                            self.download_finished(False)
                    except:
                        QMessageBox.warning(None,  self.tr("Error"),  self.tr("Wrong definition of coordinates"))
                        return False
        
        return True
            
            
    def download_finished(self,  show_message=True,  abort=False):
        if self.n_tiles == self.overall_progressBar.value() or abort:
            if show_message:
                if self.is_error != None:
                    QMessageBox.information(None, 'Error',  self.is_error)
                else:
                    QMessageBox.information(None,  self.tr("Result"),  self.tr("Download completed"))
                
            self.button_box.setEnabled(True)
            self.n_tiles = 0
            self.image_counter = 0
        
        QApplication.restoreOverrideCursor()
            
            
    @pyqtSlot()
    def on_btn_download_clicked(self):
        """
        Slot documentation goes here.
        """
        self.progressTableWidget.clear()
        self.row_count = 0
        self.button_box.setEnabled(False)
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
        
    def init_progress(self):
        self.overall_progressBar.setMaximum(self.n_tiles)
        self.overall_progressBar.setValue(0)
        self.lbl_file_download.setText((self.tr("Download-Progress: %s of %s images") % (0,  self.n_tiles)))
        
        
    def add_download_progress(self,  reply):
        is_image = QFileInfo(reply.url().path()).completeSuffix() == 'SRTMGL1.hgt.zip'
        if is_image:
            self.progressTableWidget.setRowCount(self.row_count+1)
            self.progressTableWidget.setItem(self.row_count,  0,  QTableWidgetItem(QFileInfo(reply.url().path()).baseName(),  Qt.DisplayRole))
            self.progressTableWidget.setCellWidget(self.row_count, 1,  QProgressBar())
            self.progress_widget_item_list[QFileInfo(reply.url().path()).baseName()] = self.row_count
            self.row_count += 1
        
    def set_progress(self,  akt_val=None,  all_val=None):
        if all_val == None:
            progress_value = self.overall_progressBar.value() + 1
            self.overall_progressBar.setValue(progress_value)
            self.lbl_file_download.setText((self.tr("Download-Progress: %s of %s images") % (progress_value,  self.n_tiles)))
                    
            if progress_value == self.n_tiles:
                self.lbl_file_download.setText((self.tr("Download-Progress: %s of %s images") % (progress_value,  self.n_tiles)))
                self.download_finished(show_message=True)
        else:
            self.overall_progressBar.setMaximum(all_val)
            self.overall_progressBar.setValue(akt_val)
