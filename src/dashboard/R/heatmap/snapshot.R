# Used by heatmap.R this creates our map intensities for each cell value, and uses existing functions to render those into the cell bounds.

# It relies on logical functions like calculate_total_activity to generate the map data from raw data and passes_ratio_filter (this is the threshold settings on the left, controlled by
# `settings` which is just heatmap_filter_settings, a 0-1 boolean for each kind (Rodents, Predator Pressure)

# It returns camera logs (the camera value for each value camera) for the current day `filter(date == current_day) %>%` ready to be rendered via heatmap.R


map_snapshot <- function(value, metric = "rodent", settings = heatmap_filter_settings(metric), camera_logs = camera_day_logs) {
  current_day <- selected_map_day(value)
  metric <- selected_heatmap_metric(metric)
  
  camera_logs %>%
    filter(date == current_day) %>%
    mutate(
      rodent_activity = rat_count,
      total_activity = calculate_total_activity(rodent_activity, predator_count),
      rodent_relative = if (max(rodent_activity) > 0) rodent_activity / max(rodent_activity) else 0,
      relative_activity = if (max(total_activity) > 0) total_activity / max(total_activity) else 0,
      predator_relative = predator_pressure,
      metric_has_activity = if (metric %in% c("rodent", "predator")) {
        rodent_activity > 0
      } else {
        total_activity > 0
      },
      predator_filter_pass = passes_ratio_filter(predator_relative, settings$predator_threshold, settings$predator_direction),
      rodent_filter_pass = passes_ratio_filter(rodent_relative, settings$rodent_threshold, settings$rodent_direction),
      total_filter_pass = passes_ratio_filter(relative_activity, settings$total_threshold, settings$total_direction),
      passes_filter = ifelse(
        metric_has_activity,
        predator_filter_pass & rodent_filter_pass & total_filter_pass,
        settings$predator_threshold <= 0 & settings$rodent_threshold <= 0 & settings$total_threshold <= 0
      ),
      prey_label = prey_activity_label(rodent_activity),
      predator_count_text = predator_count_label(predator_count),
      total_activity_text = total_activity_label(total_activity),
      predator_label = predator_pressure_label(predator_pressure),
      predator_heat_colour = ifelse(metric_has_activity, predator_heat_colour(predator_relative), activity_heat_colour_hex)
    ) %>%
    heatmap_cell_bounds()
}
