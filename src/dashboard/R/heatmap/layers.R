
# Build lat/lon cell camera layers
heatmap_view_payload <- function(view) {
  if (isFALSE(view$show_cells)) {
    return(list(metric = view$metric, show_cells = FALSE, cameras = list()))
  }

  cameras <- heatmap_cells_for_metric(view$display_grid, view$metric)

  list(
    metric = view$metric,
    show_cells = TRUE,
    cameras = lapply(seq_len(nrow(cameras)), function(index) {
      row <- cameras[index, ]
      list(
        id = as.character(row$camera_name),
        lat1 = as.numeric(row$cell_lat1),
        lon1 = as.numeric(row$cell_lon1),
        lat2 = as.numeric(row$cell_lat2),
        lon2 = as.numeric(row$cell_lon2),
        fill_colour = as.character(row$fill_colour),
        fill_opacity = as.numeric(row$fill_opacity),
        tooltip = as.character(row$tooltip)
      )
    })
  )
}
# init the satellite background base map
heatmap_base_map <- function(display_grid) {
  satellite_map(display_grid, satellite_tone$wash)
}
