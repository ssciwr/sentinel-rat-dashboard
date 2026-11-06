[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/ssciwr/sentinel-rat-dashboard/main.svg)](https://results.pre-commit.ci/latest/github/ssciwr/sentinel-rat-dashboard/main)

# Sentinel Rat Dashboard

Work in progress...

## Overview

R Shiny application for browsing animal detection results from PostgreSQL (PostGIS).

## Scaffolded code

* Initialize a PostgreSQL database with PostGIS extension
* Display results fetched from a database in a table

## Database

### Data Model

There are 11 tables in the database, which are defined in `src/dashboard/db/data_model.py`. The data model is illustrated in the following figure:

![db-model](docs/figures/sentinel-rat-data-model.png)

#### Predator or prey

Whether a detected animal is a predator or prey is a property of its species, stored in `taxonomy.is_predator`: `true` for predators, `false` for prey, and `NULL` while the species has not been assessed (the default for species added by the `sentinel-rat-pipeline`). A detection gets its role through its most confident species classification; the dashboard shows it in the `role` column (`predator`, `prey`, `not assessed`, or empty for detections without a species classification).

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
* `image.py`: `image_path` is the original path in the watch folder and never changes. When an image is moved out of the watch folder, `mark_image_as_moved` can record where it is kept on the server in `stored_path`, so the image can still be displayed.
* `analysis_result.py` contains the CRUD operations for the `DailyAnalysisResult` table. Data in this table can be used to generate reports for other intervals, e.g. weekly, monthly, or yearly.

Methods implemented in the CRUD classes are summarized in the following table:

* ✓ : implemented or overridden in the specialized CRUD class
* x : not allowed to use directly (raise `NotImplementedError`)
* . : inherited from `CRUDBase` and not overridden in the specialized CRUD class

| Class | add | select | get | filter | update | delete | other methods |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CRUDBase | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |  |
| CameraCRUD | ✓ | . | . | . | ✓ | . |  |
| CameraLocationHistoryCRUD | x | . | . | . | x | x | `add_location_change`,<br> `get_by_camera`,<br> `update_valid_to_most_recent_history`,<br> `delete_old_camera_history` |
| ImageCRUD | ✓ | . | . | . | x | . | `get_images_to_move`,<br> `get_images_by_file_status`,<br> `get_images_in_period`,<br> `mark_image_as_analyzed`,<br> `mark_image_as_moved`,<br> `mark_image_as_missing`,<br> `mark_image_as_restored` |
| MLModelCRUD | . | . | . | . | . | . |  |
| ObjectDetectionCRUD | ✓ | . | . | . | x | . |  |
| TaxonomyCRUD | . | . | . | . | . | . |  |
| SpeciesClassificationCRUD | ✓ | . | . | . | x | . |  |
| AppUserCRUD | ✓ | . | . | . | ✓ | . |  |
| DetectionCorrectionCRUD | ✓ | . | . | . | ✓ | ✓ |  |
| ClassificationCorrectionCRUD | ✓ | . | . | . | ✓ | ✓ |  |
| DailyAnalysisResultCRUD | . | . | . | . | . | . | `compute_daily_results`,<br> `pending_days`,<br> `recompute_for_image`,<br> `recompute_all`,<br> `commit_with_recompute` |



### Daily analysis

`daily_analysis_result_crud.compute_daily_results(session, day)` aggregates the images captured on a day (midnight to midnight in `ANALYSIS_TZ`, default `Asia/Colombo`) into one row per camera, detection model and taxonomy. It runs every night from the scheduler in [sentinel-rat-pipeline](https://github.com/ssciwr/sentinel-rat-pipeline). Only new images are used (`analyzed_at` is `NULL`), and late images are merged into the existing rows.

**Counting**

* Each detection counts once, for its most confident classification. A detection without a species is skipped.
* User corrections override model results, and the latest one wins. Removed detections are skipped, and added ones count.
* `avg_confidence` averages the winning classifications; a species set by a user counts as `1.0`.
* Counts of different detection models must not be summed, as the same animal is counted once per model.

**Thresholds**

* `DET_CONF_THRESHOLD` and `CLAS_CONF_THRESHOLD` (`0` to `1`, default `0`, which keeps everything) apply to all models. Results below them are left out, and results at them are kept.
* A species set by a user always counts. A detection confirmed by a user skips the detection threshold, but its classifications must still meet theirs.
* Each row stores the thresholds it used (`det_threshold`, `clas_threshold`). Late images use the thresholds of their camera's rows.

**Recomputing**

* `recompute=True` rebuilds a day from all its images, including moved ones, with the current thresholds.
* To apply new thresholds, call `recompute_all(session, before)`. It rebuilds every camera and day before `before`, and returns the `recomputed` and `skipped` ones.
* A correction of an analyzed image rebuilds its camera and day with the stored thresholds, in the same transaction. If images were deleted, the correction is saved with a warning (see below). If the rebuild fails for any other reason, e.g. an invalid threshold, the correction is not saved either.
* Aggregations of the same day wait for each other (PostgreSQL advisory lock).

**Deleted images**

Deleting an image also deletes its results, so they can't be counted again. Each row stores the number of analyzed images of its camera and day (`image_count`), and a rebuild with fewer images left raises `DeletedImagesError`, which protects the existing counts. On such a camera and day:

* The rows keep their counts and thresholds, and late images are still merged.
* `recompute_all` skips it.
* A correction is saved without updating the rows, and returns a message for the user in `daily_analysis_warning`.

## Development

Currently, we are using:

* Python 3.13
* R 4.4

### Install dependencies

For Python depencencies, run the following command:
```bash
pip install -e .[dev]
```

For R dependencies, make sure you have R and its dependencies installed:
```bash
sudo apt update
sudo apt install r-base
sudo apt-get install -y \
            libpng-dev \
            libpq-dev \
            libssl-dev \
            libuv1-dev \
            libcurl4-openssl-dev \
            libxml2-dev \
            libgit2-dev \
            python3-dev \
            python3-pip
```

Create a folder to install R packages, if needed:
```bash
mkdir -p ~/R/library
export R_LIBS_USER=~/R/library
```

Then, install R packages:
```bash
Rscript install.R
```

### Testing

For Python tests, the PostgreSQL database is handled by `testcontainers`'s `PostgresContainer` as configured in `tests/conftest.py`. To run the tests, use the following command:
```bash
pytest tests/
```

To run R tests, we first need to set up the database. **There might be a simpler way to do this (TBU.)**
```bash
docker run --name sentinel-postgres \
  -e POSTGRES_DB=sentinel_db \
  -e POSTGRES_USER=sentinel_user \
  -e POSTGRES_PASSWORD=sentinel_pass \
  -p 5432:5432 \
  -d postgis/postgis:17-3.5
```

Check if the database is ready:
```bash
docker exec sentinel-postgres pg_isready -U sentinel_user -d sentinel_db
```

You should see the following output (on Linux):
```
/var/run/postgresql:5432 - accepting connections
```

Then set the environment variables for the database connection:
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=sentinel_db
export POSTGRES_USER=sentinel_user
export POSTGRES_PASSWORD=sentinel_pass
```

Initialize the database schema:
```bash
python src/dashboard/init_db.py
```

Finally, run the R tests:
```bash
Rscript -e 'source("src/dashboard/R/db.R"); library(testthat); test_dir("tests/testthat")'
```

Stop and remove the database container when done:
```bash
docker stop sentinel-postgres
docker rm sentinel-postgres
```