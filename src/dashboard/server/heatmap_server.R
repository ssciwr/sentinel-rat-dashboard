# Display hbeatmap controlers and render the heatmap
register_heatmap_server <- function(input, output, session, state) {
  map_update_error <- reactiveVal(FALSE)

  record_heatmap_error <- function(error) {
    map_update_error(TRUE)
    message("Heatmap update failed in ", deparse(conditionCall(error)), ": ", conditionMessage(error))
  }

  current_heatmap_filter_settings <- reactive({
    heatmap_filter_settings(
      selected_heatmap_metric(input$heatmap_metric),
      isTRUE(input$show_all_filters),
      input$predator_threshold,
      input$rodent_threshold,
      input$total_threshold,
      identical(input$predator_threshold_below, "below"),
      identical(input$rodent_threshold_below, "below"),
      identical(input$total_threshold_below, "below")
    )
  })

 # when show heatmap is true (on the heatmap view not KPI view etc), react to the users inputs changing amongst other places in current_heatmap_filter_settings
  heatmap_view_state <- reactive({
    tryCatch({
      metric <- selected_heatmap_metric(input$heatmap_metric)
      list(
        metric = metric,
        display_grid = map_snapshot(input$time_slider, metric, current_heatmap_filter_settings(), state$camera_day_logs()),
        show_cells = !isFALSE(input$show_heatmap_cells)
      )
    }, error = function(error) {
      record_heatmap_error(error)
      NULL
    })
  })

 # Draw actual heatmap shape objects
  observeEvent(list(heatmap_view_state(), input$heatmap_map_client_ready, input$retry_heatmap), {
    req(input$heatmap_map_client_ready)
    tryCatch({
      view <- heatmap_view_state()
      if (is.null(view)) {
        return()
      }
      session$sendCustomMessage("heatmap-view", heatmap_view_payload(view))
      message("Heatmap view sent for ", nrow(view$display_grid), " cameras.")
      map_update_error(FALSE)
    }, error = record_heatmap_error)
  }, ignoreInit = TRUE)

# Manage currently selected camera by it's ID
  observeEvent(input$heatmap_map_shape_click, {
    camera_name <- input$heatmap_map_shape_click$id
    if (!is.null(camera_name)) {
      state$selected_camera_name(camera_name)
      state$selected_image_index(1)
    }
  })

  observeEvent(input$heatmap_map_render_status, {
    render_succeeded <- isTRUE(input$heatmap_map_render_status$ok)
    map_update_error(!render_succeeded)
    if (!render_succeeded) {
      message("Heatmap browser layer failed.")
    }
  })

  observeEvent(input$time_slider, {
    selected_day <- selected_map_day(input$time_slider)
    updateSelectInput(session, "time_year", selected = format(selected_day, "%Y"))
    updateSelectInput(session, "time_month", selected = format(selected_day, "%m"))
    state$selected_image_index(1)
  })

  observeEvent(list(input$time_year, input$time_month), {
    req(input$time_year, input$time_month)
    month_days <- map_days[
      format(map_days, "%Y") == input$time_year &
        format(map_days, "%m") == input$time_month
    ]
    if (length(month_days) == 0) {
      return()
    }
    updateSliderInput(
      session,
      "time_slider",
      min = min(month_days),
      max = max(month_days),
      value = if (selected_map_day(input$time_slider) %in% month_days) selected_map_day(input$time_slider) else min(month_days)
    )
  }, ignoreInit = TRUE)

  observeEvent(input$predator_species_info, {
    showModal(modalDialog(
      title = "Predator species",
      tags$ul(
        class = "predator-species-list",
        # AI-Generated
        # List every predator species represented in the analysis.
        lapply(predator_species_labels, function(species) tags$li(tags$em(species)))
      ),
      footer = modalButton("Done"),
      easyClose = TRUE,
      size = "s"
    ))
  })

  observeEvent(input$heatmap_zoom_request, {
    direction <- input$heatmap_zoom_request$direction
    if (is.null(direction)) {
      return()
    }
    zoom <- input$heatmap_map_zoom
    center <- input$heatmap_map_center
    if (is.null(zoom)) {
      zoom <- map_initial_view$zoom
    }
    if (is.null(center)) {
      center <- map_initial_view
    }
    leafletProxy("heatmap_map") %>%
      setView(
        lng = center$lng,
        lat = center$lat,
        zoom = min(map_initial_view$max_zoom, max(map_initial_view$min_zoom, zoom + direction))
      )
  })

  observeEvent(input$toggle_map_filters, {
    bslib::toggle_sidebar("spatial_filters")
  })

  observeEvent(input$heatmap_focus_location, {
    tryCatch({
      destination <- map_location_switch(input$heatmap_map_center)$destination
      leafletProxy("heatmap_map") %>%
        setView(lng = destination$lng, lat = destination$lat, zoom = destination$zoom)
    }, error = record_heatmap_error)
  })

  output$map_location_control <- renderUI({
    location <- map_location_switch(input$heatmap_map_center)
    map_icon_button(
      "map-location-button",
      paste("View", location$destination$label),
      sentinel_icon("arrow-left-right"),
      "if (window.Shiny) { Shiny.setInputValue('heatmap_focus_location', Date.now(), { priority: 'event' }); }",
      label = location$destination$label
    )
  })

  output$heatmap_map <- renderLeaflet({
    tryCatch({
      view <- isolate(heatmap_view_state())
      if (is.null(view)) {
        stop("No heatmap data is available.")
      }
      map_update_error(FALSE)
      heatmap_base_map(view$display_grid)
    }, error = function(error) {
      record_heatmap_error(error)
      satellite_map(data.frame())
    })
  })

  output$heatmap_legend <- renderUI({
    tryCatch({
      view <- heatmap_view_state()
      if (is.null(view)) {
        return(NULL)
      }
      heatmap_legend_ui(view$metric, view$display_grid)
    }, error = function(error) {
      record_heatmap_error(error)
      NULL
    })
  })

  output$heatmap_map_error <- renderUI({
    if (!isTRUE(map_update_error())) {
      return(NULL)
    }
    div(
      class = "heatmap-map-error",
      role = "alert",
      div(
        class = "heatmap-map-error-copy",
        tags$strong("Map couldn't update"),
        tags$span("Try again. Your selected controls are unchanged.")
      ),
      actionButton("retry_heatmap", "Try again", class = "heatmap-map-retry")
    )
  })
}
