# Always use rodent activity as the first default
timeline_xaxis <- function(title) {
  list(
    title = title,
    type = "date",
    range = as.POSIXct(c("2026-09-01", "2026-09-30"), tz = "UTC"),
    fixedrange = FALSE
  )
}

# Used by the KPI plot - we could use a library instead, but those also need the type arguments, the data argument,s the style args etc.
spark_plot <- function(data, value, color) {
  plot_ly(
    data,
    x = ~timestamp,
    y = data[[value]],
    type = "scatter",
    mode = "lines",
    fill = "tozeroy",
    line = list(color = color, width = 2),
    fillcolor = alpha(color, 0.16)
  ) %>%
    layout(
      margin = list(l = 28, r = 12, t = 6, b = 24),
      xaxis = list(type = "date", title = "", showgrid = FALSE),
      yaxis = list(title = "", showgrid = TRUE, zeroline = FALSE),
      showlegend = FALSE
    ) %>%
    config(displayModeBar = FALSE)
}
