
# Build lat/lon cell camera layers
heatmap_view_payload <- function(view) {
  if (isFALSE(view$show_cells)) {
    return(list(metric = view$metric, show_cells = FALSE, cameras = list()))
  }

  cameras <- heatmap_cells_for_metric(view$display_grid, view$metric)
  max_activity <- if (nrow(view$display_grid) == 0) 0 else max(view$display_grid$total_activity, na.rm = TRUE)
  detail_html <- if (view$metric == "predator") {
    detail_pressure_labels(cameras)
  } else {
    detail_pie_labels(cameras, max_activity)
  }

  list(
    metric = view$metric,
    show_cells = TRUE,
    cameras = lapply(seq_len(nrow(cameras)), function(index) {
      row <- cameras[index, ]
      list(
        id = as.character(row$camera_name),
        lat = as.numeric(row$lat),
        lon = as.numeric(row$lon),
        lat1 = as.numeric(row$cell_lat1),
        lon1 = as.numeric(row$cell_lon1),
        lat2 = as.numeric(row$cell_lat2),
        lon2 = as.numeric(row$cell_lon2),
        fill_colour = as.character(row$fill_colour),
        fill_opacity = as.numeric(row$fill_opacity),
        has_activity = isTRUE(row$metric_has_activity),
        tooltip = as.character(row$tooltip),
        detail_html = as.character(detail_html[index])
      )
    })
  )
}
# init the satellite background base map
heatmap_base_map <- function(display_grid) {
  satellite_map(display_grid, satellite_tone$wash)
}
