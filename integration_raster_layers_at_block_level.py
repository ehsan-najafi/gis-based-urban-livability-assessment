
'''----------------------------------------------------------------------------------
 Name: Integration raster layers at urban block level
 Source: integration_raster_layers_at_block_level.py
 Version: ArcGIS 10.5 or later
 Authors: Ehsan Najafi and Mohammad Mahdi Najafi
----------------------------------------------------------------------------------'''
### Sample data for test: ./sample_data/sample_data.gdb


### Input data
in_raster_data = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\sample_raster"
in_urban_blocks = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\sample_urban_block"


### Import python modules
import arcpy, os, sys, tempfile

### Set environment settings
reload(sys)
sys.setdefaultencoding('utf8')
reload(sys)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False


### Set local address to save temporary data
env_path = tempfile.gettempdir() + "\\" + "PY_" + time.strftime("%Y%m%d_%I%M%S%p")
if not os.path.exists(env_path):
    os.makedirs(env_path)

### Create temporary geodatabase
gdb_temp_path = os.path.join(env_path, "temp.gdb")
arcpy.CreateFileGDB_management(os.path.dirname(gdb_temp_path), os.path.basename(gdb_temp_path))


### Create point feature class for urban blocks
in_urban_block_points = os.path.join(gdb_temp_path, "in_urban_block_points") 
if arcpy.Exists(in_urban_block_points):
    arcpy.Delete_management(in_urban_block_points)
arcpy.FeatureToPoint_management(in_urban_blocks, in_urban_block_points, "INSIDE")


### Calculate Average values of each urban block
outZonalStatistics = arcpy.sa.ZonalStatistics(in_urban_blocks, "BLOCK_ID", in_raster_data, "MEAN", "DATA")


### Assign Average Values to urban blocks
out_average_values = os.path.join(gdb_temp_path, "out_average_values") 
if arcpy.Exists(out_average_values):
    arcpy.Delete_management(out_average_values)
arcpy.sa.ExtractValuesToPoints(in_urban_block_points, outZonalStatistics, out_average_values, "NONE", "VALUE_ONLY")


### Create ditionary for assign average values to urban blocks
dict_average_values = {}
with arcpy.da.SearchCursor(out_average_values, ["BLOCK_ID", "RASTERVALU"]) as cursor:
    for row in cursor:
        sample_id = row[0]
        dict_average_values[sample_id] = row[1]


### Assign average values to urban blocks feature class
average_field = os.path.basename(in_raster_data)
if str(arcpy.ListFields(in_urban_blocks, average_field)) != "[]":
    arcpy.DeleteField_management(in_urban_blocks, average_field)
arcpy.AddField_management(in_urban_blocks, average_field, "DOUBLE")
with arcpy.da.UpdateCursor(in_urban_blocks ,["BLOCK_ID", average_field]) as UC:
    for row in UC:
        sample_id = row[0]
        row[1] = dict_average_values[sample_id]
        UC.updateRow(row)


