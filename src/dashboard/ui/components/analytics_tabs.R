
kpi_console_tab <- function() {
  bslib::nav_panel("KPI Console", value = "kpi_alt", icon = sentinel_icon("bar-chart"),
    div(class = "kpi-console",
      fluidRow(
        column(4, div(class = "metric-card", div(class = "metric-card-title", "Rodent abundance"), div(class = "metric-card-note", "Daily detections"), plotlyOutput("ratSpark", height = "160px"))),
        column(4, div(class = "metric-card", div(class = "metric-card-title", "Non-target activity"), div(class = "metric-card-note", "Daily detections"), plotlyOutput("otherSpark", height = "160px"))),
        column(4, div(class = "metric-card", div(class = "metric-card-title", "Predator pressure"), div(class = "metric-card-note", "Daily percentage"), plotlyOutput("predSpark", height = "160px")))
      ),
      div(class = "metric-card", div(class = "metric-card-title", "Normalised activity console"), div(class = "metric-card-note", "Mouse wheel zooms time; drag pans left and right."), plotlyOutput("kpiConsolePlot", height = "390px"))
    )
  )
}
