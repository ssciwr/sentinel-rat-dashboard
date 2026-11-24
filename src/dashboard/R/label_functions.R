# Manage how labels appear on the map/inspector
predator_pressure_label <- function(pressure) {
  label <- ifelse(pressure > 0, paste0(round(pressure * 100), "%"), "none")
  paste0("Predator pressure: ", label)
}

prey_activity_label <- function(prey_activity) {
  paste0("Prey detections: ", round(prey_activity))
}

predator_count_label <- function(predator_count) {
  paste0("Predator detections: ", round(predator_count))
}

total_activity_label <- function(total_activity) {
  paste0("Total detections: ", round(total_activity))
}

metric_count <- function(label, value, colour) {
  div(
    class = "metric-count",
    div(class = "metric-count-value", style = sprintf("color: %s;", colour), round(value)),
    div(class = "metric-count-label", label),
    div(class = "metric-count-unit", "detections/24H")
  )
}
