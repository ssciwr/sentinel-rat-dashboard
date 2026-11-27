# extracted from Trap_Dash_v12.R
library(shiny)
library(leaflet)
library(ggplot2)
library(dplyr)
library(plotly)
library(scales)

source("R/metrics.R", local = TRUE)
source("R/analysis.R", local = TRUE)
source("R/annotation_db.R", local = TRUE)
source("R/db.R", local = TRUE)

# --- DATA SETUP ---
analysis_rows <- select_analysis_model(analysis_rows_with_species())
if (is.null(analysis_rows) || nrow(analysis_rows) == 0) {
  stop("No daily analysis results are available. Run daily analysis before starting the dashboard.", call. = FALSE)
}
species_roles <- unique(analysis_rows[c("species_label", "role")])
names(species_roles) <- c("species", "role")
map_days <- sort(unique(as.Date(analysis_rows$start_time, tz = analysis_timezone)))
dashboard_days <- map_days
camera_grid <- fetch_cameras()
camera_day_logs <- camera_activity_logs(map_days, analysis_rows, camera_grid)
activity_logs <- daily_activity_logs(dashboard_days, analysis_rows)

map_month_choices <- setNames(
  unique(format(map_days, "%m")),
  unique(format(map_days, "%b"))
)
map_year_choices <- unique(format(map_days, "%Y"))

kpi_console_data <- calculate_kpi_console_data(activity_logs)

predator_species_labels <- species_roles$species[species_roles$role == "predator"]
valid_detection_labels <- fetch_annotation_species()

# CSS / Visual elments for the heatmap.
heatmap_cell_scale <- 1.02
heatmap_fallback_cell_size_m <- 50
prey_activity_colour_hex <- "#ffe254"
activity_heat_colour_hex <- "#ffffff"
rodent_heat_colour_hex <- "#245c78"
predator_colour_hex <- "#1f5f3a"
predator_heat_palette <- rev(scales::viridis_pal(option = "C", begin = 0.08, end = 0.88)(101))
predator_heat_low_hex <- predator_heat_palette[1]
predator_heat_mid_hex <- predator_heat_palette[51]
predator_heat_high_hex <- predator_heat_palette[101]
