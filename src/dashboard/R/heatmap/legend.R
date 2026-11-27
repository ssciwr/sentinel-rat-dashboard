# Use existing heat palettes depending on the metric. Predator pressure shows a slightly different view
heatmap_legend_ui <- function(metric, display_grid = NULL) {
  gradient <- paste(predator_heat_palette[c(1, 26, 51, 76, 101)], collapse = ", ")
  if (metric == "predator") {
    return(div(
      class = "heatmap-legend",
      div(class = "heatmap-legend-title mb-2", "Predator pressure"),
      div(class = "pressure-legend-scale", style = paste0("background: linear-gradient(90deg, ", gradient, ");")),
      div(class = "d-flex justify-content-between small mt-1", lapply(c(0, 25, 50, 75, 100), function(value) span(paste0(value, "%")))),
      div(class = "d-flex align-items-center gap-2 small mt-3", span(class = "heatmap-empty-key"), "No rodent activity"),
      div(class = "small heatmap-legend-note border-top pt-2 mt-2", "predator / (rodent + predator)")
    ))
  } # Early exit return, so the below is only for total activity/rodent activity (which rather than be percentages are just totals/absolute values)

  values <- if (is.null(display_grid) || nrow(display_grid) == 0) {
    numeric()
  } else if (metric == "total") {
    display_grid$total_activity
  } else {
    display_grid$rodent_activity
  }
  values <- values[is.finite(values) & values > 0]
  examples <- if (length(values) > 0) max(values) * c(0, 0.25, 0.5, 0.75, 1) else rep(0, 5)
  title <- if (metric == "total") "Total activity" else "Rodent activity" # key metrics
  div(
    class = "heatmap-legend",
    div(class = "heatmap-legend-title mb-2", title),
    div(class = "pressure-legend-scale", style = paste0("background: linear-gradient(90deg, ", gradient, ");")),
    div(class = "d-flex justify-content-between small mt-1", lapply(seq_along(examples), function(index) span(round(examples[index])))),
    div(class = "small heatmap-legend-note mt-1", "detections"),
    div(class = "d-flex align-items-center gap-2 small mt-3", span(class = "heatmap-empty-key"), "No activity")
  )
}
