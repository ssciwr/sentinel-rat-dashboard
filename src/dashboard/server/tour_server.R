# This is mostly AI generated in a refactor from the original intro.js implementation (using an R module reduces code (and especially JS code))
# The tour server basically keeps track of where the user is in a "tour" and moves them through our prescribed order of steps. It manages cancelling to deal with removing the tour.
# The step text content, flow, and actions are manually written.
register_tour_server <- function(input, session, state) {
  back_button <- list(action = "back", text = "Back", secondary = TRUE)
  tour <- conductor::Conductor$new(progress = TRUE, defaultStepOptions = list(
    classes = "sentinel-tour", scrollTo = FALSE,
    cancelIcon = list(enabled = TRUE, label = "Close tour"),
    buttons = list(back_button, list(action = "next", text = "Next"))
  ))$
    step(id = "mode", el = ".heatmap-view-switcher", title = "Map Mode", position = "top",
      text = "View rodent activity, predator pressure where rodents are present, or total activity.",
      buttons = list(list(action = "next", text = "Next")))$
    step(id = "colour", el = ".map-legend-overlay", title = "Map colour", position = "right",
      text = "Colour represents activity or predator pressure. For detection counts, click individual cells.")$
    step(id = "camera", el = "#heatmap_map", title = "Camera Trap data", position = "top",
      text = "Click a camera to see its detection counts and continue. A high predator pressure can come from many detections or just a few. If no cameras are visible, close the tour and adjust the map or filters.",
      buttons = list(back_button))$
    step(id = "inspector", el = ".inspector-panel", title = "Inspect detections", position = "left",
      text = "Review machine learning detections using the robot button or image. Move a box, add a detection, or correct its species. Use the pencil beside the name to edit the camera.",
      buttons = list(back_button, list(action = "next", text = "Done")))

  observeEvent(input[["start-dashboard-tour"]], {
    if (isTRUE(tour$isActive())) return()
    state$selected_camera_name(NULL)
    updateNavbarPage(session, "tabs", selected = "spatial")
    session$onFlushed(function() tour$init(session)$start(session), once = TRUE)
  })

  observeEvent(tour$getCurrentStep(), {
    if (identical(tour$getCurrentStep(), "camera")) state$selected_camera_name(NULL)
  })

  observeEvent(state$selected_camera_name(), {
    req(isTRUE(tour$isActive()))
    if (is.null(state$selected_camera_name())) {
      if (identical(tour$getCurrentStep(), "inspector")) tour$show("camera")
      return()
    }
    if (!identical(tour$getCurrentStep(), "camera")) return()
    # AI-Generated
    # Highlight the camera view after Shiny has rendered it.
    session$onFlushed(function() tour$show("inspector", session), once = TRUE)
  }, ignoreNULL = FALSE)

  observeEvent(input$open_annotation, {
    if (isTRUE(tour$isActive())) tour$complete()
  })
}
