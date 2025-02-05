from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all submodules
hiddenimports = collect_submodules("geopandas")
hiddenimports += [
    "fiona",
    "fiona.ogrext",
    "pyproj",
    "numpy",
    "pandas",
    "shapely.geometry",
    "shapely.wkb",
    "shapely.wkt"
]

# Collect data files
datas = collect_data_files("geopandas")
