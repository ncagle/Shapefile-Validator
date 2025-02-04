# -*- coding: utf-8 -*-
"""
shapefile_validator.py
Created by NCagle
2025-02-04
      _
   __(.)<
~~~⋱___)~~~

Simple GUI that uses geopandas to check if zipped shapefiles
are valid and can be opened.
"""
import zipfile
import os
from pathlib import Path
import tempfile
import logging
from typing import Tuple, Optional
import tkinter as tk
from tkinter import filedialog, ttk
from threading import Thread
import tkinterdnd2 as tkdnd
import geopandas as gpd


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ShapefileValidatorGUI:
    """
    GUI interface for validating zipped shapefiles with drag and drop support.
    """
    def __init__(self):
        self.root = tkdnd.Tk()
        self.root.title("Shapefile Validator")

        # Set minimum window size
        self.root.minsize(500, 300)

        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)

        # Create and pack widgets
        self.setup_ui()

        # Center window on screen
        self.center_window()


    def setup_ui(self):
        """Set up the GUI elements"""
        # File selection frame
        select_frame = ttk.Frame(self.root)
        select_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        select_frame.grid_columnconfigure(0, weight=1)

        self.path_var = tk.StringVar()
        self.path_entry = ttk.Entry(select_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        self.browse_btn = ttk.Button(select_frame, text="Browse", command=self.browse_file)
        self.browse_btn.grid(row=0, column=1)

        # Drop zone frame
        self.drop_frame = ttk.LabelFrame(self.root, text="Drop Zone")
        self.drop_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.drop_frame.grid_columnconfigure(0, weight=1)
        self.drop_frame.grid_rowconfigure(0, weight=1)

        # Drop zone label
        self.drop_label = ttk.Label(
            self.drop_frame,
            text="Drag and drop a zipped shapefile here\nor click Browse to select a file",
            justify="center"
        )
        self.drop_label.grid(row=0, column=0, padx=20, pady=20)

        # Configure drop zone
        self.drop_frame.drop_target_register('DND_Files')
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.drop_frame.bind('<Enter>', self.on_drag_enter)
        self.drop_frame.bind('<Leave>', self.on_drag_leave)

        # Validate button
        self.validate_btn = ttk.Button(
            self.root, 
            text="Validate Shapefile", 
            command=self.validate_threaded
        )
        self.validate_btn.grid(row=2, column=0, pady=10)

        # Status display
        self.status_text = tk.Text(
            self.root, 
            height=5, 
            wrap=tk.WORD, 
            state="disabled"
        )
        self.status_text.grid(row=3, column=0, padx=10, pady=(0, 10), sticky="nsew")


    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")


    def handle_drop(self, event):
        """Handle file drop events"""
        file_path = event.data

        # Clean up the file path (handle quotes and curly braces)
        file_path = file_path.strip('{}').strip('"')

        if file_path.lower().endswith('.zip'):
            self.path_var.set(file_path)
            self.validate_threaded()
        else:
            self.update_status("Please drop a .zip file", True)


    def on_drag_enter(self, event):
        """Visual feedback when dragging over drop zone"""
        self.drop_label.configure(text="Release to validate file")
        self.drop_frame.configure(style="Highlight.TLabelframe")


    def on_drag_leave(self, event):
        """Reset visual feedback when leaving drop zone"""
        self.drop_label.configure(
            text="Drag and drop a zipped shapefile here\nor click Browse to select a file"
        )
        self.drop_frame.configure(style="TLabelframe")


    def browse_file(self):
        """Open file dialog for selecting a zipped shapefile"""
        filename = filedialog.askopenfilename(
            title="Select Zipped Shapefile",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")]
        )
        if filename:
            self.path_var.set(filename)


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
        self.validate_btn.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.update_status("Validating...")

        Thread(target=self.validate_file, daemon=True).start()


    def validate_file(self):
        """Validate the selected shapefile"""
        try:
            zip_path = self.path_var.get()
            is_valid, error_msg = validate_zipped_shapefile(zip_path)

            if is_valid:
                self.root.after(0, self.update_status, "Shapefile is valid and can be opened")
            else:
                self.root.after(0, self.update_status, f"Validation failed: {error_msg}", True)
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

    # Create custom style for drop zone highlight
    style = ttk.Style()
    style.configure("Highlight.TLabelframe", background="#e1e1e1")

    app.root.mainloop()
