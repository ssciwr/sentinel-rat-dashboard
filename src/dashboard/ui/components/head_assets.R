# These just manage the look and feel appearance, mainly they do what <head> in a html document would/does

sentinel_theme_vars <- function() {
  tags$style(HTML(sprintf(
    ":root { --sat-saturation: %s; --sat-contrast: %s; --prey-colour: %s; --rodent-heat: %s; --predator-colour: %s; --predator-heat-low: %s; --predator-heat-mid: %s; --predator-heat-high: %s; }",
    satellite_tone$saturation,
    satellite_tone$contrast,
    prey_activity_colour_hex,
    rodent_heat_colour_hex,
    predator_colour_hex,
    predator_heat_low_hex,
    predator_heat_mid_hex,
    predator_heat_high_hex
  )))
}

heatmap_controls_asset_version <- function(filename = "www/scripts/heatmap-controls.js") {
  modification_time <- file.info(filename)$mtime
  if (is.na(modification_time)) {
    return("1")
  }
  as.character(as.integer(as.numeric(modification_time)))
}

sentinel_head_assets <- function() {
  tagList(
    tags$link(rel = "stylesheet", href = "https://cdn.jsdelivr.net/npm/@annotorious/annotorious@3.8.10/dist/annotorious.css"),
    tags$script(src = "https://cdn.jsdelivr.net/npm/@annotorious/annotorious@3.8.10/dist/annotorious.js"),
    conductor::useConductor(),
    sentinel_theme_vars(),
    includeCSS("ui/styles/general.css"),
    includeCSS("ui/styles/sidebar.css"),
    includeCSS("ui/styles/leaflet_map.css"),
    includeCSS("ui/styles/timeline.css"),
    includeCSS("ui/styles/heatmap_layers.css"),
    includeCSS("ui/styles/camera_inspector.css"),
    includeCSS("ui/styles/kpi.css"),
    includeCSS("ui/styles/annotation.css"),
    includeCSS("ui/styles/responsive.css"),
    tags$script(src = paste0("scripts/shiny-inputs.js?v=", heatmap_controls_asset_version("www/scripts/shiny-inputs.js"))),
    tags$script(src = paste0("scripts/heatmap-controls.js?v=", heatmap_controls_asset_version())),
    tags$script(src = paste0("scripts/annotation-modal.js?v=", heatmap_controls_asset_version("www/scripts/annotation-modal.js")))
  )
}
