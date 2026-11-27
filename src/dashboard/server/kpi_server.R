# Manage KPI data (currently faux fake data)
register_kpi_server <- function(output) {
  output$ratSpark <- renderPlotly({
    spark_plot(activity_logs, "rat_count", "#ffe254")
  })

  output$otherSpark <- renderPlotly({
    spark_plot(activity_logs, "other_count", "#386a48")
  })

  output$predSpark <- renderPlotly({
    spark_plot(activity_logs, "predator_pressure_pct", predator_colour_hex)
  })

  output$kpiConsolePlot <- renderPlotly({
    plot_ly(kpi_console_data, x = ~timestamp) %>%
      add_lines(y = ~rodent_index, name = "Rodent abundance", line = list(color = "#ffe254", width = 2)) %>%
      add_lines(y = ~non_target_index, name = "Non-target activity", line = list(color = "#386a48", width = 2)) %>%
      add_lines(y = ~predator_index, name = "Predator pressure", line = list(color = predator_colour_hex, width = 2)) %>%
      layout(
        dragmode = "pan",
        margin = list(l = 48, r = 24, t = 10, b = 40),
        xaxis = timeline_xaxis("Time"),
        yaxis = list(title = "Normalised score", range = c(0, 100)),
        legend = list(orientation = "h", x = 0, y = 1.12)
      ) %>%
      config(scrollZoom = TRUE, displayModeBar = TRUE)
  })
}
