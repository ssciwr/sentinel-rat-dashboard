# extracted from frontend/R/heatmap.R
# AI-Generated

# sizes zoomed-in pie markers from daily activity without letting them dominate the map.
detail_marker_size <- function(total_activity, max_activity) {
minimum_fixed_size <- 28
  if (!is.finite(max_activity) || max_activity <= 0) {
    return(rep(minimum_fixed_size, length(total_activity)))
  }
  relative_activity <- pmin(pmax(total_activity / max_activity, 0), 1)
  relative_size <- (sqrt(relative_activity) + relative_activity) / 2 # we append half the square root because area of a circle grows above linear to the radius
  # so if the radius was simply the number of detections, proportionately to the user, a value like 8 (radius 8) would appear as 4x times the size of a circle with half the radius (e.g. 4)
  # increasing either area rather than radius or just radius make differences appear too small / too large between the above example respectively,
  # - so we sum then divide by two the normalized linear + square root scaling(with detections as the base unit)
  # This also prevents very high detection pie charts from totally dominating.
  round(minimum_fixed_size + relative_size * 40)
}

# AI-Generated
# builds isolated HTML pie markers for the zoomed-in detail layer.
detail_pie_labels <- function(detail_grid, max_activity) {
  marker_size <- detail_marker_size(detail_grid$total_activity, max_activity)

  represented_total <- detail_grid$rodent_activity + detail_grid$predator_count
  prey_degrees <- ifelse(represented_total > 0, detail_grid$rodent_activity / represented_total * 360, 0)
  predator_degrees <- ifelse(represented_total > 0, 360, 0)
  marker_class <- ifelse(detail_grid$total_activity > 0, "detail-activity-marker", "detail-activity-marker is-empty")
  title <- htmltools::htmlEscape(paste(detail_grid$camera_name, detail_grid$total_activity_text, detail_grid$prey_label, detail_grid$predator_count_text, sep = " | "))
  sprintf(
    "<span class='%s' data-camera-name='%s' style='--detail-size:%spx; --prey-deg:%.1fdeg; --predator-deg:%.1fdeg;' title='%s'><span class='detail-activity-pie'></span><span class='detail-activity-count'>%s</span></span>",
    marker_class,
    htmltools::htmlEscape(detail_grid$camera_name),
    marker_size,
    prey_degrees,
    predator_degrees,
    title,
    round(detail_grid$total_activity)
  )
}
