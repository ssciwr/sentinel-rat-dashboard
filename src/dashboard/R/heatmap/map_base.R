# Controls the Map base data/display of world background information, background map saturation etc

# This i have found works well to overlay with data but this could easily be modified
satellite_tone <- list(
  wash = 0.22,
  saturation = 0.5,
  contrast = 0.78
)
# Hardcoded to our relevant area of Sri Lanka for this depployment
map_initial_view <- list(
  lng = 81.0015,
  lat = 7.0015,
  zoom = 16, # Keeps the sample data in view - later we might want to automate this to detect automatically/rezoom automatically based on the data (a little tricky because we had the two distant regions) (semitodo)
  min_zoom = 1,
  max_zoom = 18
)
map_wash <- data.frame(lon1 = -180, lat1 = -85, lon2 = 180, lat2 = 85)

add_map_wash <- function(map, opacity = 0.2) {
  map %>%
    addRectangles(
      data = map_wash,
      lng1 = ~lon1,
      lat1 = ~lat1,
      lng2 = ~lon2,
      lat2 = ~lat2,
      fillColor = "#ffffff",
      fillOpacity = tone_value(opacity, 0.2),
      stroke = FALSE,
      group = "satellite_wash",
      options = pathOptions(interactive = FALSE, pane = "satellite_wash")
    )
}


# Center map view on load
map_view_from_data <- function(data) {
  valid_locations <- data[is.finite(data$lon) & is.finite(data$lat), , drop = FALSE]
  if (nrow(valid_locations) == 0) {
    return(map_initial_view)
  }

  utils::modifyList(
    map_initial_view,
    list(lng = valid_locations$lon[[1]], lat = valid_locations$lat[[1]])
  )
}

# This is our base/behind the real
satellite_map <- function(data, wash_opacity = 0.2) {
  initial_view <- map_view_from_data(data)

  leaflet(
    data,
    options = leafletOptions(
      attributionControl = FALSE,
      maxZoom = map_initial_view$max_zoom,
      zoomControl = FALSE
      )
    ) %>%
    addMapPane("satellite_wash", zIndex = 350) %>%
    addProviderTiles(
      providers$Esri.WorldImagery,
      options = providerTileOptions(
        attribution = "",
        maxZoom = map_initial_view$max_zoom,
        maxNativeZoom = map_initial_view$max_zoom
    )
  ) %>%
    add_map_wash(wash_opacity) %>%
    setView(initial_view$lng, initial_view$lat, initial_view$zoom)
}

# Utility
selected_map_day <- function(value) {
  if (is.null(value)) {
    return(min(map_days))
  }
  if (inherits(value, "Date")) {
    return(value)
  }
  if (inherits(value, "POSIXt")) { #POSIX timing...
    return(as.Date(value, tz = "UTC"))
  }
  as.Date(value, origin = "1970-01-01")
}