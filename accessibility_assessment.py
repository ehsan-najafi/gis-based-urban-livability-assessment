'''----------------------------------------------------------------------------------
 Name: Spatial accessibility Assessment
 Source: accessibility_assessment.py
 Version: ArcGIS 10.5 or later
 Authors: Ehsan Najafi and Mohammad Mahdi Najafi
----------------------------------------------------------------------------------'''
###  Sample data for test: /sample_data/sample_data.gdb AND /sample_data/accessibility_thresholds.xls


### Input data
in_network_dataset = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\network_dataset\network_dataset_ND"
in_poi_dataset = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\poi"
in_urban_blocks = r"C:\gis-based-urban-livability-assessment\sample_data\sample_data.gdb\sample_urban_block"
accessibility_defination_excel_path = r"C:\gis-based-urban-livability-assessment\sample_data\accessibility_thresholds.xls"


### Import python modules
import arcpy, os, sys, tempfile

### Set environment settings
reload(sys)
sys.setdefaultencoding('utf8')
reload(sys)
arcpy.env.overwriteOutput = True
arcpy.env.addOutputsToMap = False


### Set local address to save temp data in user temp
env_path = tempfile.gettempdir() + "\\" + "PY_" + time.strftime("%Y%m%d_%I%M%S%p")
if not os.path.exists(env_path):
    os.makedirs(env_path)

### Create Temporary Geodatabase
gdb_temp_path = os.path.join(env_path, "temp.gdb")
arcpy.CreateFileGDB_management(os.path.dirname(gdb_temp_path), os.path.basename(gdb_temp_path))


#### Read accessibility defination excel file
accessibility_defination_table = os.path.join(gdb_temp_path, "accessibility_defination")
arcpy.ExcelToTable_conversion(accessibility_defination_excel_path, accessibility_defination_table)
dict_accessibility_defination = {}
with arcpy.da.SearchCursor(accessibility_defination_table, ["poi_layer", "min_dist", "max_dist", "min_area", "max_area"]) as sc:
    for row in sc:
        dict_accessibility_defination[row[0]] = [row[1], row[2], row[3], row[4]]


### Create point featureclass for urban blocks
in_urban_block_points = os.path.join(gdb_temp_path, "in_urban_block_points") 
if arcpy.Exists(in_urban_block_points):
    arcpy.Delete_management(in_urban_block_points)
arcpy.FeatureToPoint_management(in_urban_blocks, in_urban_block_points, "INSIDE")
origins_layer = arcpy.MakeFeatureLayer_management(in_urban_block_points, "origins_layer", "", "")


### Calculate accessibility to each poi_data (defined in excel file)
for poi_name in dict_accessibility_defination.keys():
    accessibility_defs = dict_accessibility_defination[poi_name]
    minimum_distance_or_time = float(accessibility_defs[0])
    maximum_distance_or_time = float(accessibility_defs[1])
    minimum_parks_area = float(accessibility_defs[2])
    maximum_parks_area = float(accessibility_defs[3])
    in_poi_points = os.path.join(in_poi_dataset, poi_name)  

    ### Create temportary featureclass for poi points
    in_poi_points_temp = os.path.join(gdb_temp_path, poi_name + "_temp") 
    if arcpy.Exists(in_poi_points_temp):
        arcpy.Delete_management(in_poi_points_temp)
    arcpy.FeatureClassToFeatureClass_conversion(in_poi_points, os.path.dirname(in_poi_points_temp), os.path.basename(in_poi_points_temp), "")
    poi_layer = arcpy.MakeFeatureLayer_management(in_poi_points_temp, poi_name + "_layer", "", "")

    ### Create origins Dictionary
    dict_origins_ID = {}
    oid_urban_blocks = arcpy.ListFields(in_urban_block_points, "", "OID")[0].name
    with arcpy.da.SearchCursor(in_urban_block_points, [oid_urban_blocks, "BLOCK_ID"]) as cursor:
        for row in cursor:
            oid = row[0]
            dict_origins_ID[oid] = row[1]
    dict_poi_ID_Area = {}
    oid_poi_points = arcpy.ListFields(in_poi_points_temp, "", "OID")[0].name
    with arcpy.da.SearchCursor(in_poi_points_temp, [oid_poi_points, "POI_ID", "poi_area"]) as cursor:
        for row in cursor:
            oid = row[0]
            dict_poi_ID_Area[oid] = [row[1], row[2]]

    ### Process: create OD Cost Matrix Layer
    OD_Cost_Matrix = poi_name + "_odcm_layer"
    arcpy.MakeODCostMatrixLayer_na(in_network_dataset, OD_Cost_Matrix, "Length", str(maximum_distance_or_time), "", "", "ALLOW_UTURNS", "", "NO_HIERARCHY","", "STRAIGHT_LINES", "")

    ### Add urban blocks as origins locations to network analysis
    arcpy.AddLocations_na(OD_Cost_Matrix, "Origins", origins_layer, "", "5000 Meters", "", "roads_drive SHAPE;network_dataset_ND_Junctions NONE", "MATCH_TO_CLOSEST", "APPEND", "NO_SNAP", "5 Meters", "INCLUDE", "roads_drive #;network_dataset_ND_Junctions #")
    
    ### Add current POI features as destinations to network analysis
    arcpy.AddLocations_na(OD_Cost_Matrix, "Destinations", poi_layer, "Name Name #", "5000 Meters", "", "roads_drive SHAPE;network_dataset_ND_Junctions NONE", "MATCH_TO_CLOSEST", "APPEND", "NO_SNAP", "5 Meters", "INCLUDE", "roads_drive #;network_dataset_ND_Junctions #")
    
    ### Solve network analysis
    arcpy.Solve_na(OD_Cost_Matrix, "SKIP", "TERMINATE", "")

    ### Add field
    in_route_lines = os.path.join(gdb_temp_path, poi_name + "_route_lines") 
    if arcpy.Exists(in_route_lines):
        arcpy.Delete_management(in_route_lines)
    arcpy.CopyFeatures_management(OD_Cost_Matrix + "/Lines", in_route_lines, "", "0", "0", "0")
    arcpy.AddField_management(in_route_lines, "ORG_ID", "LONG")
    arcpy.AddField_management(in_route_lines, "POI_ID", "LONG")
    arcpy.AddField_management(in_route_lines, "POI_AREA", "DOUBLE")

    with arcpy.da.UpdateCursor(in_route_lines ,["OriginID", "DestinationID", "ORG_ID", "POI_ID", "POI_AREA"]) as UC:
        for row in UC:
            row[2] = dict_origins_ID[row[0]]
            poi_ID_Area = dict_poi_ID_Area[row[1]]
            row[3] = poi_ID_Area[0]
            row[4] = poi_ID_Area[1]
            UC.updateRow(row)

    dict_access_score = {}
    with arcpy.da.SearchCursor(in_urban_block_points, ["BLOCK_ID"]) as cursor:
        for row in cursor:
            org_id = row[0]
            dict_access_score[org_id] = 0.0

    with arcpy.da.SearchCursor(in_route_lines, ["ORG_ID", "POI_ID", "POI_AREA", "Total_Length"]) as cursor:
        for row in cursor:
            org_id = row[0]
            poi_id = row[1]
            poi_area = row[2]
            total_length = row[3]

            ### Find normalized distance (for current route)
            if total_length <= minimum_distance_or_time:
                score_dist = 1.0
            elif total_length > minimum_distance_or_time and total_length <= maximum_distance_or_time:
                score_dist = (1.0 - (float(total_length - minimum_distance_or_time)/float(maximum_distance_or_time - minimum_distance_or_time)))
            elif total_length > minimum_distance_or_time:
                score_dist = 0.0

            ### Find normalized area (for current route)
            if poi_area >= maximum_parks_area:
                score_area = 1.0
            elif poi_area >= minimum_parks_area and poi_area < maximum_parks_area:
                score_area = float(poi_area - minimum_parks_area)/float(maximum_parks_area-minimum_parks_area)
            elif poi_area < minimum_parks_area:
                score_area = 0.0

            ### Calculate accessibility score            
            accessibility_score = score_area * score_dist

            ### Add accessibility scores to dictionary
            if org_id not in dict_access_score.keys():
                dict_access_score[org_id] = accessibility_score
            else:
                dict_access_score[org_id] = dict_access_score[org_id] + accessibility_score


    ### Create field for calculate accessibility values of current POI
    poi_access_score_field = "ACC_" + poi_name
    if str(arcpy.ListFields(in_urban_blocks, poi_access_score_field)) != "[]":
        arcpy.DeleteField_management(in_urban_blocks, poi_access_score_field)
    arcpy.AddField_management(in_urban_blocks, poi_access_score_field, "DOUBLE")

    ### Calculate accessibility values of current POI
    with arcpy.da.UpdateCursor(in_urban_blocks ,["BLOCK_ID", poi_access_score_field]) as UC:
        for row in UC:
            origid = row[0]
            accessibility_score = float(dict_access_score[origid])
            row[1] = accessibility_score
            UC.updateRow(row)



