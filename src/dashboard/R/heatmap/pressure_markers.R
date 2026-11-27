# AI-Generated
# displays actual pressure percentages in the same colours as the map legend.
detail_pressure_labels <- function(detail_grid) {
  if (nrow(detail_grid) == 0) {
    return(character())
  }
  colours <- detail_grid$predator_heat_colour
  brightness <- colSums(grDevices::col2rgb(colours) * c(0.2126, 0.7152, 0.0722))
  text_colours <- ifelse(brightness > 150, "#10251f", "#ffffff")
  labels <- ifelse(detail_grid$metric_has_activity, paste0(round(detail_grid$predator_pressure * 100), "%"), "—")
  titles <- paste(detail_grid$camera_name, labels, detail_grid$prey_label, detail_grid$predator_count_text, sep = " | ")
  sprintf(
    "<span class='detail-pressure-marker%s' data-camera-name='%s' style='background:%s;color:%s;' title='%s'>%s</span>",
    ifelse(detail_grid$metric_has_activity, "", " is-empty"),
    htmltools::htmlEscape(detail_grid$camera_name),
    colours,
    text_colours,
    htmltools::htmlEscape(titles),
    labels
  )
}
