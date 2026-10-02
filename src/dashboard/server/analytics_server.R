# registers analytics plots independent from map and annotation state.
register_analytics_server <- function(output) {
  output$correlationPlot <- renderPlot({
    ggplot(activity_logs, aes(x = timestamp)) +
      geom_line(aes(y = ai_activity, color = "AI Detection Intensity Index"), linewidth = 1) +
      geom_point(data = filter(activity_logs, trap_catch > 0),
                 aes(y = 0, color = "Trap Catches"), size = 4, shape = 17) +
      scale_color_manual(values = c("AI Detection Intensity Index" = "#5f8f6a", "Trap Catches" = "red")) +
      labs(title = "AI Activity vs. Manual Trap Catch", y = "AI Intensity Index", x = "Time") +
      theme_minimal()
  })

  output$ratPlot <- renderPlotly({
    plot_daily_metric(activity_logs, "rat_count", "Rodent abundance", "#dd4b39", "Rodent detections")
  })

  output$otherPlot <- renderPlotly({
    plot_daily_metric(activity_logs, "other_count", "Non-target activity", "#d8c56f", "Non-target detections")
  })

  output$predPlot <- renderPlotly({
    plot_daily_metric(activity_logs, "predator_pressure_pct", "Predator pressure", predator_colour_hex, "Predator share (%)", c(0, 100))
  })

  output$combinedPlot <- renderPlotly({
    plot_ly(activity_logs, x = ~timestamp) %>%
      add_lines(y = ~rat_count, name = "Rodent abundance", line = list(color = "#dd4b39")) %>%
      add_lines(y = ~other_count, name = "Non-target activity", line = list(color = "#d8c56f")) %>%
      add_lines(y = ~predator_pressure_pct, name = "Predator pressure", yaxis = "y2", line = list(color = predator_colour_hex)) %>%
      layout(
        dragmode = "pan",
        xaxis = timeline_xaxis("Time"),
        yaxis = list(title = "Detections"),
        yaxis2 = list(title = "Predator share (%)", overlaying = "y", side = "right", range = c(0, 100)),
        legend = list(orientation = "h", x = 0, y = 1.12)
      ) %>%
      config(scrollZoom = TRUE, displayModeBar = TRUE)
  })
}
