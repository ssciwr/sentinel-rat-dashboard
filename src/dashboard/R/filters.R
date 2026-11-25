tone_value <- function(value, default) {
  if (is.null(value) || length(value) == 0 || is.na(value)) {
    return(default)
  }
  as.numeric(value)
}

ratio_threshold <- function(value, default = 0) {
  threshold <- tone_value(value, default)
  threshold <- ifelse(threshold > 1, threshold / 100, threshold)
  pmin(pmax(threshold, 0), 1)
}


# centralize metric and thresholds for map filtering.
selected_heatmap_metric <- function(value) {
  if (!is.null(value) && value %in% c("rodent", "total", "predator")) {
    return(value)
  }
  "rodent" # this is the default returned value (last expression --> gets returned in R)
}

normalise_filter_direction <- function(value) {
  if (!is.null(value) && value %in% c("above", "below")) {
    return(value)
  }
  "above"
}

# compares relative metric values against a percentage-style threshold.
passes_ratio_filter <- function(value, threshold, direction = "above") {
  scaled_value <- pmin(pmax(value, 0), 1)
  scaled_threshold <- ratio_threshold(threshold)
  if (normalise_filter_direction(direction) == "below") {
    return(scaled_value <= scaled_threshold)
  }
  scaled_value >= scaled_threshold
}

# Use filters to show the right data points, but only apply what makes sense (e.g. if advanced all of them, otherwise the
# filter of the current view e.g.  "rodent" only or "total" only.)
heatmap_filter_settings <- function(metric, show_all_filters = FALSE, predator_threshold = 0, rodent_threshold = 0, total_threshold = 0, predator_below = FALSE, rodent_below = FALSE, total_below = FALSE) {
  metric <- selected_heatmap_metric(metric)
  show_all_filters <- isTRUE(show_all_filters)
  applies <- function(filter_metric) {
    show_all_filters || identical(metric, filter_metric)
  }
  threshold_for <- function(filter_metric, value) {
    if (applies(filter_metric)) ratio_threshold(value) else 0
  }
  direction_for <- function(filter_metric, below) {
    if (applies(filter_metric) && isTRUE(below)) "below" else "above"
  }
  list(
    predator_threshold = threshold_for("predator", predator_threshold),
    rodent_threshold = threshold_for("rodent", rodent_threshold),
    total_threshold = threshold_for("total", total_threshold),
    predator_direction = direction_for("predator", predator_below),
    rodent_direction = direction_for("rodent", rodent_below),
    total_direction = direction_for("total", total_below)
  )
}
