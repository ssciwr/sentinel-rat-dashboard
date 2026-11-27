map_focus_locations <- list(
  sri_lanka = utils::modifyList(map_view_from_data(camera_grid), list(label = "Sri Lanka")),
  heidelberg = list(label = "Heidelberg", lat = 49.40768, lng = 8.69079, zoom = 14)
)
# basic utility to move between Sri Lanka and Heidelberg (Heidelberg = hardcoded Zoo coordinates)
# This moves to the location furthest away form the current position (out of the locations hardcoded above)
# Note that this is only used for switching, the initial location is hardcdoded in the map component.

map_location_switch <- function(center, locations = map_focus_locations) {
  if (is.null(center)) {
    center <- locations[[1]]
  }
  latitude <- center$lat * pi / 180
  longitude <- center$lng * pi / 180
  proximity <- vapply(locations, function(location) {
    site_latitude <- location$lat * pi / 180
    sin(latitude) * sin(site_latitude) + cos(latitude) * cos(site_latitude) * cos(longitude - location$lng * pi / 180)
  }, numeric(1))
  list(nearest = locations[[which.max(proximity)]], destination = locations[[which.min(proximity)]])
}
