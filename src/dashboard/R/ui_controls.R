source("ui/components/icons.R", local = TRUE)

heatmap_filter_control <- function(metric, slider_id, label, info_button = NULL) {
  invert_id <- paste0(slider_id, "_below")
  div(
    class = paste("sidebar-map-filter heatmap-filter-panel", paste0("heatmap-filter-", metric)),
    `data-filter-metric` = metric,
    div(class = "sidebar-filter-heading", span(label), info_button),
    sliderInput(slider_id, NULL, min = 0, max = 100, value = 0, step = 5, post = "%"),
    div(
      class = "filter-invert-control",
      radioButtons(invert_id, label = NULL, choices = c("Threshold above" = "above", "Threshold below" = "below"), selected = "above")
    )
  )
}

heatmap_metric_button <- function(metric, label, active = FALSE) {
  tags$button(
    type = "button",
    class = paste("btn btn-sm heatmap-view-button", if (active) "is-active" else ""),
    `data-heatmap-metric` = metric,
    `aria-pressed` = if (active) "true" else "false",
    label
  )
}

map_icon_button <- function(class_name, title, icon_tag, onclick, label = NULL) {
  tags$button(
    type = "button",
    class = paste("btn btn-light shadow-sm map-control-button", class_name),
    title = title,
    `aria-label` = title,
    onclick = onclick,
    icon_tag,
    label
  )
}
