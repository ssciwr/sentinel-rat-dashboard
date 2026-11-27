# Shiny UI composition entrypoint.
source("ui/components/icons.R", local = TRUE)
source("ui/components/head_assets.R", local = TRUE)
source("ui/components/sidebar.R", local = TRUE)
source("ui/components/map_controls.R", local = TRUE)
source("ui/components/spatial_tab.R", local = TRUE)
source("ui/components/analytics_tabs.R", local = TRUE)
source("ui/settings.R", local = TRUE)

ui <- bslib::page_navbar(
  title = "SENTINEL-RAT V12",
  id = "tabs",
  selected = "spatial",
  theme = bslib::bs_theme(
    version = 5,
    bg = "#f3f6f1",
    fg = "#10251f",
    primary = "#c79535",
    "border-radius" = "0.75rem"
  ),
  bg = "#10251f",
  inverse = TRUE,
  fillable = "spatial",
  fillable_mobile = TRUE,
  gap = 0,
  padding = 0,
  header = tags$head(sentinel_head_assets()),
  spatial_tab(),
  bslib::nav_panel(
    "Correlation & Dynamics", value = "analytics", icon = sentinel_icon("activity"),
    div(class = "p-3", plotOutput("correlationPlot"))
  ),
  kpi_console_tab(),
  bslib::nav_spacer(),
  settings_ui(),
  bslib::nav_item(actionButton(
    "start-dashboard-tour", "Tour", icon = sentinel_icon("info-circle"), class = "btn-outline-light btn-sm"
  )),
  footer = htmlTemplate(
    filename = "ui/templates/annotation_modal.html",
    previous_icon = sentinel_icon("chevron-left"),
    next_icon = sentinel_icon("chevron-right"),
    close_icon = sentinel_icon("x-lg"),
    species_options = lapply(valid_detection_labels, function(species) tags$option(value = species, species))
  )
)
