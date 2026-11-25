# Set up the annotation server/DB connection (this is seperate from db.R / server.R to modularize, as this functionality,
# besides the date and the camera ID, is not spatial and separate to the heatmap data, legends, heatmap color, UI selectors like thresholds, and KPI information)
# This should keep this code self-contained and easier to review/modify (e.g. with AI)


# Note: This is very complex and mixes communicating with the Annotorious JS / annotorious UI in the second half with DB functions (top half/reticulate)
# I would try and simplify this further, it is tricky to achieve the interactive data functionality of drawing bboxes, holding draft client side data and loading/updating the DB.
# The second half might be worth further simplification. There could be R modules that can handle it, none seemed that obvious so far. I already removed one previous overcomplicated approach that AI suggested by default.


register_annotation_server <- function(input, output, session, state, auth = NULL, save_correction = save_detection_annotation) {
  annotation_targets <- new.env(parent = emptyenv())
	selected_camera_record <- reactive({
    req(state$selected_camera_name())
    map_snapshot(input$time_slider, camera_logs = state$camera_day_logs()) %>%
      filter(camera_name == state$selected_camera_name()) %>%
      slice(1)
  })

  selected_camera_day <- reactive({
    camera <- selected_camera_record()
    req(nrow(camera) == 1)
    tryCatch(
      fetch_annotation_data(camera$camera_id, selected_map_day(input$time_slider)),
      error = function(error) {
        message("Camera images could not be loaded: ", conditionMessage(error))
        validate(need(FALSE, "Camera images could not be loaded. Please reopen the inspector."))
      }
    )
  })

  selected_camera_images <- reactive(selected_camera_day()$images)

# Render camera image with it's annotation bboxes and labelled classes on the frontend
  send_annotation_editor_frame <- function(open = TRUE) {
    images <- selected_camera_images()
    if (nrow(images) == 0) {
      return()
    }
    index <- min(max(state$selected_image_index(), 1), nrow(images))
    state$selected_image_index(index)
    image_id <- images$image_id[index]
    annotations <- tryCatch(fetch_saved_image_annotations(image_id), error = function(error) {
      message("Saved annotations could not be loaded: ", conditionMessage(error))
      NULL
    })
    if (is.null(annotations)) {
      showNotification("Saved annotations could not be loaded. Please try again.", type = "error")
      return(FALSE)
    }
    frame <- camera_frame_payload(images[index, ], annotations)
    if (is.null(frame$image_url)) {
      showNotification("This camera image is unavailable and cannot be edited.", type = "error")
      return(FALSE)
    }
    annotations_by_image <- state$annotation_overrides()
    annotations_by_image[[image_id]] <- annotations
    state$annotation_overrides(annotations_by_image)
    state$annotation_modal_open(TRUE)
    # Annotorious and a html template plus some light JS code takes care of parsing this, displaying editable bbxoes and letting the suer return updated annotation data
    session$sendCustomMessage(
      "open_annotation_modal",
      list(
        image = frame,
        index = index,
        total = nrow(images),
        open = open
      )
    )
    TRUE
  }

  selected_detection_export <- reactive({
    req(state$selected_camera_name())
    images <- selected_camera_images()
    if (nrow(images) == 0) {
      return(data.frame(detection_time = character(), genus_detected = character()))
    }
    selected_camera_day()$detections %>%
      inner_join(select(images, image_id, timestamp), by = "image_id") %>%
      transmute(
        detection_time = format(timestamp, "%Y-%m-%d %H:%M:%S UTC"),
        genus_detected = genus_detected
      )
  })

  # state$selected_camera_name being null makes the normal map display and this inspector view disappear.
  observeEvent(input$close_inspector, {
    state$selected_camera_name(NULL)
  })

  # Manage pagination as such through out lsit of detections for this camera
  observeEvent(input$prev_camera_image, {
    images <- selected_camera_images()
    req(nrow(images) > 0)
    state$selected_image_index(if (state$selected_image_index() <= 1) nrow(images) else state$selected_image_index() - 1)
  })

  observeEvent(input$next_camera_image, {
    images <- selected_camera_images()
    req(nrow(images) > 0)
    state$selected_image_index(if (state$selected_image_index() >= nrow(images)) 1 else state$selected_image_index() + 1)
  })

  observeEvent(input$open_annotation, {
    images <- selected_camera_images()
    if (nrow(images) == 0) {
      showNotification("No detections to modify for this camera day.", type = "message")
      return()
    }
    send_annotation_editor_frame(TRUE)
  })

  observeEvent(input$annotation_frame_step, {
    req(state$annotation_modal_open())
    images <- selected_camera_images()
    req(nrow(images) > 0)
    step <- as.integer(input$annotation_frame_step$step)
    if (is.na(step)) {
      return()
    }
    previous_index <- state$selected_image_index()
    state$selected_image_index(((previous_index - 1 + step) %% nrow(images)) + 1)
    if (!send_annotation_editor_frame(TRUE)) state$selected_image_index(previous_index)
  })

  observeEvent(input$annotation_modal_closed, {
    state$annotation_modal_open(FALSE)
  })

  # main function where we process updates from the annotoriosu powered, html template + partly JS controlled bbox editign
  observeEvent(input$detection_annotation_changed, {
    req(state$annotation_modal_open())
    payload <- input$detection_annotation_changed
    event_type <- payload$event_type
    if (is.null(event_type) || !event_type %in% c("bbox_created", "bbox_edited", "bbox_deleted", "species_changed")) return()
    detection_id <- if (is.null(payload$detection_id)) "new detection" else payload$detection_id
    image_id <- payload$image_id
    species <- if (is.null(payload$species)) "unlabelled" else payload$species
    images <- selected_camera_images()
    req(nrow(images) > 0, identical(image_id, images$image_id[state$selected_image_index()]))


    saved <- if (is.null(auth) || !auth$can_manage_cameras()) {
      showNotification("Sign in from Settings to save corrections.", type = "warning")
      NULL
    } else {
      annotation_key <- paste(image_id, detection_id, sep = "/") # ID fo the image is used as a reference
      if (!is.null(annotation_targets[[annotation_key]])) payload$detection_id <- annotation_targets[[annotation_key]]
      tryCatch({
        result <- save_correction(payload, auth$credentials$user_info$app_user_id)
        annotation_targets[[annotation_key]] <- result$target_id
        result
      }, error = function(error) {
        message("Annotation save failed: ", conditionMessage(error))
        showNotification("Correction could not be saved. Check the species and box, then try again.", type = "error")
        NULL
      })
    }
    annotations_by_image <- state$annotation_overrides()
    if (is.null(saved)) {
      state$last_correction("Not saved. The last saved annotations have been restored.")
      session$sendCustomMessage("restore_annotations", list(image_id = image_id, annotations = annotations_by_image[[image_id]]))
      return()
    }
    if (isTRUE(saved$analysis_warning)) {
      showNotification("Correction saved, but daily results could not be updated because some images were deleted.", type = "warning")
    }
    if (is.list(payload$annotations)) {
      annotations_by_image[[image_id]] <- payload$annotations
      state$annotation_overrides(annotations_by_image)
    }
    bbox <- payload$bbox
    bbox_summary <- NULL
    bbox_coordinates <- unlist(bbox[c("x0", "y0", "x1", "y1")], use.names = FALSE) # send always x0/x1/y0/y1 form for clarity
    if (is.numeric(bbox_coordinates) && length(bbox_coordinates) == 4 && all(is.finite(bbox_coordinates))) {
      bbox_summary <- sprintf(
        "bbox: (%s, %s)–(%s, %s)",
        bbox_coordinates[1],
        bbox_coordinates[2],
        bbox_coordinates[3],
        bbox_coordinates[4]
      )
    }
    state$last_correction(paste(c("Saved", event_type, detection_id, image_id, species, bbox_summary), collapse = " | "))
  })

  output$download_detections <- downloadHandler(
    filename = function() {
      paste0(state$selected_camera_name(), "-", format(selected_map_day(input$time_slider), "%Y%m%d"), "-detections.csv")
    },
    content = function(file) {
      write.csv(selected_detection_export(), file, row.names = FALSE)
    }
  )

  output$camera_image_panel <- renderUI({
    images <- selected_camera_images()
    if (nrow(images) == 0) {
      return(div(
        class = "camera-frame camera-frame-empty",
        div(class = "camera-empty-state", "No detections for this camera day.")
      ))
    }
    index <- min(max(state$selected_image_index(), 1), nrow(images))
    # Some JS embedded here in fake "R html". This could be in another template since it jsut references document JS functions getting ID and actions upon them, but it's here becuse the img data needs to be set (src which makes it appear) so it makes sense to have these here.
    frame <- images[index, ]
    annotation_click <- "var button = document.getElementById('open_annotation'); if (button) { button.click(); }"
    div(
      class = "camera-frame",
      div(
        class = "camera-frame-image-wrap",
        role = "button",
        tabindex = "0",
        onclick = annotation_click,
        onkeydown = paste("if (event.key === 'Enter' || event.key === ' ') { event.preventDefault();", annotation_click, "}"),
        tags$img(src = camera_frame_image(frame), alt = paste("Camera frame", frame$image_id)),
        tagList(preview_bbox_tags(frame$image_id, selected_camera_day()$detections))
      ),
      div(
        class = "camera-meta",
        span(format(frame$timestamp, "%Y-%m-%d %H:%M UTC")),
        div(class = "camera-detection-actions", span(detection_count_label(frame$detection_count)))
      ),
      div(
        class = "camera-controls",
        actionButton("prev_camera_image", NULL, icon = sentinel_icon("chevron-left"), class = "btn-default", title = "Previous frame"),
        span(class = "camera-index", paste("Frame", index, "of", nrow(images))),
        actionButton("next_camera_image", NULL, icon = sentinel_icon("chevron-right"), class = "btn-default", title = "Next frame")
      )
    )
  })

  output$correction_status <- renderUI({
    req(state$last_correction())
    div(class = "correction-status", state$last_correction())
  })

  output$inspector_panel <- renderUI({
    if (is.null(state$selected_camera_name())) return(NULL)
    camera <- selected_camera_record()
    req(nrow(camera) > 0)
    camera_images <- selected_camera_images()
    modify_button <- if (nrow(camera_images) > 0) {
      actionButton("open_annotation", label = NULL, icon = icon("robot"), class = "inspector-modify", title = "Review ML detections")
    } else {
      tags$button(
        type = "button",
        class = "btn btn-default inspector-modify is-disabled",
        disabled = "disabled",
        title = "No detections to modify",
        icon("robot")
      )
    }
    absolutePanel(
      class = "inspector-panel",
      fixed = TRUE,
      top = "50%",
      bottom = "auto",
      left = "50%",
      right = "auto",
      div(class = "box card p-3",
          div(
            class = "inspector-header",
            div(class = "d-flex align-items-center gap-2 overflow-hidden",
              div(class = "inspector-title", camera$camera_name),
              settings_modal_link("camera_edit_open", sentinel_icon("pencil"), class = "btn inspector-edit", title = "Edit camera")
            ),
            div(
              class = "inspector-actions",
              downloadLink("download_detections", sentinel_icon("database"), class = "database-download", title = "Download detections CSV"),
              modify_button,
              actionButton("close_inspector", label = NULL, icon = sentinel_icon("x-lg"), class = "inspector-close", title = "Close")
            )
          ),
          div(
            class = "activity-counts",
            metric_count("Prey", camera$rodent_activity, predator_heat_low_hex),
            metric_count("Predator", camera$predator_count, predator_heat_high_hex)
          ),
          uiOutput("camera_image_panel"),
          uiOutput("correction_status"))
    )
  })
}
