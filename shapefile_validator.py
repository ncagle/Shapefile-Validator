# -*- coding: utf-8 -*-
r"""
shapefile_validator.py
Created by NCagle
2025-02-04
      _
   __(.)<
~~~⋱___)~~~

Simple GUI that uses geopandas to check if zipped shapefiles
are valid and can be opened.

GUI Instructions:
Click Browse to add zipped shapefiles. Multiple can be added at once
Select files in the list below and click Remove Selected to remove them
Click Validate Shapefiles to check all files in the list

Using PyInstaller to package as an executable.
With GDAL explicitly installed (much larger executable size)
pyinstaller --name ShapefileValidator --onefile --windowed ^
    --additional-hooks-dir=. ^
    --hidden-import fiona.ogrext ^
    --hidden-import geopandas ^
    --hidden-import pyogrio._geometry ^
    --hidden-import fiona ^
    --hidden-import pyogrio ^
    --add-binary "C:\Users\NatCagle\Anaconda3\envs\pyinstaller\Library\bin\gdal*.dll;." ^
    --add-binary "C:\Users\NatCagle\Anaconda3\envs\pyinstaller\Library\bin\geos*.dll;." ^
    --add-binary "C:\Users\NatCagle\Anaconda3\envs\pyinstaller\Library\bin\proj*.dll;." ^
    --add-binary "C:\Users\NatCagle\Anaconda3\envs\pyinstaller\Library\bin\sqlite*.dll;." ^
    shapefile_validator.py

With GDAL bundled with pyogrio as a dependency of geopandas (smaller executable size)
pyinstaller --name ShapefileValidator --onefile --windowed ^
    --additional-hooks-dir=. ^
    --hidden-import geopandas ^
    --hidden-import pyogrio._geometry ^
    --add-binary "C:\Users\NatCagle\Anaconda3\envs\shapefile-validator\Lib\site-packages\pyogrio.libs\gdal-debee5933f0da7bb90b4bcd009023377.dll;." ^
    shapefile_validator.py
"""
import sys
import os
from pathlib import Path
import tempfile
import logging
from typing import Tuple, Optional, List, Dict
import zipfile
import tkinter as tk
from tkinter import filedialog, ttk
from threading import Thread


# # Fix PATH for PyInstaller bundle
# # Checks if running in a PyInstaller bundle using sys.frozen
# if getattr(sys, "frozen", False):
#     # Gets the temporary directory path where PyInstaller extracts files using sys._MEIPASS
#     bundle_dir = sys._MEIPASS
#     # Adds this directory to the system PATH before any other imports
#     os.environ["PATH"] = f"{bundle_dir};" + os.environ['PATH']
#     # Also try setting GDAL_DATA
#     gdal_data = os.path.join(bundle_dir, "Library", "share", "gdal")
#     if os.path.exists(gdal_data):
#         os.environ["GDAL_DATA"] = gdal_data

import geopandas as gpd


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShapefileValidatorGUI:
    """
    GUI interface for validating multiple zipped shapefiles.
    """
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Shapefile Validator by NCagle")

        # Set minimum window size
        self.root.minsize(600, 400)

        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # Dictionary to store files and their validation status
        self.files: Dict[str, bool] = {}

        # Create and pack widgets
        self.setup_ui()

        # Center window on screen
        self.center_window()


    def setup_ui(self):
        """Set up the GUI elements"""
        # File selection frame
        select_frame = ttk.Frame(self.root)
        select_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        select_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(select_frame, text="Files to validate:").grid(row=0, column=0, padx=5)

        self.file_count_label = ttk.Label(select_frame, text="0 files selected")
        self.file_count_label.grid(row=0, column=1, padx=5)

        self.browse_btn = ttk.Button(select_frame, text="Browse", command=self.browse_files)
        self.browse_btn.grid(row=0, column=2)

        self.clear_btn = ttk.Button(select_frame, text="Clear All", command=self.clear_files)
        self.clear_btn.grid(row=0, column=3, padx=(5, 0))

        # Instructions frame
        self.instructions_frame = ttk.LabelFrame(self.root, text="Instructions")
        self.instructions_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.instructions_frame.grid_columnconfigure(0, weight=1)
        self.instructions_frame.grid_rowconfigure(0, weight=1)

        instructions = (
            "Click Browse to add zipped shapefiles. Multiple can be added at once\n"
            "Select files in the list below and click Remove Selected to remove them\n"
            "Click Validate Shapefiles to check all files in the list"
        )

        self.instruction_label = ttk.Label(
            self.instructions_frame,
            text=instructions,
            justify="left"
        )
        self.instruction_label.grid(row=0, column=0, padx=20, pady=20)

        # File list
        self.file_list = tk.Listbox(
            self.root,
            selectmode=tk.EXTENDED,
            height=6
        )
        self.file_list.grid(row=2, column=0, padx=10, sticky="nsew")

        # Scrollbar for file list
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)

        # Progress frame
        progress_frame = ttk.Frame(self.root)
        progress_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=200
        )
        self.progress.grid(row=0, column=0, sticky="ew")

        # Buttons frame
        button_frame = ttk.Frame(self.root)
        button_frame.grid(row=4, column=0, columnspan=2, pady=5)

        self.validate_btn = ttk.Button(
            button_frame,
            text="Validate Shapefiles",
            command=self.validate_threaded
        )
        self.validate_btn.pack(side=tk.LEFT, padx=5)

        self.remove_btn = ttk.Button(
            button_frame,
            text="Remove Selected",
            command=self.remove_selected
        )
        self.remove_btn.pack(side=tk.LEFT, padx=5)

        # Status display
        self.status_text = tk.Text(
            self.root,
            height=10,
            wrap=tk.WORD,
            state="disabled"
        )
        self.status_text.grid(row=5, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")


    def update_file_count(self):
        """Update the file count label"""
        count = len(self.files)
        self.file_count_label.configure(
            text=f"{count} {'file' if count == 1 else 'files'} selected"
        )


    def clear_files(self):
        """Clear all files from the list"""
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self.update_file_count()
        self.update_status("All files cleared")


    def remove_selected(self):
        """Remove selected files from the list"""
        selected = self.file_list.curselection()
        for index in reversed(selected):
            file_path = self.file_list.get(index)
            self.files.pop(file_path, None)
            self.file_list.delete(index)
        self.update_file_count()


    def add_files(self, file_paths: List[str]):
        """Add files to the validation list"""
        for path in file_paths:
            if path.lower().endswith('.zip') and path not in self.files:
                self.files[path] = None
                self.file_list.insert(tk.END, path)
        self.update_file_count()


    def browse_files(self):
        """Open file dialog for selecting multiple zipped shapefiles"""
        filenames = filedialog.askopenfilenames(
            title="Select Zipped Shapefiles",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
        )
        if filenames:
            self.add_files(filenames)


    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")


    def update_status(self, message: str, is_error: bool = False):
        """Update the status display with a message"""
        self.status_text.configure(state="normal")
        self.status_text.delete(1.0, tk.END)
        if is_error:
            self.status_text.insert(tk.END, f"❌ {message}")
        else:
            self.status_text.insert(tk.END, f"✓ {message}")
        self.status_text.configure(state="disabled")


    def validate_threaded(self):
        """Run validation in a separate thread to prevent GUI freezing"""
        if not self.files:
            self.update_status("No files selected to validate", True)
            return

        self.validate_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.update_status("Validating files...")
        self.progress['value'] = 0

        Thread(target=self.validate_files, daemon=True).start()


    def validate_files(self):
        """Validate all selected shapefiles"""
        try:
            total_files = len(self.files)
            progress_step = 100.0 / total_files
            results = []

            for i, file_path in enumerate(self.files.keys()):
                is_valid, error_msg = validate_zipped_shapefile(file_path)
                results.append((file_path, is_valid, error_msg))

                # Update progress
                self.root.after(0, self.progress.configure, {'value': (i + 1) * progress_step})

            # Format results message
            valid_count = sum(1 for _, is_valid, _ in results if is_valid)
            message = f"Validation complete: {valid_count}/{total_files} files valid\n\n"

            for file_path, is_valid, error_msg in results:
                filename = os.path.basename(file_path)
                if is_valid:
                    message += f"✓ {filename}: Valid\n"
                else:
                    message += f"❌ {filename}: {error_msg}\n"

            self.root.after(0, self.update_status, message)

        finally:
            self.root.after(0, self.validate_btn.configure, {"state": "normal"})
            self.root.after(0, self.browse_btn.configure, {"state": "normal"})


def validate_zipped_shapefile(zip_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a zipped shapefile by attempting to extract and read it.

    Arguments:
        zip_path (str): Path to the zipped shapefile

    Returns:
        success (bool): True if shapefile is valid, False otherwise
        error_msg (Optional[str]): Description of error if validation fails, None if successful

    Notes:
        - Checks both zip integrity and shapefile validity
        - Requires the following shapefile components: .shp, .shx, .dbf
        - Performs validation in a temporary directory to avoid cleanup
    """
    try:
        # Verify zip file exists
        if not os.path.exists(zip_path):
            return False, f"File not found: {zip_path}"

        # Check if file is actually a zip
        if not zipfile.is_zipfile(zip_path):
            return False, "File is not a valid zip archive"

        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to extract the zip file
            try:
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
            except zipfile.BadZipFile:
                return False, "Corrupt zip file - cannot extract contents"

            # Look for .shp file in extracted contents
            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                return False, "No .shp file found in zip archive"

            # Verify essential shapefile components exist
            shp_path = shp_files[0]
            base_path = str(shp_path)[:-4]  # Remove .shp extension
            for ext in [".shx", ".dbf"]:
                if not os.path.exists(base_path + ext):
                    return False, f"Missing required shapefile component: {ext}"

            # Attempt to read the shapefile
            try:
                gdf = gpd.read_file(shp_path)
                if len(gdf) == 0:
                    return False, "Shapefile contains no features"
                return True, None
            except Exception as e:
                return False, f"Error reading shapefile: {str(e)}"

    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


if __name__ == "__main__":
    app = ShapefileValidatorGUI()
    app.root.mainloop()
