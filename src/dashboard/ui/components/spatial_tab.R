# Trigger rendering of the sidebar, heatmap legend and heatmap output itself
# The inspector panel is hidden unless a Camera has been selected (to display data)
spatial_tab <- function() {
  bslib::nav_panel(
    "Camera Rings", value = "spatial", icon = sentinel_icon("map"),
    bslib::layout_sidebar(
      sidebar = sentinel_sidebar(),
      padding = 0, gap = 0, border = FALSE, border_radius = FALSE,
      div(
        class = "map-stage bslib-fill-item",
        map_toolbar(),
        div(class = "map-legend-overlay", uiOutput("heatmap_legend")),
        leafletOutput("heatmap_map", height = "100%"),
        uiOutput("heatmap_map_error"),
        map_timeline()
      )
    ),
    uiOutput("inspector_panel")
  )
}
