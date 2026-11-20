# Given several different cell lat/lons, work out the gaps between and if we can make well-adjoining rectangle cells that can fit between them

heatmap_cell_bounds <- function(data) {
  if (nrow(data) == 0) {
    return(data)
  }

  meters_per_degree_lat <- 111320 # this is ok hardcoded like this mostly becausewe project a space around data points (as a square so they can fit nicely adjusted to each other)
  # So we do not prioritise volume/spatial accuracy but rather interpretability from the interface. That's the philsoophy behind this adapting the sizes of different cells
  mean_latitude <- mean(data$lat, na.rm = TRUE)
  mean_lng_meters <- meters_per_degree_lat * cos(mean_latitude * pi / 180)
  x_meters <- data$lon * mean_lng_meters
  y_meters <- data$lat * meters_per_degree_lat

  nearest_distances <- rep(heatmap_fallback_cell_size_m, nrow(data))
  if (nrow(data) > 1) {
    nearest_distances <- vapply(seq_len(nrow(data)), function(index) {
      distances <- sqrt((x_meters - x_meters[index])^2 + (y_meters - y_meters[index])^2)
      positive_distances <- distances[distances > 0]
      if (length(positive_distances) == 0) {
        return(heatmap_fallback_cell_size_m)
      }
      min(positive_distances, na.rm = TRUE)
    }, numeric(1))
  }

  finite_distances <- nearest_distances[is.finite(nearest_distances) & nearest_distances > 0]
  spacing_meters <- if (length(finite_distances) > 0) median(finite_distances) else heatmap_fallback_cell_size_m
  side_meters <- spacing_meters * heatmap_cell_scale

  data %>%
    mutate(
      cell_side_meters = side_meters,
      cell_lat_half = cell_side_meters / 2 / meters_per_degree_lat,
      cell_lng_half = cell_side_meters / 2 / (meters_per_degree_lat * pmax(cos(lat * pi / 180), 0.01)),
      cell_lat1 = lat - cell_lat_half,
      cell_lat2 = lat + cell_lat_half,
      cell_lon1 = lon - cell_lng_half,
      cell_lon2 = lon + cell_lng_half
    )
}

# Cells without data show be dimmed which keeps opacity lower.
heatmap_fill_opacity <- function(value, is_dimmed) {
  scaled <- pmin(pmax(value, 0), 1)
  opacity <- ifelse(scaled > 0, 0.2 + scaled * 0.65, 0.08)
  opacity * ifelse(is_dimmed, 0.35, 1)
}

# remap the colour onto the predator palette (verdis)
predator_heat_colour <- function(value) {
  scaled <- pmin(pmax(value, 0), 1)
  palette_index <- round(scaled * 100) + 1
  predator_heat_palette[palette_index]
}

heatmap_cells_for_metric <- function(display_grid, metric) {
  visible_grid <- display_grid %>% filter(passes_filter)
  relative_column <- switch(metric, rodent = "rodent_relative", total = "relative_activity", "predator_relative")
  empty_relative <- if (metric == "rodent") visible_grid$rodent_relative else visible_grid$relative_activity
  visible_grid %>%
    mutate(
      fill_colour = ifelse(metric_has_activity, predator_heat_colour(.data[[relative_column]]), activity_heat_colour_hex),
      fill_opacity = ifelse(metric_has_activity, 0.65, heatmap_fill_opacity(empty_relative, FALSE)),
      tooltip = switch(
        metric,
        rodent = paste(camera_name, prey_label, sep = " | "),
        total = paste(camera_name, total_activity_text, prey_label, predator_count_text, sep = " | "),
        paste(camera_name, predator_label, prey_label, predator_count_text, sep = " | ")
      )
    )
}
