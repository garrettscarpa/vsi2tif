#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 29 10:47:20 2024
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import imagej
import scyjava as sj
import tifffile as tiff
import gc
from PyQt5 import QtWidgets

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VSI to TIFF Converter")
        self.setup_ui()
    
    def setup_ui(self):
        layout = QtWidgets.QGridLayout(self)

        # VSI Folder Selection
        layout.addWidget(QtWidgets.QLabel("Select VSI Folder:"), 0, 0)
        self.vsi_folder_entry = QtWidgets.QLineEdit()
        layout.addWidget(self.vsi_folder_entry, 0, 1)
        vsi_folder_button = QtWidgets.QPushButton("Browse")
        vsi_folder_button.clicked.connect(self.browse_vsi_folder)
        layout.addWidget(vsi_folder_button, 0, 2)

        # TIFF Folder Selection
        layout.addWidget(QtWidgets.QLabel("Select TIFF Folder:"), 1, 0)
        self.tif_folder_entry = QtWidgets.QLineEdit()
        layout.addWidget(self.tif_folder_entry, 1, 1)
        tif_folder_button = QtWidgets.QPushButton("Browse")
        tif_folder_button.clicked.connect(self.browse_tif_folder)
        layout.addWidget(tif_folder_button, 1, 2)

        # Memory Allocation
        layout.addWidget(QtWidgets.QLabel("Gigs of Memory (default 28):"), 2, 0)
        self.memory_entry = QtWidgets.QLineEdit()
        self.memory_entry.setText("28")  # Set default value to 28
        layout.addWidget(self.memory_entry, 2, 1)

        # Parallel Processes Input
        layout.addWidget(QtWidgets.QLabel("Number of Parallel Processes (default 2):"), 3, 0)
        self.process_entry = QtWidgets.QLineEdit()
        self.process_entry.setText("2")  # Default to 2 parallel processes
        layout.addWidget(self.process_entry, 3, 1)

        # Start Conversion Button
        start_button = QtWidgets.QPushButton("Start Conversion")
        start_button.clicked.connect(self.run_conversion)
        layout.addWidget(start_button, 4, 1)

    def browse_vsi_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select VSI Folder")
        if folder:
            self.vsi_folder_entry.setText(folder)

    def browse_tif_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select TIFF Folder")
        if folder:
            self.tif_folder_entry.setText(folder)

    def run_conversion(self):
        vsi_folder = self.vsi_folder_entry.text()
        tif_folder = self.tif_folder_entry.text()

        # Get memory allocation
        try:
            memory_input = self.memory_entry.text()
            gigs_of_memory = int(memory_input) if memory_input else 28
            if gigs_of_memory <= 0:
                raise ValueError("Memory must be a positive integer.")
        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Input Error", f"Invalid memory input: {ve}")
            return

        # Get number of parallel processes
        try:
            process_input = self.process_entry.text()
            max_workers = int(process_input) if process_input else 2
            if max_workers <= 0:
                raise ValueError("Processes must be a positive integer.")
        except ValueError as ve:
            QtWidgets.QMessageBox.critical(self, "Input Error", f"Invalid process input: {ve}")
            return

        sj.config.add_option(f'-Xmx{gigs_of_memory}g')  # Set memory allocation
        ij = imagej.init('sc.fiji:fiji', mode='headless')  # Initialize ImageJ in headless mode

        # Get and sort VSI files in alphabetical order
        vsi_files = sorted([f for f in os.listdir(vsi_folder) if f.endswith('.vsi')])
        if not vsi_files:
            QtWidgets.QMessageBox.information(self, "No Files", "No VSI files found in the selected folder.")
            return

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(convert_vsi_to_tif, file, vsi_folder, tif_folder, ij): file for file in vsi_files}
            for future in as_completed(futures):
                file = futures[future]
                try:
                    future.result()
                    print(f"Processed {file} successfully.")
                except Exception as e:
                    print(f"Error processing {file}: {e}")

        QtWidgets.QMessageBox.information(self, "Completion", "All conversions completed.")

# Function to convert VSI files to TIFF format
def convert_vsi_to_tif(vsi_file, vsi_folder, tif_folder, ij):
    image_url = os.path.join(vsi_folder, vsi_file)
    save_url = os.path.join(tif_folder, vsi_file.split('.vsi')[0] + '.tif')

    options = sj.jimport('loci.plugins.in.ImporterOptions')()
    options.setOpenAllSeries(True)
    options.setVirtual(True)
    options.setId(image_url)

    try:
        jimage = ij.io().open(image_url, options={'useBioFormats': True})
        image_array = ij.py.from_java(jimage)
        image_array_np = image_array.values

        tiff.imwrite(save_url, image_array_np)
        print(f"Image saved successfully to {save_url}.")
    except Exception as e:
        print(f"Error during conversion of {vsi_file}: {e}")
    finally:
        if 'image_array' in locals():
            del image_array
        if 'jimage' in locals():
            del jimage
        gc.collect()

if __name__ == "__main__":
    app = QtWidgets.QApplication([])
    window = MainWindow()
    window.show()
    app.exec_()
