
calculate_predator_pressure <- function(rat_count, predator_count) {
  ifelse(rat_count > 0, predator_count / (rat_count + predator_count), 0)
}

calculate_total_activity <- function(rat_count, predator_count) {
  rat_count + predator_count
}

# Rescale data to relative activity over time to see it on the same graph (axis independent)
calculate_kpi_console_data <- function(activity_logs) {
  activity_logs %>%
    mutate(
      rodent_index = rescale(rat_count, to = c(0, 100)),
      non_target_index = rescale(other_count, to = c(0, 100)),
      predator_index = predator_pressure_pct
    )
}

label_genus <- function(label) {
  sub(" .*", "", label)
}

