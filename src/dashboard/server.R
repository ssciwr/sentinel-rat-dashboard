source("R/auth.R", local = TRUE)
source("ui/settings.R", local = TRUE)
source("server/auth_server.R", local = TRUE)
source("server/heatmap_server.R", local = TRUE)
source("server/annotation_server.R", local = TRUE)
source("server/analytics_server.R", local = TRUE)
source("server/kpi_server.R", local = TRUE)
source("server/settings_server.R", local = TRUE)
source("server/tour_server.R", local = TRUE)

# Routes shared state to feature-focused server modules.
server <- function(input, output, session) {
  auth <- register_auth_server(input, session)
  state <- list(
    selected_camera_name = reactiveVal(NULL),
    selected_image_index = reactiveVal(1),
    camera_day_logs = reactiveVal(camera_day_logs),
    last_correction = reactiveVal(NULL),
    annotation_modal_open = reactiveVal(FALSE),
    annotation_overrides = reactiveVal(list())
  )

  register_heatmap_server(input, output, session, state)
  register_annotation_server(input, output, session, state, auth = auth)
  register_analytics_server(output)
  register_kpi_server(output)
  register_settings_server(input, output, session, auth = auth, state = state)
  register_tour_server(input, session, state)
}
