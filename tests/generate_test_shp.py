# -*- coding: utf-8 -*-
"""
generate_test_shp.py
Created by NCagle
2025-02-04
      _
   __(.)<
~~~⋱___)~~~


Generates test shapefiles for use in testing the ShapefileValidator.

This script creates three valid test shapefiles and three invalid test shapefiles.
The valid shapefiles contain different geometry types and attributes.
The invalid shapefiles contain various errors to test the ShapefileValidator's error detection.
All files use EPSG:4326 (WGS84) as the coordinate reference system.
Each geometry type has some basic attributes for testing attribute queries.
The shapefiles are saved in the "test_data" folder.

__Valid Shapefiles__
Polygons
    - 3 simple shapes (square, triangle, rectangle)
    - Includes attributes: id, name, area

Lines
    - 5 connected line segments forming a path
    - Includes attributes: id, segment name, approximate length

Points
    - 5 random points (with fixed seed for reproducibility)
    - Includes attributes: id, name, random value


__Invalid Shapefiles__
Empty Shapefile
    - Contains no features
    - Tests the "empty shapefile" check

Corrupt DBF
    - Has a truncated DBF file
    - Tests database file corruption detection

Missing Component
    - Missing the .shx file
    - Tests required component checking
"""
import os
import shutil
import geopandas as gpd
from shapely.geometry import (
    Polygon,
    LineString,
    Point,
    MultiPolygon
)
import numpy as np
from zipfile import ZipFile


# Valid data generation functions
def create_valid_test_polygons() -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame with 3 simple polygons.

    Returns:
        gdf (GeoDataFrame): GeoDataFrame with 3 polygons and basic attributes

    Notes:
        Creates polygons in EPSG:4326 (WGS84)
    """
    # Create three simple polygons
    polygons = [
        # Square
        Polygon([
            (-1, -1), (-1, 1), (1, 1), (1, -1), (-1, -1)
        ]),
        # Triangle
        Polygon([
            (2, 0), (3, 2), (4, 0), (2, 0)
        ]),
        # Rectangle
        Polygon([
            (-3, -2), (-3, 0), (-2, 0), (-2, -2), (-3, -2)
        ])
    ]

    # Create GeoDataFrame with attributes
    gdf = gpd.GeoDataFrame(
        {
            "id": range(1, 4),
            "name": ["Square", "Triangle", "Rectangle"],
            "area": [4.0, 2.0, 2.0],  # approximate areas
            "geometry": polygons
        },
        crs="EPSG:4326"
    )

    return gdf


def create_valid_test_lines() -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame with 5 connected line segments.

    Returns:
        gdf (GeoDataFrame): GeoDataFrame with 5 connected lines and basic attributes

    Notes:
        Creates lines in EPSG:4326 (WGS84)
    """
    # Create connected line segments forming a path
    lines = [
        LineString([(0, 0), (1, 1)]),
        LineString([(1, 1), (2, 0)]),
        LineString([(2, 0), (3, 2)]),
        LineString([(3, 2), (4, 1)]),
        LineString([(4, 1), (5, 0)])
    ]

    # Create GeoDataFrame with attributes
    gdf = gpd.GeoDataFrame(
        {
            "id": range(1, 6),
            "segment": ["A", "B", "C", "D", "E"],
            "length": [np.sqrt(2), np.sqrt(2), np.sqrt(5), np.sqrt(2), np.sqrt(2)],
            "geometry": lines
        },
        crs="EPSG:4326"
    )

    return gdf


def create_valid_test_points() -> gpd.GeoDataFrame:
    """
    Create a GeoDataFrame with 5 random points.

    Returns:
        gdf (GeoDataFrame): GeoDataFrame with 5 points and basic attributes

    Notes:
        Creates points in EPSG:4326 (WGS84)
        Uses fixed seed for reproducibility
    """
    # Set random seed for reproducibility
    np.random.seed(42)

    # Generate random points
    x = np.random.uniform(-5, 5, 5)
    y = np.random.uniform(-5, 5, 5)
    points = [Point(x, y) for x, y in zip(x, y)]

    # Create GeoDataFrame with attributes
    gdf = gpd.GeoDataFrame(
        {
            "id": range(1, 6),
            "name": [f"Point_{i}" for i in range(1, 6)],
            "value": np.random.randint(1, 100, 5),
            "geometry": points
        },
        crs="EPSG:4326"
    )

    return gdf


# Invalid data generation functions
def create_invalid_empty_shapefile(output_name: str):
    """
    Creates a shapefile with no features.

    Arguments:
        output_name (str): Base name for the shapefile (without extension)
    """
    empty_gdf = gpd.GeoDataFrame(
        columns=["id", "geometry"],
        geometry=[],
        crs="EPSG:4326"
    )
    empty_gdf.to_file(f"{output_name}.shp")


def create_corrupt_dbf(output_name: str):
    """
    Creates a shapefile with a corrupted DBF file.

    Arguments:
        output_name (str): Base name for the shapefile (without extension)
    """
    # First create a valid shapefile
    valid_gdf = create_valid_test_points()
    valid_gdf.to_file(f"{output_name}.shp")

    # Corrupt the DBF file by truncating it
    dbf_path = f"{output_name}.dbf"
    with open(dbf_path, "rb+") as f:
        f.truncate(len(f.read()) // 2)


def create_missing_component_shapefile(output_name: str):
    """
    Creates a shapefile set with a missing required component (.shx).

    Arguments:
        output_name (str): Base name for the shapefile (without extension)
    """
    # First create a valid shapefile
    valid_gdf = create_valid_test_points()
    valid_gdf.to_file(f"{output_name}.shp")

    # Remove the .shx file
    os.remove(f"{output_name}.shx")


if __name__ == "__main__":
    # Create zip files
    def _zip_shapefile(base_name: str):
        """
        Helper function to zip shapefile components.
        
        Arguments:
            base_name (str): Path to the shapefile without extension
        """
        # Get absolute paths
        abs_path = os.path.join(os.getcwd(), base_name)

        # List all files matching the base name
        files_to_zip = []
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            full_path = f"{abs_path}{ext}"
            if os.path.exists(full_path):
                files_to_zip.append(full_path)

        # Create zip file
        zip_path = f"{abs_path}.zip"
        with ZipFile(zip_path, "w") as zipf:
            for file in files_to_zip:
                # Add file to zip with just the filename (no path)
                zipf.write(file, os.path.basename(file))


    # Remove files after zip
    def _remove_zipped_source_files(base_name: str):
        """
        Helper function to remove the shapefile components after zipping.
        
        Arguments:
            base_name (str): Path to the shapefile without extension
        """
        # Get absolute paths
        abs_path = os.path.join(os.getcwd(), base_name)

        # Remove all files matching the base name
        for ext in [".shp", ".shx", ".dbf", ".prj", ".cpg"]:
            full_path = f"{abs_path}{ext}"
            if os.path.exists(full_path):
                os.remove(full_path)


    # Create directory for test data
    os.makedirs("test_data", exist_ok=True)
    os.makedirs("test_data/valid", exist_ok=True)
    os.makedirs("test_data/invalid", exist_ok=True)

    # Generate valid shapefiles
    valid_dir = "test_data/valid"
    polygons_gdf = create_valid_test_polygons()
    lines_gdf = create_valid_test_lines()
    points_gdf = create_valid_test_points()

    polygons_gdf.to_file(f"{valid_dir}/test_polygons.shp")
    lines_gdf.to_file(f"{valid_dir}/test_lines.shp")
    points_gdf.to_file(f"{valid_dir}/test_points.shp")

    # Generate invalid shapefiles
    invalid_dir = "test_data/invalid"
    create_invalid_empty_shapefile(f"{invalid_dir}/empty")
    create_corrupt_dbf(f"{invalid_dir}/corrupt_dbf")
    create_missing_component_shapefile(f"{invalid_dir}/missing_shx")

    # Zip valid files
    _zip_shapefile(f"{valid_dir}/test_polygons")
    _zip_shapefile(f"{valid_dir}/test_lines")
    _zip_shapefile(f"{valid_dir}/test_points")

    # Zip invalid files
    _zip_shapefile(f"{invalid_dir}/empty")
    _zip_shapefile(f"{invalid_dir}/corrupt_dbf")
    _zip_shapefile(f"{invalid_dir}/missing_shx")

    # Remove source files after zipping
    _remove_zipped_source_files(f"{valid_dir}/test_polygons")
    _remove_zipped_source_files(f"{valid_dir}/test_lines")
    _remove_zipped_source_files(f"{valid_dir}/test_points")
    _remove_zipped_source_files(f"{invalid_dir}/empty")
    _remove_zipped_source_files(f"{invalid_dir}/corrupt_dbf")
    _remove_zipped_source_files(f"{invalid_dir}/missing_shx")

    print("Test data generation complete!")
    print("\nValid test files:")
    print("- test_data/valid/test_polygons.zip (3 valid polygons)")
    print("- test_data/valid/test_lines.zip (5 connected lines)")
    print("- test_data/valid/test_points.zip (5 random points)")
    print("\nInvalid test files:")
    print("- test_data/invalid/empty.zip (shapefile with no features)")
    print("- test_data/invalid/corrupt_dbf.zip (corrupted DBF file)")
    print("- test_data/invalid/missing_shx.zip (missing .shx file)")
