# Sentinel Rat Dashboard

Work in progress...

## Overview

R Shiny application for browsing animal detection results from PostgreSQL (PostGIS).

## Scaffolded code

* Initialize a PostgreSQL database with PostGIS extension
* Display results fetched from a database in a table

## Database

### Data Model

There are 12 tables in the database, which are defined in `src/dashboard/db/data_model.py`. The data model is illustrated in the following figure:

[Figure of data model here...]()

### Folder structure

```
src/dashboard/db/
├── database.py # set up the database connection and session
├── data_model.py # define the SQLAlchemy data model
├── crud.py # define the CRUD operations for the data model
├── utils.py # utility functions
├── <table_name>.py # define the CRUD operations for each table
```

CRUD operations are defined in general in `crud.py` and then specialized for each table in `<table_name>.py`, if needed.

**Note**:

* `camera.py` covers both `Camera` and `CameraLocationHistory` tables
* `detection.py` covers both `ObjectDetection` and `DetectionCorrection` tables
* `classification.py` covers both `SpeciesClassification` and `ClassificationCorrection` tables
* `analysis_result.py` contains the CRUD operations for the `DailyAnalysisResult` table. Data in this table can be used to generate reports for other intervals, e.g. weekly, monthly, or yearly.

Methods implemented in the CRUD classes are summarized in the following table:

* ✓: implemented
* x: not allowed to use directly (raise NotImplementedError)
* -: inherited from `CRUDBase` and not overridden in the specialized CRUD class

| Class | add | select | get | filter | update | delete | other methods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CRUDBase | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| CameraCRUD | ✓ | - | - | - | ✓ | - |  |
| CameraLocationHistoryCRUD | x | - | - | - | x | x | `add_location_change`,<br> `get_by_camera`,<br> `update_valid_to_most_recent_history`,<br> `delete_old_camera_history` |
| ImageCRUD | ✓ | - | - | - | x | - | `get_images_to_delete`,<br> `get_images_in_period`,<br> `mark_image_for_deletion` |
| MLModelCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| ObjectDetectionCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| TaxonomyCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| SpeciesClassificationCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| AppUserCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| DetectionCorrectionCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| ClassificationCorrectionCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| DailyAnalysisResultCRUD | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |


