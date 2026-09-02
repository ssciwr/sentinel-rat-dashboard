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
    stop("Could not find a Python interpreter for reticulate.")
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
  project_root <- normalizePath(file.path(script_dir, "../.."), winslash = "/")
  src_dir <- file.path(project_root, "src")

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

create_db_session <- function() {
  db_database_module$SessionLocal()
}

db_session <- create_db_session()

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

  data.frame(
    id = as.integer(detection$id),
    image_capture_id = as.integer(detection$image_capture_id),
    det_model_id = as.integer(detection$det_model_id),
    created_at = as.character(reticulate::py_to_r(detection$created_at)),
    confidence = as.numeric(detection$confidence),
    bbox = bbox_text,
    detected_class = as.character(detection$detected_class),
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
