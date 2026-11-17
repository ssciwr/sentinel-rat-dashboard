# This is just a preliminary test to see if reticulate can import the dashboard.db module and call its functions from R
# Please refactor later

library(reticulate)

# configure reticulate to use the appropriate Python interpreter
configure_reticulate_python <- function() {
  python_bin <- Sys.getenv("RETICULATE_PYTHON", unset = "")
  if (!nzchar(python_bin)) {
    python_bin <- Sys.which("python3")
  }
  if (!nzchar(python_bin)) {
    python_bin <- Sys.which("python")
  }
  if (!nzchar(python_bin)) {
    stop("Could not find a Python interpreter for reticulate.", call. = FALSE)
  }

  reticulate::use_python(python_bin, required = TRUE)
}


# add the src directory to the Python path so that reticulate can find the dashboard.db module
add_src_to_python_path <- function() {
  source_file <- tryCatch(sys.frame(1)$ofile, error = function(e) NULL)
  if (is.null(source_file)) {
    return(invisible(NULL))
  }

  script_dir <- dirname(normalizePath(source_file, winslash = "/"))
  src_dir <- normalizePath(file.path(script_dir, "..", ".."), winslash = "/")

  if (dir.exists(src_dir)) {
    sys <- reticulate::import("sys")
    if (!src_dir %in% sys$path) {
      sys$path <- c(src_dir, sys$path)
    }
  }
}

configure_reticulate_python()
add_src_to_python_path()

db_module <- reticulate::import("dashboard.db")
db_database_module <- reticulate::import("dashboard.db.database")

detection_crud <- db_module$detection_crud
camera_crud <- db_module$camera_crud
daily_analysis_result_crud <- db_module$daily_analysis_result_crud
taxonomy_crud <- db_module$taxonomy_crud
app_user_crud <- db_module$app_user_crud

create_db_session <- function() {
  db_database_module$SessionLocal()
}

db_session <- create_db_session()

# label for taxonomy.is_predator; NULL/NA means nobody assessed the species yet
predator_label <- function(is_predator) {
  if (is.null(is_predator) || is.na(is_predator)) {
    return("not assessed")
  }
  if (isTRUE(is_predator)) "predator" else "prey"
}

# common name if known, otherwise the scientific name
species_label <- function(genus, species = NULL, common_name = NULL) {
  if (!is.null(common_name) && nzchar(common_name)) {
    return(common_name)
  }
  if (is.null(species) || !nzchar(species)) {
    return(genus)
  }
  # species may hold the epithet ("rattus") or the full binomial ("Rattus rattus")
  if (startsWith(species, paste0(genus, " "))) species else paste(genus, species)
}

detection_to_row <- function(detection) {
  bbox <- reticulate::py_to_r(detection$bbox)
  bbox_text <- if (is.null(bbox)) {
    NA_character_
  } else if (is.list(bbox)) {
    if (is.null(names(bbox))) {
      paste(unlist(bbox), collapse = ", ")
    } else {
      paste(paste(names(bbox), unlist(bbox), sep = ": "), collapse = ", ")
    }
  } else {
    as.character(bbox)
  }

  # species and predator/prey role come from the most confident classification;
  # detections without classification (e.g. not an animal) have none
  top <- detection_crud$top_classification(detection)
  if (is.null(top)) {
    species_text <- NA_character_
    species_confidence <- NA_real_
    role <- NA_character_
  } else {
    taxonomy <- top$taxonomy
    species_text <- species_label(
      taxonomy$genus, taxonomy$species, taxonomy$common_name
    )
    species_confidence <- as.numeric(top$confidence)
    role <- predator_label(taxonomy$is_predator)
  }

  data.frame(
    id = as.integer(detection$id),
    image_capture_id = as.integer(detection$image_capture_id),
    det_model_id = as.integer(detection$det_model_id),
    created_at = as.character(reticulate::py_to_r(detection$created_at)),
    confidence = as.numeric(detection$confidence),
    bbox = bbox_text,
    detected_class = as.character(detection$detected_class),
    species = species_text,
    species_confidence = species_confidence,
    role = role,
    stringsAsFactors = FALSE
  )
}

fetch_detections <- function(session = db_session) {
  detections <- detection_crud$select(session)

  if (length(detections) == 0) {
    return(data.frame())
  }

  do.call(rbind, lapply(detections, detection_to_row))
}

# Convert a daily analysis result into one R data-frame row.
# Tuyen please feel totally free to overwrite this when relevant
daily_analysis_result_to_row <- function(daily_analysis_result) {
  data.frame(
    id = as.integer(daily_analysis_result$id),
    camera_id = as.integer(daily_analysis_result$camera_id),
    start_time = reticulate::py_to_r(daily_analysis_result$start_time),
    end_time = reticulate::py_to_r(daily_analysis_result$end_time),
    taxonomy_id = as.integer(daily_analysis_result$taxonomy_id),
    taxonomy_count = as.integer(daily_analysis_result$taxonomy_count),
    avg_confidence = as.numeric(daily_analysis_result$avg_confidence),
    stringsAsFactors = FALSE
  )
}

# Retrieve daily analysis results newest first through the Python CRUD helper. Can/should be overwritten later by final implementation
# generic catch all which can hopefully stay as is in R using `daily_analysis_result_to_row` which can be overwritten to the final Python database functions implementation
fetch_analyses <- function(session = db_session) {
  analyses <- daily_analysis_result_crud$select(session)

  if (length(analyses) == 0) {
    return(data.frame())
  }

  rows <- do.call(rbind, lapply(analyses, daily_analysis_result_to_row))
  rows[order(rows$start_time, decreasing = TRUE), , drop = FALSE]
}

fetch_cameras <- function(session = db_session) {
  cameras <- camera_crud$select_map_rows(session)

  if (length(cameras) == 0) {
    return(data.frame())
  }

  do.call(rbind, lapply(cameras, function(camera) {
    data.frame(
      camera_id = as.integer(camera$id),
      camera_name = as.character(camera$name),
      lat = as.numeric(camera$latitude),
      lon = as.numeric(camera$longitude),
      status = as.character(camera$status),
      stringsAsFactors = FALSE
    )
  }))
}

fetch_camera_settings <- function() {
  session <- create_db_session()
  on.exit(session$close())
  fetch_cameras(session)
}

# for editing
save_camera_settings <- function(name, latitude, longitude, camera_id = NULL, status = NULL) {
  session <- create_db_session()
  on.exit(session$close())
  camera <- camera_crud$save_coordinates(
    session, name = name, latitude = latitude, longitude = longitude,
    camera_id = camera_id, status = status
  )
  as.integer(camera$id)
}

