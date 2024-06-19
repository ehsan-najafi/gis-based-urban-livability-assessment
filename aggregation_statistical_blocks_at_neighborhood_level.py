
'''----------------------------------------------------------------------------------
 Name: Statistical data aggregation
 Source: aggregation_statistical_blocks_at_neighborhood_level.py
 Version: ArcGIS 10.5 or later
 Authors: Ehsan Najafi and Mohammad Mahdi Najafi
----------------------------------------------------------------------------------'''
###  Sample data for test: ./sample_data/sample_data.gdb


### Input data
in_urban_blocks = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\sample_urban_block"
in_neighborhoods = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\sample_neighborhood"
statistical_fields = ['Population']


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


### Spatial join blocks and neighborhoods where 
out_joined_blocks_fc = os.path.join(gdb_temp_path, "joined_blocks")
if arcpy.Exists(out_joined_blocks_fc):
    arcpy.Delete_management(out_joined_blocks_fc)
arcpy.SpatialJoin_analysis(in_urban_blocks, in_neighborhoods, out_joined_blocks_fc, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "COMPLETELY_WITHIN", "", "")


### Create ditionary for assign neighborhoods ID for each urban block
dict_neighborhood_Ids = {}
with arcpy.da.SearchCursor(out_joined_blocks_fc, ["NEIGHBORHOOD_ID", "BLOCK_ID"]) as cursor:
    for row in cursor:
        neighborhood_id = row[0]
        block_id = row[1]
        dict_neighborhood_Ids[block_id] = neighborhood_id


### Calculate summerize for statistical fields
out_summerize_table = gdb_temp_path + "\\" + "out_summerize_table"
if arcpy.Exists(out_summerize_table):
    arcpy.Delete_management(out_summerize_table)
summrize_fields = []
for field_name in statistical_fields:
    summrize_fields.append([field_name, 'SUM'])
arcpy.Statistics_analysis(out_joined_blocks_fc, out_summerize_table, summrize_fields, case_field='NEIGHBORHOOD_ID')


### Add New Statistical Fields in Neighborhood Featureclass
for field in statistical_fields:
    summrize_field = "SUM_" + field

    ### Create ditionary for assign summrize values to neighborhoods feature class
    dict_summrize_values = {}
    with arcpy.da.SearchCursor(out_summerize_table, ["NEIGHBORHOOD_ID", summrize_field]) as cursor:
        for row in cursor:
            sample_id = row[0]
            dict_summrize_values[sample_id] = row[1]

    ### Assign summrize values to neighborhoods feature class
    if str(arcpy.ListFields(in_neighborhoods, summrize_field)) != "[]":
        arcpy.DeleteField_management(in_neighborhoods, summrize_field) 
    arcpy.AddField_management(in_neighborhoods, summrize_field, "DOUBLE")
    with arcpy.da.UpdateCursor(in_neighborhoods ,["NEIGHBORHOOD_ID", summrize_field]) as UC:
        for row in UC:
            neighborhood_id = row[0]
            row[1] = dict_summrize_values[neighborhood_id]
            UC.updateRow(row)

    ### Assign summrize values to neighborhoods feature class
    if str(arcpy.ListFields(in_urban_blocks, summrize_field)) != "[]":
        arcpy.DeleteField_management(in_urban_blocks, summrize_field)
    arcpy.AddField_management(in_urban_blocks, summrize_field, "DOUBLE")
    with arcpy.da.UpdateCursor(in_urban_blocks, ["BLOCK_ID", summrize_field]) as UC:
        for row in UC:
            block_id = row[0]
            neighborhood_id = dict_neighborhood_Ids[block_id]
            row[1] = dict_summrize_values[neighborhood_id]
            UC.updateRow(row)


