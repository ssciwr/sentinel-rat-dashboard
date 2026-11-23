# Support the user filtering displayed data points across the three possible metrics (e.g. Rodent Activity, Predator Pressure)
# These filters can include only those above, or respectively below, a given threshold, and they can be stacked together too.
sentinel_sidebar <- function() {
  bslib::sidebar(
    id = "spatial_filters",
    title = "Map filters",
    width = 240,
    open = "closed",
    bg = "#0d1d19",
    fg = "#f7efe2",
      div(
        class = "sidebar-map-controls",
        conditionalPanel(
          "input.show_all_filters || !input.heatmap_metric || input.heatmap_metric === 'rodent'",
          heatmap_filter_control("rodent", "rodent_threshold", "Rodent activity threshold")
        ),
        conditionalPanel(
          "input.show_all_filters || input.heatmap_metric === 'total'",
          heatmap_filter_control("total", "total_threshold", "Total activity threshold")
        ),
        conditionalPanel(
          "input.show_all_filters || input.heatmap_metric === 'predator'",
          heatmap_filter_control(
            "predator",
            "predator_threshold",
            "Predator pressure threshold",
            actionButton(
              "predator_species_info",
              label = NULL,
              icon = sentinel_icon("info-circle"),
              class = "btn-sm predator-info-button",
              title = "Predator species"
            )
          )
        ),
        div(class = "d-none", checkboxInput("show_all_filters", NULL, FALSE)),
        actionButton("toggle_all_filters", "Show all filters", class = "btn-outline-light btn-sm w-100 mt-3", `aria-expanded` = "false")
      )
  )
}
