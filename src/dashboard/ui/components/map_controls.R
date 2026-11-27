map_toolbar <- function() {
  div(
    class = "heatmap-floating-controls d-flex align-items-center gap-2",
    actionButton("toggle_map_filters", "Filters", icon = sentinel_icon("funnel"), class = "btn-light shadow-sm map-control-button"),
    uiOutput("map_location_control", inline = TRUE)
  )
}

map_zoom_controls <- function() {
  div(
    class = "map-zoom-controls d-flex gap-2",
    map_icon_button(
      "map-zoom-in-button", "Zoom in", sentinel_icon("plus-lg"),
      "if (window.Shiny) { Shiny.setInputValue('heatmap_zoom_request', { direction: 1, nonce: Date.now() }, { priority: 'event' }); }"
    ),
    map_icon_button(
      "map-zoom-out-button", "Zoom out", sentinel_icon("dash-lg"),
      "if (window.Shiny) { Shiny.setInputValue('heatmap_zoom_request', { direction: -1, nonce: Date.now() }, { priority: 'event' }); }"
    )
  )
}

# Timeline plus the Month/Year buttons
map_timeline <- function() {
  initial_day <- min(map_days)
  initial_month_days <- map_days[format(map_days, "%Y-%m") == format(initial_day, "%Y-%m")]
  div(
    class = "global-date-bar",
    map_zoom_controls(),
    div(
      class = "timeline-controls d-flex flex-wrap justify-content-center align-items-center gap-3",
      div(
        class = "heatmap-view-switcher align-items-center",
        span(class = "heatmap-view-label", "Show"),
        div(
          class = "btn-group", role = "group", `aria-label` = "Map data type",
          heatmap_metric_button("rodent", "Rodent activity", TRUE),
          heatmap_metric_button("total", "Total activity"),
          heatmap_metric_button("predator", "Predator pressure")
        )
      ),
      div(
        class = "timeline-date-controls d-flex align-items-center gap-3",
        div(class = "timeline-date-field", tags$label(`for` = "time_month", "Month"), selectInput("time_month", NULL, map_month_choices, format(initial_day, "%m"), width = "100px", selectize = FALSE)),
        div(class = "timeline-date-field", tags$label(`for` = "time_year", "Year"), selectInput("time_year", NULL, map_year_choices, format(initial_day, "%Y"), width = "100px", selectize = FALSE))
      )
    ),
    div(
      class = "global-date-slider",
      sliderInput(
        "time_slider", label = NULL,
        min = min(initial_month_days), max = max(initial_month_days), value = initial_day,
        step = 1, timeFormat = "%d %b", width = "100%"
      )
    )
  )
}
